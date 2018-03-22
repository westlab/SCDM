#import subprocess as sp
import configparser
from http import HTTPStatus

from settings.docker import CODE_SUCCESS, CODE_HAS_IMAGE, CODE_NO_IMAGE, DOCKER_BASIC_SETTINGS_PATH
from tool.gRPC.grpc_client import RpcClient
from tool.rsync import Rsync

class MigrationWorker:
    TOTAL_STREAM_COUNT = 2
    ORDER_OF_REQUEST_MIGRATION = 1


    def __init__(self, cli, i_name, version, c_name, cp_name, m_opt, c_opt):
        config = configparser.ConfigParser()
        config.read(DOCKER_BASIC_SETTINGS_PATH)

        self._d_cli = cli
        self._d_config = config
        self._i_name = i_name
        self._version = version
        self._c_name = c_name
        self._cp_name = cp_name
        self._m_opt = m_opt
        self._c_opt = c_opt

    """
    Start migration-worker for migrating Docker App based on the following tasks
    1. Check connection
    2. Inspect images, pull the image if it doesn't exist
    3. Create checkpoints (leave the app run)
    4. Send checkpoints to dst host
    5. Restore the App based on the data

    @return True|False`
    """
    def run(self):
        rpc_client = RpcClient()
        # 1. Check connection
        #code = rpc_client.ping()
        #if code is not CODE_SUCCESS:
        #    print(self.returned_data_creator(rpc_client.ping.__name__, code))

        # 2. Inspect images
        # 3. Create checkpoints
        # 4. Send checkpoint data to dst host
        gen = rpc_client.request_migration(self._i_name, self._version, self._c_name, self._c_opt)
        for x in range(self.TOTAL_STREAM_COUNT):
            code = gen.next()
            print(code)
            if x+1 is self.ORDER_OF_REQUEST_MIGRATION:
                print("time to migtate!")
                has_checkpointed = self._d_cli.checkpoint(self._c_name, self._cp_name)
                has_sent = self.send_checkpoint()
                if has_checkpointed and has_sent:
                    continue
                elif has_checkpointed is not True:
                    return self.returned_data_creator('checkpoint', code=code)
                elif has_sent is not True:
                    return self.returned_data_creator('send_checkpoint', code=code)
            else:
                continue

        # 5. Restore the App based on the data
        code = rpc_client.restore(self._c_name)
        if code is not CODE_SUCCESS:
            return self.returned_data_creator(rpc_client.restore.__name__, code=code)
        return self.returned_data_creator('fin')


    """
    Checkpoint and send checkpoint data to dst host

    @params None
    @return True|False
    """
    def send_checkpoint(self):
        c = self._d_cli.container_presence(self._c_name)
        cp_path = '{0}/{1}/'.format(self._d_config['checkpoint']['default_cp_dir'], c.id)
        return Rsync.call(cp_path, cp_path, 'miura', src_addr=None, dst_addr=self._m_opt['dst_addr'])

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
            print('restore')
        elif func_name is "migration_request":
            data["message"] = "cannot checkpoint"
            return { "data": data, "status": HTTPStatus.INTERNAL_SERVER_ERROR.value }
        elif func_name is 'checkpoint':
            data["message"] = "cannot checkpoint"
            return { "data": data, "status": HTTPStatus.INTERNAL_SERVER_ERROR.value }
        elif func_name is 'send_checkpoint':
            data["message"] = 'cannot send checkpoint data'
            return { "data": data, "status": HTTPStatus.BAD_REQUEST.value}
        elif func_name is 'fin':
            data["message"] = "Accepted"
            return { "data": data, "status": HTTPStatus.OK.value }
        else:
            data["message"] = "unknown function"
            return { "data": data, "status": HTTPStatus.BAD_REQUEST.value}
