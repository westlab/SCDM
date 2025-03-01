import docker
import re
import shutil
import json
import os
from enum import Enum
from pathlib import Path
import pdb # for debug

from tool.docker.docker_base_api import DockerBaseApi
from tool.common.rsync import Rsync
from settings.docker import OVERLAYER2_DIR_PATH, LAYERDB_DIR_PATH, IMAGEDB_DIR_PATH, CONTAINER_CONF_PATH, DST_TARGET_DIR_PATH

"""
Extract components of Docker container
"""

class VolumeType(Enum):
    volume = 1
    bind = 2

class DockerVolume(DockerBaseApi):
    def __init__(self, kind, host_path, docker_path, cli=None, name=None):
        super().__init__()
        self._kind = VolumeType.volume if kind == 'volume' else VolumeType.bind
        self._h_path = Path(host_path)
        self._d_path = Path(docker_path)
        self._lo_client = cli if cli is not None else docker.APIClient()  

    @property
    def kind(self):
        return self._kind
    @property
    def d_path(self):
        return self._d_path
    @property
    def h_path(self):
        return self._h_path
    @classmethod
    def collect_volumes(cls, c_name, lo_cli, cli):
        arr_volumes = []
        try:
            if cli.containers.get(c_name):
                volumes = lo_cli.inspect_container(c_name)['Mounts']
                if volumes:
                    for vo in volumes:
                        arr_volumes.append(cls(vo['Type'], vo['Source'], vo['Destination'], lo_cli))
            return arr_volumes
        except docker.errors.NotFound:
            return arr_volumes

    """
    Initialize volume instance wihtout docker api
    @params String c_name
    @params docker cli
    @params DockerMigration_pb2 Volume <String kind, String host_path, String docker_path> volumes
    """
    @classmethod
    def initialize_all_without_api(cls, c_name, cli, volumes):
        arr_volumes = []
        for vo in volumes:
            arr_volumes.append(cls(kind=vo.kind, host_path=vo.h_path, docker_path=vo.d_path, cli=cli))
        return arr_volumes

    def hash_converter(self):
        return {'kind': self._kind.name, 'h_path': str(self._h_path), 'd_path': str(self._d_path)}

class DockerContainerExtraction(DockerBaseApi):
    def __init__(self, c_name, c_id, i_layer_ids, c_layer_ids, volumes=None):
        super().__init__()
        cli = docker.APIClient()

        self._lo_client = cli
        self._c_name = c_name
        self._c_id = c_id
        self._i_layer_ids = i_layer_ids
        self._c_layer_ids = c_layer_ids
        self._volumes = DockerVolume.initialize_all_without_api(c_name,cli, volumes) if volumes else DockerVolume.collect_volumes(c_name, cli, self._client)

    @property
    def c_name(self):
        return self._c_name
    @property
    def c_id(self):
        return self._c_id
    @property
    def i_layer_ids(self):
        return self._i_layer_ids
    @property
    def c_layer_ids(self):
        return self._c_layer_ids
    @property
    def volumes(self):
        return self._volumes

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

    def dst_target_dir_path(self):
        if self._c_id is None:
            self._c_id = self.container_presence(self._c_name).id
        return Path(DST_TARGET_DIR_PATH + '/' + self._c_id)

    def dst_target_dir_dict(self):
        return dict.fromkeys(['rootfs', 'rootfs-init', 'mounts','containers'])

    def checkpoint_path(self, container_id):
        return self.container_settings_path(container_id)/'checkpoints'

    """
    Create temporary directory for storing container artifacts
    """
    @classmethod
    def create_target_tmp_dir(cls, c_id):
        base_path = Path(DST_TARGET_DIR_PATH)
        if not base_path.exists():
            base_path.mkdir()
            os.chmod(str(base_path), 0o777)
        if (base_path/c_id).exists():
            return True
        try:
            (base_path/c_id).mkdir(mode=0o777)
            os.chmod(str((base_path/c_id)), 0o777)
        except Exception as e:
            print("create_tmp_target_dir args:", e.args)
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
    Extract related file names of running container
        container running states:   /var/lib/docker/containers/<Con-ID>
        Layer files:                /var/lib/docker/overlay2/<rootfs-ID>, <rootfs-ID>-init
        Mount info:                 /var/lib/docker/image/overlay2/layerdb/mounts/<Con-ID>
        volumes:                    /var/lib/docker/volumes/<vol-name>/_data
    @params String container_name
    @return Array[String dir_name]
    """
    def extract_container_related_paths(self):
        return  (self.extract_container_related_artifacts()).values()

    """
    Return Dict, which stores container related paths with file name key
    @returns Dict{ Key: String dir_name, Value: Path dir_name}
    """
    def extract_container_related_artifacts(self):
        running_state_dict = self.dst_target_dir_dict()
        running_state_dict['rootfs'] = [ self.overlays_path()/layer_id for layer_id in self._c_layer_ids if (self.overlays_path()/layer_id).name.isalnum()][0]
        running_state_dict['rootfs-init'] = [ self.overlays_path()/layer_id for layer_id in self._c_layer_ids if not (self.overlays_path()/layer_id).name.isalnum()][0]
        running_state_dict['containers'] = self.container_settings_path(self._c_id)
        running_state_dict['mounts'] = self.container_mount_settings_path()/self._c_id

        for i in range(len(self._volumes)):
            if self._volumes[i].kind.value == VolumeType.volume.value:
                running_state_dict['volumes_' + str(i)] = self._volumes[i]._h_path

        return running_state_dict

    def transfer_container_artifacts(self, dst_addr):
        dst_base_path = self.dst_target_dir_path()
        con_dir = self.extract_container_related_artifacts()
        arr = []
        
        for tmp_d_name, d_name in con_dir.items():
            src_path = str(d_name)
            dst_path = str(dst_base_path/tmp_d_name) + '/'
            is_success = Rsync.call(src_path, dst_path, 'miura', src_addr=None, dst_addr=dst_addr)
            arr.append(is_success)
        if all(arr):
            return True
        else:
            return False

    """
    ReWrite lower layer in overlay setting
    @return True|False
    """
    def change_lower_layer_settings(self):
        identifier = self.get_short_identifer_relations()
        for layer_id in self._c_layer_ids:
            c_layer_path = self.overlays_path()/layer_id/'lower'
            setting = 'l/' + ':l/'.join(identifier['image']) if 'init' in str(c_layer_path) else 'l/' + ':l/'.join(identifier['image'] + identifier['container'])
            c_layer_path.write_text(setting)
        return True

    """
    Create symbolic links for container layer
    @params True | False
    """
    def create_symbolic_links(self):
        try:
            for layer_id in self._c_layer_ids:
                base_path = self.identifier_path(layer_id)
                target_link = Path("../" + layer_id + "/diff")
                base_path.symlink_to(target_link)
        except Exception as e:
            print("create_symbolic_links args:", e.args)
            return False
        return True

    """
    Allocate tranfered files to original location
    @return True | False
    """
    def allocate_container_artifacts(self):
        target_path = self.dst_target_dir_path()
        d = self.extract_container_related_artifacts()
        try:
            for tmp_d_name, d_name in d.items():
                shutil.move(str(target_path/tmp_d_name/d_name.name), str(d_name))
            self.create_symbolic_links()
            self.change_lower_layer_settings()
        except Exception as e:
            print("allocate_container_artifacts args:", e.args)
            return False
        return True

