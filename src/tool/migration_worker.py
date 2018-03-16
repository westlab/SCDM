import subprocess as sp
import configparser

from tool.gRPC import grpc_client
from settings.docker import DOCKER_BASIC_SETTINGS_PATH, CREDENTIALS_SETTING_PATH
from tool.docker_api import DockerApi

class MigrationWorker:
    def __init__(self, cp_name, dst_addr):
        config = configparser.ConfigParser()
        config.read(DOCKER_BASIC_SETTINGS_PATH)
        self._config = config
        self._dst_addr = dst_addr
        self._cp_name =  cp_name
        self._cli = DockerApi()

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
    #TODO: Find a way to send the fiels with more throughput, and easier way
    def rsync(self):
        print('rsync')
        cre_config = configparser.ConfigParser()
        cre_config.read(CREDENTIALS_SETTING_PATH)
        c = self._cli.container_presence('cr_test')
        # copy all directory under the cp_path, which leads to take time to copy and send files 
        cp_path = '{0}/{1}/'.format(self._config['checkpoint']['default_cp_dir'])
        cmd = "sshpass -p {passwd} rsync -avzr -e ssh {cp_path} miura@{dst}:{cp_path}".format(passwd=cre_config['dst_host']['password'], dst=self._dst_addr, cp_path=cp_path)
        try:
            sp.run(cmd.strip().split(" "), check=True)
            return True
        except:
            return False

