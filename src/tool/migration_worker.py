import configparser
from http import HTTPStatus
from datetime import datetime

from settings.docker import CODE_SUCCESS, CODE_HAS_IMAGE, CODE_NO_IMAGE, DOCKER_BASIC_SETTINGS_PATH
from tool.common.logging.logger_factory import LoggerFactory
from tool.common.rsync import Rsync
from tool.docker.docker_layer import DockerLayer
from tool.docker.docker_container_extraction import DockerContainerExtraction
from tool.gRPC.grpc_client import RpcClient

class MigrationWorker:
    TOTAL_STREAM_COUNT = 2
    ORDER_OF_REQUEST_MIGRATION = 2

    def __init__(self, cli, i_name, version, c_name, m_opt, c_opt):
        config = configparser.ConfigParser()
        config.read(DOCKER_BASIC_SETTINGS_PATH)
        i_layer_manager = DockerLayer()

        self._logger = LoggerFactory.create_logger(self)
        self._d_cli = cli
        self._d_c_extractor = DockerContainerExtraction(c_name, cli.container_presence(c_name).id,
                i_layer_manager.get_local_layer_ids(i_name),
                i_layer_manager.get_container_layer_ids(c_name))
        self._d_config = config
        self._i_name = i_name
        self._version = version
        self._c_name = c_name
        self._m_opt = m_opt
        self._c_opt = c_opt

    """
    Start migration-worker for migrating Docker App based on the following tasks
    1. Inspect images, pull the image if it doesn't exist
    2. Create a container (leave the app run)
    3. Create checkpoint (leave the app run)
    4. Send checkpoints to dst host
    5. Restore the App based on the data

    @return True|False
    """
    def run(self):
        self._logger.info("run: Init RPC client")
        rpc_client = RpcClient(dst_addr=self._m_opt['dst_addr'])
        #repo = '{base}/{i_name}'.format(base=self._d_config['docker_hub']['remote'],i_name=self._i_name)
        tag = self.tag_creator()

        #1. Inspec Images
        code = rpc_client.inspect(i_name=self._i_name, version=self._version, c_name=self._c_name)
        # inspect existence of docker image in dockerhub
        #if code == CODE_NO_IMAGE:
            # if it exists, dst will pull the image
            # if it does not exists, src pushes the image

        #2. checkpoint docker container
        #3. tranfer tranfer the container artifacts
        # TODO: before checkpoint, check signal is changed
        has_checkpointed = self._d_cli.checkpoint(self._c_name)
        if has_checkpointed is not True:
            return self.returned_data_creator('checkpoint', code=HTTPStatus.INTERNAL_SERVER_ERROR.value)
        has_sent = self._d_c_extractor.transfer_container_artifacts(dst_addr=self._m_opt['dst_addr'])
        if has_sent is not True:
            return self.returned_data_creator('send_checkpoint', code=HTTPStatus.INTERNAL_SERVER_ERROR.value)
        #DockerLayer.reload_daemon()
        # 5. Restore the App based on the data
        code = rpc_client.allocate_container_artifacts(self._d_c_extractor.c_name,
                                                       self._d_c_extractor.c_id,
                                                       self._d_c_extractor.i_layer_ids,
                                                       self._d_c_extractor.c_layer_ids)
        self._logger.info("Restore container at dst host")
        code = rpc_client.restore(self._c_name)
        if code != CODE_SUCCESS:
            return self.returned_data_creator(rpc_client.restore.__name__, code=code)
        return self.returned_data_creator('fin')

    def run_involving_image_migration(self):
        self._logger.info("run_with_image_migration: Init RPC client")
        rpc_client = RpcClient(dst_addr=self._m_opt['dst_addr'])
        repo = '{base}/{i_name}'.format(base=self._d_config['docker_hub']['remote'],i_name=self._i_name)
        tag = self.tag_creator()

        # 1. Inspect images
        code = rpc_client.inspect(i_name=repo, version=tag, c_name=self._c_name)
        if code == CODE_NO_IMAGE:
            image = self._d_cli.commit(c_name=self._c_name, repository=repo, tag=tag)
            if image is not None:
                self._logger.info("Push Docker repo:{0}, tag:{1}".format(repo, tag))
                has_pushed = self._d_cli.push(repository=repo, tag=tag)
                if has_pushed is False:
                    return self.returned_data_creator('push')
            else:
                 return self.returned_data_creator('commit')
        # 2. Fetch Docker image from docker hub, and Create a containeri
        # 3. Create checkpoints
        # 4. Send checkpoints docker
        status_with_c_id = rpc_client.create_container(i_name=repo, version=tag, c_name=self._c_name)
        if status_with_c_id.code == CODE_SUCCESS:
            self._logger.info("Checkpoint running container")
            has_checkpointed = self._d_cli.checkpoint(self._c_name)
            has_sent = self.send_checkpoint(c_id=status_with_c_id.c_id)

            if has_checkpointed is not True:
                return self.returned_data_creator('checkpoint', code=status_with_c_id.code)
            if has_sent is not True:
                return self.returned_data_creator('send_checkpoint', code=status_with_c_id.code)
        else:
            return self.returned_data_creator('create', code=status_with_c_id.code)

        # 5. Restore the App based on the data
        self._logger.info("Restore container at dst host")
        code = rpc_client.restore(self._c_name)
        if code != CODE_SUCCESS:
            return self.returned_data_creator(rpc_client.restore.__name__, code=code)
        return self.returned_data_creator('fin')

    """
    Checkpoint and send checkpoint data to dst host

    @params None
    @return True|False
    """
    def send_checkpoint(self, c_id):
        src_c = self._d_cli.container_presence(self._c_name)
        cp_path = '{0}/{1}/'.format(self._d_config['checkpoint']['default_cp_dir'], src_c.id)
        dst_path = '{0}/{1}/'.format(self._d_config['checkpoint']['default_cp_dir'], c_id)
        is_success = Rsync.call(cp_path, dst_path, 'miura', src_addr=None, dst_addr=self._m_opt['dst_addr'])
        return is_success

    """
    Create docker tag, which is unique to generated worker
    @params None
    @return String tag
    """
    def tag_creator(self):
        return datetime.now().strftime('%Y%m%d_%H%M%S')

    """
    Create message for explaning status to those who request with migration API

    @params String func_name
    @params Integer code
    @params dict        { "data": dict, "status": Integer }
            data        { "message": String, "container_dict": dict }
            container_dict   { "image_name": String, "version": String, "container_name": String }
    """
    def returned_data_creator(self, func_name, code=None):
        container_dict = { "image_name": self._i_name, "version": self._version, "container": self._c_name }
        data = { "container_dict": container_dict }

        if func_name is "ping":
            data["message"] = "dockerd is not running"
            return { "data": data, "status": HTTPStatus.INTERNAL_SERVER_ERROR.value }
        elif func_name is "restore":
            data["message"] = "cannot restore"
            return { "data": data, "status": HTTPStatus.INTERNAL_SERVER_ERROR.value }
        elif func_name is "migration_request":
            data["message"] = "cannot checkpoint"
            return { "data": data, "status": HTTPStatus.INTERNAL_SERVER_ERROR.value }
        elif func_name is 'create':
            data["message"] = "cannot create container"
            return { "data": data, "status": HTTPStatus.INTERNAL_SERVER_ERROR.value }
        elif func_name is 'checkpoint':
            data["message"] = "cannot checkpoint"
            return { "data": data, "status": HTTPStatus.INTERNAL_SERVER_ERROR.value }
        elif func_name is 'send_checkpoint':
            data["message"] = 'cannot send checkpoint data'
            return { "data": data, "status": HTTPStatus.BAD_REQUEST.value}
        elif func_name is  "commit":
            data["message"] = 'cannot commit the container '
            return { "data": data, "status": HTTPStatus.BAD_REQUEST.value}
        elif func_name is  "push":
            data["message"] = 'cannot push generated image'
            return { "data": data, "status": HTTPStatus.INTERNAL_SERVER_ERROR.value }
        elif func_name is 'fin':
            data["message"] = "Accepted"
            return { "data": data, "status": HTTPStatus.OK.value }
        else:
            data["message"] = "unknown function"
            return { "data": data, "status": HTTPStatus.BAD_REQUEST.value}

