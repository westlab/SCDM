import docker
import re
import shutil
from pathlib import Path

from tool.docker.docker_base_api import DockerBaseApi
from tool.common.rsync import Rsync
from settings.docker import OVERLAYER2_DIR_PATH, LAYERDB_DIR_PATH, IMAGEDB_DIR_PATH, CONTAINER_PATH, DST_TARGET_DIR_PATH

"""
Extract components of Docker container
"""

class DockerContainerExtraction(DockerBaseApi):
    def __init__(self):
        super().__init__()
        self._lo_client = docker.APIClient()

    def overlays_path(self):
        return Path(OVERLAYER2_DIR_PATH)

    def container_settings_path(self, container_id):
        return Path(CONTAINER_CONF_PATH + '/' + container_id)

    def container_mount_settings_path(self):
        return Path(LAYERDB_DIR_PATH + "/mounts")

    def identifier_path(self, layer_id):
        identifier = self.layer_short_identifier(layer_id)
        return Path(self.overlays_path()/"l"/identifier)

    def layer_short_identifier(self, layer_id):
        return (self.overlays_path()/layer_id/"link").read_text()

    def dst_target_dir_path(self, container_name):
        container_id = self.container_presence(container_name).id
        return Path(DST_TARGET_DIR_PATH + '/' + container_id)

    """
    Get relation between container id and local container layer_id
    @params String container_name
    @return Array[String layer_id]
    """
    def get_container_layer_ids(self, container_name):
        layer_ids = []
        pattern = OVERLAYER2_DIR_PATH + '/(.*)/diff'
        reg = re.compile(pattern)
        layer_config = self._lo_client.inspect_container(container_name)['GraphDriver']['Data']
        layer_ids.append(reg.match(layer_config['LowerDir'].split(':')[0]).group(1))
        layer_ids.append(reg.match(layer_config['UpperDir']).group(1))
        return layer_ids

    """
    Create symbolic links for container layer
    @params Array[String layer_id]
    @params True | False
    """
    def create_symbolic_links(self, layer_ids):
        try: 
            for layer_id in layer_ids:
                identifier = self.identifier_path(layer_id)
                target_link = Path("../" + layer_id + "/diff")
                identifier_path.touch()
                identifier_path.symlink_to(target_link)
        except Exception as e:
            print("args:", e.args)
            return False
        return True

    """
    Extract related file names of running container
        container running states:   /var/lib/docker/containers/<Con-ID>
        Layer files:                /var/lib/docker/overlay2/<rootfs-ID>, <rootfs-ID>-init
        Mount info:                 /var/lib/docker/image/overlay2/layerdb/mounts/<Con-ID>
    @params String container_name
    @return Array[String dir_name]
    """
    def extract_container_related_paths(self, container_name):
        return  (self.extract_container_related_artifacts(container_name)).values()

    """
    Return Dict, which stores container related paths with file name key
    @params String container_name
    @returns Dict{ Key: String dir_name, Value: Path dir_name}
    """
    def extract_container_related_artifacts(self, container_name):
        running_state_dict = {}
        container_id = self.container_presence(container_name).id
        layer_ids = self.get_container_layer_ids(container_name)
        running_state_dict['rootfs'] = [ self.overlays_path()/layer_id for layer_id in layer_ids if (self.overlays_path()/layer_id).name.isalnum()][0]
        running_state_dict['rootfs_init'] = [ self.overlays_path()/layer_id for layer_id in layer_ids if not (self.overlays_path()/layer_id).name.isalnum()][0]
        running_state_dict['containers'] = self.container_settings_path(container_id)
        running_state_dict['mounts'] = self.container_mount_settings_path()/container_id
        return running_state_dict

    """
    Allocate tranfered files to original location
    @params String container_name
    @params Array[String layer_id]: src information
    @return True | False
    """
    def allocate_container_artifacts(self, container_name, layer_ids):
        target_path = self.dst_target_dir_path(container_name)
        d = self.extract_container_related_artifacts(container_name)
        try:
            for tmp_d_name, d_name in d.iteritems():
                shutil.move(str(targe_path/tmp_d_name), d_name)
            self.create_symbolic_links(layer_ids)
        except Exception as e:
            print("args:", e.args)
            return False
        return True

