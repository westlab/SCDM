# from multiprocessing import Process
import xmlrpc.client
#from tool.docker_api import DockerApi

class MigrationWorker:
    def __init__(self, image_name, dst_addr, service_id=0):
        self._image_name = image_name
        self._dst_addr = dst_addr
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
        rpc_client = xmlrpc.client.ServerProxy("http://localhost:24002/")
        print(rpc_client.hello())
