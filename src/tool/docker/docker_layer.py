import docker
import json
import re
import sys
from pathlib import Path

from tool.docker.docker_base_api import DockerBaseApi
from settings.docker import OVERLAYER2_DIR_PATH, LAYERDB_DIR_PATH, IMAGEDB_DIR_PATH, CONTAINER_CONF_PATH

"""
Manage Docker Image and Container Layers
"""

LAYERDB_DIR_PATH="/var/lib/docker/image/overlay2/layerdb"
OVERLAYER2_DIR_PATH="/var/lib/docker/overlay2"


class DockerLayer(DockerBaseApi):
    def __init__(self):
        super().__init__()
        self._lo_client = docker.APIClient()

    def image_settings_path(self):
        return Path(IMAGEDB_DIR_PATH + "/content/sha256")

    def cache_id_settings_base_path(self):
        return Path(LAYERDB_DIR_PATH + "/sha256")

    def overlays_path(self):
        return Path(OVERLAYER2_DIR_PATH)

    def alternaitve_cache_id_file_path(self, layer_id):
        return self.cache_id_settings_base_path()/layer_id/"local-cache-id"

    """
    Get relationships between original layer_ids and local layer_ids 
    @returns Dict[key: local layer_id, value: original layer_id]
    """
    def get_layer_id_relations(self):
        relations = {}
        base_path = self.cache_id_settings_base_path()
        try: 
            for o_layer_id in base_path.glob("*"):
                o_layer_path = base_path/o_layer_id
                tmp_local_cache_id_path = o_layer_id/"local-cache-id"

                if not tmp_local_cache_id_path.exists():
                    local_cache_id_path = o_layer_id/"cache-id"
                    relations[local_cache_id_path.read_text().strip()] = o_layer_id.name.strip()
        except Exception as e:
            print("get_layer_id_relations args:", e.args)
        return relations

    """
    Get the designated image layer_ids 
    @params String image_name
    @returns Array[String layer_id]
    """
    def get_local_layer_ids(self, image_name):
        pattern = OVERLAYER2_DIR_PATH + '/(.*)/diff'
        reg = re.compile(pattern)
        layer_config =  self._lo_client.inspect_image(image_name)['GraphDriver']['Data']

        local_layer_ids = [ reg.match(local_layer).group(1) for local_layer in layer_config['LowerDir'].split(':')] if 'LowerDir' in layer_config.keys() else []
        local_layer_ids.append(reg.match(layer_config['UpperDir']).group(1))
        return local_layer_ids

    """
    Remap local-layer-id to original-layer-id for designated layer_ids
    and Change dir relations of related dir and symbolic links
    @params Array[String local_layer_ids]
    @params Dict {key: local layer_id, value: original layer_id}
    @returns True | False
    """
    def remap_local_layer_ids(self, lo_layer_ids, relations):
        try:
            for lo_layer_id in lo_layer_ids:
                o_layer_id = relations[lo_layer_id]
                alternative_file_path = self.alternaitve_cache_id_file_path(o_layer_id)

                if not alternative_file_path.exists():
                    self.write_original_layer_id(o_layer_id)
                    self.change_layer_dir_relation(o_layer_id, lo_layer_id)
            return True
        except Exception as e:
            print("remap_local_layer_ids args:", e.args)
            return False

    """
    Change cache-id file name for designated layer_ids
    @params String original_layer_id
    """
    def write_original_layer_id(self, o_layer_id):
        cache_id_file_path = self.cache_id_settings_base_path()/o_layer_id/"cache-id"
        # rename existing cache-id file
        cache_id_file_path.rename(self.alternaitve_cache_id_file_path(o_layer_id))
        cache_id_file_path.write_text(o_layer_id)

    """
    Change actual layer dir name and modify symbolic links
    @params String original_layer_id
    @params String local_layer_id
    """
    def change_layer_dir_relation(self, o_layer_id, lo_layer_id):
        base_path = self.overlays_path()
        #rename layer dir
        (base_path/lo_layer_id).rename(base_path/o_layer_id)

        #change symbolic links
        target_link = Path("../" + o_layer_id + "/diff")
        shortened_layer_identifier = (base_path/o_layer_id/"link").read_text()
        shortened_layer_identifier_path = base_path/"l"/shortened_layer_identifier
        shortened_layer_identifier_path.unlink()
        shortened_layer_identifier_path.symlink_to(target_link)

    """
    Execute following remapping tasks:
    1. Get layer relations between original and local layer
    2. Get local layer id from docker inspection API
    3. Remap layer id from local to original
    4. Change related dir and symbolic links.

    @params String image_name
    """
    def execute_remapping(self, image_name):
        relations = self.get_layer_id_relations()
        local_ids = self.get_local_layer_ids(image_name)
        self.remap_local_layer_ids(local_ids, relations)

