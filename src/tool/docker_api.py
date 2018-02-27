# doc https://docker-py.readthedocs.io/en/stable/
import docker

class DockerApi:
    def __init__(self):
        self._client = docker.from_env()
        self._base_path = './tool/dockerfiles'

    # TODO: dockerfileからの生成を行わないので修正する必要あり
    def build(self, filename):
        # fileがない場合は、status: 400を返す
        image = self._client.images.build(path=self._base_path,
                                          dockerfile=filename)
        return dict(image_id=image.short_id)

    # inspect own image state by image_name
    def inspect(self, image_name):
        print("inspect")

    def checkpoint(self):
        print('checkpoint')

    def restore(self):
        print('restore')

