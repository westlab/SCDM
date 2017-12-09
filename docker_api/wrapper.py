# doc https://docker-py.readthedocs.io/en/stable/
import docker
import xmlrpc.client
import os
#from pathlib import Path

class DockerWrapper:
    def __init__(self):
        self._client = docker.from_env()
        self._base_path = './docker_api/dockerfiles'

    def build(self, filename):
        # fileがない場合は、status: 400を返す
        image = self._client.images.build(path=self._base_path,
                                          dockerfile=filename)
        return dict(image_id=image.short_id)

    def migrate(self):
        """execute migration from src to dst"""
        rpc_client = xmlrpc.client.ServerProxy("http://localhost:24002/")
        print(rpc_client.hello())
