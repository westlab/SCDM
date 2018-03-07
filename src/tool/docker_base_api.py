# doc https://docker-py.readthedocs.io/en/stable/
import docker
import configparser

class DockerBaseApi:
    DOCKER_HUB_SETTING_FILE = "./conf/docker_hub.ini"

    def __init__(self):
        self._client = docker.from_env()
        self._base_path = "./tool/dockerfiles"

    """
    Log in specific Dockerhub repo
    based on settings written in docker_hub.ini

    @return True|False
    """
    def login(self):
        config = configparser.ConfigParser()
        config.read(DockerBaseApi.DOCKER_HUB_SETTING_FILE)
        try:
            is_success = self._client.login(username=config['account']['username'],
                                            password=config['account']['password'],
                                            email=config['account']['email'])
            return True if is_success is not None else False
        except docker.errors.APIError:
            print("Given account information is Unauthorized")
            return False

    """
    Pull docker image based on given two arguments

    @params String name
    @params String version="latest"
    @return Image
    """
    def pull(self, name, version="latest"):
        image = self._client.images.pull(self.name_converter(name, version))
        return image

    """
    Check whether specific image exists,
    and return the image or None

    @params String name
    @params String version="latest"
    @return Images|NoneType
    """
    def image_presence(self, name, version="latest"):
        name_and_ver = self.name_converter(name, version)
        try:
            return self._client.images.get(name_and_ver)
        except docker.errors.ImageNotFound:
            return None

    """
    Check whether specific image exists,
    and return True or False

    @params String name
    @params String version="latest"
    @return True|False
    """
    def image_present(self, name, version="latest"):
        name_and_ver = self.name_converter(name, version)
        try:
            i = self._client.images.get(name_and_ver)
            return True if i is not None else False
        except docker.errors.ImageNotFound:
            return False

    """
    Check whether specific container exists,
    and return Container or None

    @params String name
    @return Containers|NoneType
    """
    def container_presence(self, name):
        try:
            return self._client.containers.get(name)
        except docker.errors.ImageNotFound:
            return None

    """
    Check whether specific container exists,
    and return True or False

    @params String name
    @return True|False
    """
    def container_present(self, name):
        try:
            c = self._client.containers.get(name)
            return True if c is not None else False
        except docker.errors.NotFound:
            return False

    """
    Convert name with version along with docker-py
    based on given two arguments

    @params String name
    @params String version
    @return String
    """
    def name_converter(self, name, version):
        return name + ':' + version

    def run(self):
        print('run')

    def checkpoint(self):
        print("checkpoint")

    def restore(self):
        print("restore")

    # TODO: dockerfileからの生成を行わないので修正する必要あり
    # のちのちasynchronous
    def build(self, name, version="latest"):
        # search image by docker image name in local

        # 例外処理

        # fileがない場合は、status: 400を返す
        image = self._client.images.build(path=self._base_path,
                                          dockerfile=filename)
        return dict(image_id=image.short_id)
