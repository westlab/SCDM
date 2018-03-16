import subprocess as sp
import configparser

from tool.gRPC import grpc_client
from settings.docker import DOCKER_BASIC_SETTINGS_PATH

class MigrationWorker:
    def __init__(self, i_name, cp_name, dst_addr, service_id=0):
        config = configparser.ConfigParser()
        self._config = config.read(DOCKER_BASIC_SETTINGS_PATH)
        self._i_name = i_name
        self._dst_addr = dst_addr
        self._cp_name =  cp_name
        self._service_id = service_id

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

    """
    Send checkpoint from src to dst host using rsync

    @return True|False
    """
    #TODO: secure communication
    def rsync(self):
        cmd = "rsync -avz {dst}:{cp_path]/{dir_name} {cp_path}/{dir_name}".format(dst=self._dst_addr,
                                                                                 cp_path=self._config['checkpoint']['default_cp_dir'],
                                                                                 dir_name=self._cp_name)
        try:
            sp.run(cmd.strip().split(" "), check=True)
            return True
        except:
            return False

