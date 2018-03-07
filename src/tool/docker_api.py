import docker

from tool.docker_base_api import DockerBaseApi

class DockerApi(DockerBaseApi):
    def __init__(self):
        super().__init__()

    """
    Fetch an image based on given arguments
    If host hasn't the image, host will pull the image through Dockerhub

    @params String name
    @params String version=latest
    @return Image
    """
    def fetch_image(self, name, version="latest"):
        image = self.image_presence(name, version)
        if image is None:
            try:
                pulled_image  = self.pull(name, version)
                return pulled_image
            except docker.errors.APIError:
                return None
        else:
            return image
