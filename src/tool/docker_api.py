import docker

from tool.docker_base_api import DockerBaseApi
from tool.migration_worker import MigrationWorker

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
            # already exist the image in local
            return image

    """
    Inspect an image and a container based on i_name and c_name

    @params String i_name(image_name), c_name(container_name)
    @params String version
    @return dict{"image": Boolean, "container": Boolean}
    """
    def inspect_artifacts(self, i_name, version, c_name):
        return {"image": self.image_present(i_name, version),
                "container": self.container_present(c_name)}

