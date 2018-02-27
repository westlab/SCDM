# from multiprocessing import Process
import xmlrpc.client

from tool.docker_api import DockerApi

class MigrationWorker:
    def __init__(self, image_name, dst_addr):
        self._image_name = image_name
        self._dst_addr = dst_addr

        super().__init__()

    # 一連のプロトコルを記述する
    def start(self):
        # migration protocol
        # 1. connection check
        # 2. inspect the images, and build(非同期)
        # 3. create checkopoints (leaves the app run)
        # 4. send checkpoints data
        # 5. (要議論)
        # 5. suspend the src app, and then restore the dst app
        # 5. restore the dst app, and then suspend the src app
        # 6. send ack

        rpc_client = xmlrpc.client.ServerProxy("http://localhost:24002/")
        print(rpc_client.hello())
