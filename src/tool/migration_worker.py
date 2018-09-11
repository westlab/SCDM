import configparser
from http import HTTPStatus
from datetime import datetime
from subprocess import Popen
from pathlib import Path
import pdb # for debug
import copy

from settings.docker import CODE_SUCCESS, CODE_HAS_IMAGE, CODE_NO_IMAGE, DOCKER_BASIC_SETTINGS_PATH
from tool.common.logging.logger_factory import LoggerFactory
from tool.common.rsync import Rsync
from tool.docker.docker_layer import DockerLayer
from tool.docker.docker_container_extraction import DockerContainerExtraction
from tool.docker.docker_container_extraction import DockerVolume
from tool.gRPC.grpc_client import RpcClient

# For evaluation
from tool.common.time_recorder import TimeRecorder, ProposedMigrationConst
from tool.common.resource_recorder import ResourceRecorder
from tool.common.disk_recorder import DiskRecorder

class MigrationWorker:
    TOTAL_STREAM_COUNT = 2
    ORDER_OF_REQUEST_MIGRATION = 2

    def __init__(self, cli, i_name, version, c_name, m_opt, c_opt, bandwidth=0):
        config = configparser.ConfigParser()
        config.read(DOCKER_BASIC_SETTINGS_PATH)
        i_layer_manager = DockerLayer()

        self._logger = LoggerFactory.create_logger(self)
        self._d_cli = cli
        self._c_id = cli.container_presence(c_name).id
        self._d_c_extractor = DockerContainerExtraction(c_name, self._c_id,i_layer_manager.get_local_layer_ids(i_name),i_layer_manager.get_container_layer_ids(c_name))
        self._d_config = config
        self._i_name = i_name
        self._version = version
        self._c_name = c_name
        self._m_opt = m_opt
        self._c_opt = c_opt
        self._bandwidth = bandwidth

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
        d_recorder = DiskRecorder('{0}_{1}'.format(self._c_name, self._bandwidth))
        t_recorder = TimeRecorder('{0}_{1}'.format(self._c_name, self._bandwidth) )
        r_recorder = ResourceRecorder('{0}_{1}'.format(self._c_name, self._bandwidth))

        r_recorder.insert_init_cond()
        r_recorder.track_on_subp()
        t_recorder.track(ProposedMigrationConst.MIGRATION_TIME)

        #1. Inspect Images
        code = rpc_client.inspect(i_name=self._i_name, version=self._version, c_name=self._c_name)
        # inspect existence of docker image in dockerhub
        #if code == CODE_NO_IMAGE:
            # if it exists, dst will pull the image
            # if it does not exists, src pushes the image

        #2. checkpoint docker container
        #3. tranfer tranfer the container artifacts

        # TODO: before checkpoint, check signal is changed
        t_recorder.track(ProposedMigrationConst.CHECKPOINT)
        t_recorder.track(ProposedMigrationConst.SERVICE_DOWNTIME)
        has_checkpointed = self._d_cli.checkpoint(self._c_name)
        t_recorder.track(ProposedMigrationConst.CHECKPOINT)
        if has_checkpointed is not True:
            return self.returned_data_creator('checkpoint', code=HTTPStatus.INTERNAL_SERVER_ERROR.value)
        has_create_tmp_dir = rpc_client.create_tmp_dir(self._c_id)
        if has_create_tmp_dir is not CODE_SUCCESS:
            #TODO: fix
            return self.returned_data_creator('checkpoint', code=HTTPStatus.INTERNAL_SERVER_ERROR.value)

        t_recorder.track(ProposedMigrationConst.RSYNC_C_FS)
        has_sent = self._d_c_extractor.transfer_container_artifacts(dst_addr=self._m_opt['dst_addr'])
        t_recorder.track(ProposedMigrationConst.RSYNC_C_FS)
        if has_sent is not True:
            return self.returned_data_creator('send_checkpoint', code=HTTPStatus.INTERNAL_SERVER_ERROR.value)

        # 5. Restore the App based on the data
        t_recorder.track(ProposedMigrationConst.SYNC_C)
        volumes=[ volume.hash_converter() for volume in self._d_c_extractor.volumes]
        code = rpc_client.allocate_container_artifacts(self._d_c_extractor.c_name,
                                                       self._d_c_extractor.c_id,
                                                       self._d_c_extractor.i_layer_ids,
                                                       self._d_c_extractor.c_layer_ids,
                                                       volumes=volumes
                                                       )
        t_recorder.track(ProposedMigrationConst.SYNC_C)

        t_recorder.track(ProposedMigrationConst.RELOAD)
        code = rpc_client.reload_daemon()
        t_recorder.track(ProposedMigrationConst.RELOAD)

        self._logger.info("Restore container at dst host")
        t_recorder.track(ProposedMigrationConst.RESTORE)
        code = rpc_client.restore(self._c_name)
        t_recorder.track(ProposedMigrationConst.RESTORE)

        t_recorder.track(ProposedMigrationConst.SERVICE_DOWNTIME)
        t_recorder.track(ProposedMigrationConst.MIGRATION_TIME)
        r_recorder.terminate_subp()
        if code != CODE_SUCCESS:
            return self.returned_data_creator(rpc_client.restore.__name__, code=code)

        t_recorder.write()
        r_recorder.write()
        d_recorder.track_all(self._d_c_extractor)
        d_recorder.write()
        return self.returned_data_creator('fin')

    def run_involving_commit(self):
        self._logger.info("run_with_image_migration: Init RPC client")
        rpc_client = RpcClient(dst_addr=self._m_opt['dst_addr'])
        tag = self.tag_creator()

        src_repo = '{base}/{i_name}'.format(base=self._d_config['docker_hub']['private'],i_name=self._i_name)
        dst_repo = '{base}/{i_name}'.format(base=self._d_config['docker_hub']['local'],i_name=self._i_name)
        dir_name = '{0}_{1}'.format(self._i_name,tag)
        dst_default_path = '{0}/{1}'.format(self._d_config['destination']['default_dir'], dir_name)
        volumes=[]
        c_volume_options = []

        for vo in DockerVolume.collect_volumes(self._c_name, self._d_cli.lo_client, self._d_cli.client):
            vo_hash = vo.hash_converter()
            c_vo_hash = copy.copy(vo_hash)
            c_vo_hash['h_path'] = '{default_path}/{dir_name}'.format(default_path=dst_default_path, dir_name=Path(vo_hash['h_path']).name)
            volumes.append(vo_hash)
            c_volume_options.append(c_vo_hash)

        # 1. Inspect images
        #code = rpc_client.inspect(i_name=repo, version=tag, c_name=self._c_name)
        image = self._d_cli.commit(c_name=self._c_name, repository=src_repo, tag=tag)
        if image is not None:
            self._logger.info("Push Docker repo:{0}, tag:{1}".format(src_repo, tag))
            has_pushed = self._d_cli.push(repository=src_repo, tag=tag)
            if has_pushed is False:
                return self.returned_data_creator('push')
        else:
            return self.returned_data_creator('commit')
        # 2. Create checkpoints
        # 3. Send checkpoints docker
        # 4. Send volume 
        pulled_image = rpc_client.pull(i_name=dst_repo, version=tag)

        if pulled_image is not None:
            self._logger.info("Checkpoint running container")
            has_checkpointed = self._d_cli.checkpoint(self._c_name, cp_name='checkpoint1', need_tmp_dir=True)
            has_checkpoint_sent = self.send_checkpoint(src_repo, tag)
            has_volume_sent = self.send_volume(dst_repo, tag, volumes) if len(volumes) != 0 else True

            if has_checkpointed is not True:
                return self.returned_data_creator('checkpoint')
            if has_checkpoint_sent is not True:
                return self.returned_data_creator('send_checkpoint')
            if has_volume_sent is not True:
                return self.returned_data_creator('volume')
        else:
            return self.returned_data_creator('create')

        #5. create a container
        #6. Restore the App based on the data

        status_with_c_id = rpc_client.create_container(i_name=dst_repo, version=tag, c_name=self._c_name, volumes=c_volume_options)
        if status_with_c_id.code ==  CODE_SUCCESS:
            self._logger.info("Restore container at dst host")
            restore_target_path = '{0}/checkpoints'.format(dst_default_path)
            code = rpc_client.restore(self._c_name, default_path=restore_target_path)
            if code != CODE_SUCCESS:
                return self.returned_data_creator(rpc_client.restore.__name__, code=code)
        else:
            return self.returned_data_creator('create')

        return self.returned_data_creator('fin')

    """
    Checkpoint and send checkpoint data to dst host

    @params String repo
    @params String tag
    @return True|False
    """
    def send_checkpoint(self, src_repo, tag):
        src_c = self._d_cli.container_presence(self._c_name)
        dst_dir_name = '{0}_{1}'.format(self._i_name,tag)
        cp_path = '{0}/{1}/'.format(self._d_config['checkpoint']['default_dir'], src_c.id)
        dst_path = '{0}/{1}/'.format(self._d_config['destination']['default_dir'], dst_dir_name)
        is_success = Rsync.call(cp_path, dst_path, 'miura', src_addr=None, dst_addr=self._m_opt['dst_addr'])
        return is_success

    def send_volume(self, dst_repo, tag, volumes):
        src_c = self._d_cli.container_presence(self._c_name)
        dir_name = '{0}_{1}'.format(self._i_name,tag)
        for vo in volumes:
            src_path = vo['h_path']
            dst_path = '{0}/{1}/'.format(self._d_config['destination']['default_dir'], dir_name)
            is_success = Rsync.call(src_path, dst_path, 'miura', src_addr=None, dst_addr=self._m_opt['dst_addr'])
            if is_success is False:
                return False
        return True

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
        elif func_name is 'volume':
            data["message"] = "cannot volume"
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

