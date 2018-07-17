import docker
import re
import shutil
import json
from pathlib import Path

from tool.docker.docker_base_api import DockerBaseApi
from tool.common.rsync import Rsync
from settings.docker import OVERLAYER2_DIR_PATH, LAYERDB_DIR_PATH, IMAGEDB_DIR_PATH, CONTAINER_CONF_PATH, DST_TARGET_DIR_PATH

"""
Extract components of Docker container
"""

class DockerContainerExtraction(DockerBaseApi):
    def __init__(self, i_layer_ids, c_layer_ids=None):
        super().__init__()
        self._lo_client = docker.APIClient()
        self._i_layer_ids = i_layer_ids
        self._c_layer_ids = c_layer_ids

    @property
    def image_layer_ids(self):
        return self._i_layer_ids

    @property
    def container_layer_ids(self):
        return self._c_layer_ids

    @image_layer_ids.setter
    def image_layer_ids(self, layer_ids):
        self._i_layer_ids = layer_ids

    @container_layer_ids.setter
    def container_layer_ids(self, layer_ids):
        self._c_layer_ids = layer_ids

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
    Create docker dst target directory
    @params String container_name
    @return True | Flase
    """
    def create_tmp_target_dir(self, container_name):
        base_path = self.dst_target_dir_path(container_name)
        try:
            base_path.mkdir(parents=true)
        except Exception as e:
            print("create_tmp_target_dir args:", e.args)
            return False
        return True

    """
    Get relation between container id and local container layer_id
    @params String container_name
    @return Array[String layer_id]
    """
    def get_container_layer_ids(self, container_name, has_reload=True):
        layer_ids = []
        pattern = OVERLAYER2_DIR_PATH + '/(.*)/diff'
        reg = re.compile(pattern)
        layer_config = self._lo_client.inspect_container(container_name)['GraphDriver']['Data']
        layer_ids.append(reg.match(layer_config['LowerDir'].split(':')[0]).group(1)) if 'LowerDir' in layer_config.keys() else None
        layer_ids.append(reg.match(layer_config['UpperDir']).group(1))

        if self._c_layer_ids is None:
            self._c_layer_ids = layer_ids

    """
    Create symbolic links for container layer
    @params True | False
    """
    def create_symbolic_links(self):
        try: 
            for layer_id in self._c_layer_ids:
                base_path = self.identifier_path(layer_id)
                target_link = Path("../" + layer_id + "/diff")
                #base_path.touch()
                base_path.symlink_to(target_link)
        except Exception as e:
            print("create_symbolic_links args:", e.args)
            return False
        return True

    """
    Get relation between layer_id and short_identifier
    @return  Dict{Key: String image | container, Value: String short_identider}
    """
    def get_short_identifer_relations(self):
        identifiers = {}
        identifiers['image'] = [self.layer_short_identifier(i_layer_id) for i_layer_id in self._i_layer_ids]
        if self._c_layer_ids is not None:
            identifiers['container'] = [self.layer_short_identifier(c_layer_id) for c_layer_id in self._c_layer_ids if 'init' in c_layer_id]
        return identifiers

    """
    ReWrite lower layer in overlay setting
    @return True|False
    """
    def change_lower_layer_settings(self):
        identifier = self.get_short_identifer_relations()
        print(identifier)
        for layer_id in self._c_layer_ids:
            c_layer_path = self.overlays_path()/layer_id/'lower'
            setting = 'l/' + ':l/'.join(identifier['image']) if 'init' in str(c_layer_path) else 'l/' + ':l/'.join(identifier['image'] + identifier['container'])
            c_layer_path.write_text(setting)
        return True

    """
    Extract related file names of running container
        container running states:   /var/lib/docker/containers/<Con-ID>
        Layer files:                /var/lib/docker/overlay2/<rootfs-ID>, <rootfs-ID>-init
        Mount info:                 /var/lib/docker/image/overlay2/layerdb/mounts/<Con-ID>
    @params String container_name
    @return Array[String dir_name]
    """
    def extract_container_related_paths(self, container_name, layer_ids):
        return  (self.extract_container_related_artifacts(container_name, layer_ids)).values()

    """
    Return Dict, which stores container related paths with file name key
    @params String container_name
    @params Array[String layer_id]
    @returns Dict{ Key: String dir_name, Value: Path dir_name}
    """
    def extract_container_related_artifacts(self, container_name, layer_ids):
        running_state_dict = {}
        container_id = self.container_presence(container_name).id
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
        d = self.extract_container_related_artifacts(container_name, layer_ids)
        try:
            for tmp_d_name, d_name in d.items():
                shutil.move(str(targe_path/tmp_d_name), d_name)
            self.create_symbolic_links(layer_ids)
        except Exception as e:
            print("allocate_container_artifacts args:", e.args)
            return False
        return True

    def transfer_container_artifacts(self, container_name):
        dst_addr='10.24.129.91'
        layer_ids = self.get_container_layer_ids(container_name)
        dst_base_path = self.dst_target_dir_path(container_name)
        con_dir = self.extract_container_related_artifacts(container_name, layer_ids)
        for tmp_d_name, d_name in con_dir.items():
            #print(tmp_d_name)
            #print(d_name)
            src_path = str(d_name)
            dst_path = str(dst_base_path/tmp_d_name) + '/'
            is_success = Rsync.call(src_path, dst_path, 'miura', src_addr=None, dst_addr=dst_addr)

