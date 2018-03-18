#import subprocess as sp
import configparser

from tool.gRPC import grpc_client
from tool.rsync import Rsync

class MigrationWorker:
    def __init__(self, cli, i_name, version, c_name, cp_name, migration_option, c_opt):
        self._docker_cli = cli
        self._rpc_client = RpcClient()
        self._i_name = i_name
        self._version = version
        self._c_name = c_name
        self._cp_name = cp_name
        self._migration_opt = migration_opt
        self._c_opt = c_opt

    """
    Start migration-worker for migrating Docker App based on the following tasks
    1. Check connection
    2. Inspect the images, pull the image if it doesn't exist
    3. Create checkpoints (leave the app run)
    4. Send checkpoints to dst host
    5. Restore the App based on the data

    @return True|False
    """
    def start(self):
        print("start")
        c = self._cli.container_presence('cr_test')
        cp_path = '{0}/{1}/'.format(self._config['checkpoint']['default_cp_dir'], c.id)
        Rsync.call(cp_path, cp_path, 'miura', src_addr=None, dst_addr=self._dst_addr)

