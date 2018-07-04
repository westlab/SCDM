import docker
import json
from pathlib import Path

from tool.docker.docker_base_api import DockerBaseApi

"""
Manage Docker Image and Container Layers
"""

IMAGEDB_DIR_PATH="/var/lib/docker/image/overlay2/imagedb"
LAYERDB_DIR_PATH="/var/lib/docker/image/overlay2/layerdb"
OVERLAYER2_DIR_PATH="/var/lib/docker/overlay2"


class DockerLayer(DockerBaseApi):
    def __init__(self):
        super().__init__()

    def image_settings_path(self):
        return Path(IMAGEDB_DIR_PATH)/"content"/"sha256"

    def cache_id_settings_base_path(self):
        return Path(LAYERDB_DIR_PATH)/"sha256"

    def container_mount_settings_path(self):
        return Path(LAYERDB_DIR_PATH)/"mounts"

    def overlays_path(self):
        return OVERLAYER2_DIR_PATH

    def alternaitve_cache_id_file_path(self, layer_id):
        return self.cache_id_settings_base_path()/layer_id/"local-cache-id"

    """
    Returns rootfs layer_ids for the designated image_id
    @params String image_id
    @returns Array[String layer_ids]
    """
    def get_layer_ids(self, image_id):
        image_settings_file_path = self.image_settings_path()/image_id
        f = open(image_settings_file_path)
        data = json.load(f)
        f.close()
        layer_ids = [ d.strip("sha256:") for d in data["rootfs"]["diff_ids"]]
        return layer_ids


    """
    Remap cache-id file  for designated layer_ids
    @params Array[String layer_ids]
    @params True | False
    """
    def remap_local_layer_ids(self, layer_ids):
        base_path = self.cache_id_settings_base_path()
        try:
            for layer_id in layer_ids:
                cache_id_file_path = base_path/layer_id/"cache_id"
                # rename existing cache-id file
                alternative_file_path = self.alternaitve_cache_id_file_path(layer_id)
                cache_id_file_path.rename(alternative_file_path)

                # touch cache-id
                cache_id_file_path.write_text(layer_id)
            return True
        except:
            return False

    """
    Fetch cache-ids for designated layer_ids
    @params Array[String layer_ids]
    @return Array[String cache_ids]
    """
    def fetch_local_layer_ids(self, layer_ids):
        cache_ids =[]
        try:
            for layer_id in layer_ids:
                alternative_file_path = self.alternaitve_cache_id_file_path(layer_id)
                cache_id = alternative_file_path.read_text()
                cache_ids.append(self, cache_id)
            return cache_ids
        except:
            return []

    """
    Change directory from local_layer_id to original layer_id in overlay2
    @params Array[String layer_ids]
    @return True | False
    """
    def change_overlay2_dirname(self, layer_ids):
        return "hoge"


    """
    Unlink symbolic link of an old layer id dir an link new symbolic link
    @params String layer_id
    @retuns True | False
    """
    def relink_symbolic(self, layer_id):

