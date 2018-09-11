# doc https://docker-py.readthedocs.io/en/stable/
import docker
from enum import Enum
import json
import subprocess as sp
import configparser
import pdb

from tool.common.logging.logger_factory import LoggerFactory
from settings.docker import DOCKER_BASIC_SETTINGS_PATH, CREDENTIALS_SETTING_PATH

class DockerBaseApi:

    def __init__(self):
        config = configparser.ConfigParser()
        config.read(DOCKER_BASIC_SETTINGS_PATH)
        self._client = docker.from_env()
        self._lo_client = docker.APIClient()
        self._basic_config = config
        self._logger = LoggerFactory.create_logger(self)

    @property
    def client(self):
        return self._client
    @property
    def lo_client(self):
        return self._lo_client

    @classmethod
    def reload_daemon(cls):
        cmd = 'sudo systemctl restart docker'
        try:
            sp.run(cmd.strip().split(' '), check=True)
            return True
        except Exception as e:
            print("args:", e.args)
            return False

    """
    Log in specific Dockerhub repo
    based on settings written in docker_hub.ini

    @return True|False
    """
    def login(self):
        config = configparser.ConfigParser()
        config.read(CREDENTIALS_SETTING_PATH)
        try:
            is_success = self._client.login(username=config['remote_docker_hub']['username'],
                                            password=config['remote_docker_hub']['password'],
                                            email=config['remote_docker_hub']['email'])
            return True if is_success is not None else False
        except docker.errors.APIError:
            print("Given account information is Unauthorized")
            return False

    """
    Check whether docker server is running

    @return True|False
    """
    def ping(self):
        return self._client.ping()

    """
    Pull docker image based on given two arguments

    @params String repository
    @params String tag="latest"
    @return Image
    """
    def pull(self, repository, tag="latest"):
        try: 
            image = self._client.images.pull(self.name_converter(repository, tag))
            return image
        except:
            return None

    """
    Push docker image based on the repository and tag

    @params String repository
    @params String tag
    @params True | False
    """
    def push(self, repository, tag="latest"):
        try:
            re = self._client.images.push(repository, tag=tag)
            if 'error' in re:
                raise
            else:
                return True
        except docker.errors.APIError:
            return False
        except:
            return False

    """
    Create Docker container specified name and tag,
    and basic options

    @params String i_name
    @params String version="latest"
    @params dict options(port, container_name)
    @return Container|None
    """
    def create(self, i_name, options, version="latest"):
        name_and_ver = self.name_converter(i_name, version)
        options = self.container_option(options)
        try:
            container = self._client.containers.create(name_and_ver, **options)
            return container
        except docker.errors.ImageNotFound:
            return None
        except docker.errors.APIError:
            return None

    """
    Commit Docker container

    @params String i_name
    @params String version
    @params String c_name
    @params image | None
    """
    def commit(self, c_name, repository=None, tag=None):
        try:
            container = self._client.containers.get(c_name)
            if repository and tag is not None:
                image = container.commit(repository=repository, tag=tag)
                return image
            else:
                image = container.commit
                return image
        except docker.errors.APIError:
            return None

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
    Checkpoint a running container

    @params String c_name
    @params String cp_name
    #@params Boolean leave_running
    @return True|False
    """
    def checkpoint(self, c_name, cp_name='checkpoint1', need_tmp_dir=False):
        if need_tmp_dir is True:
            cmd='docker checkpoint create --checkpoint-dir {cp_dir} {c_name} {cp_name}'.format(cp_dir=self._basic_config['checkpoint']['default_dir'], c_name=c_name, cp_name=cp_name)
        else:
            cmd='docker checkpoint create {c_name} {cp_name}'.format(c_name=c_name, cp_name=cp_name)
        try:
            result = sp.run(cmd.strip().split(" "), check=True)
            #print(result)
            return True
        except Exception as e:
            print("args:", e.args)
            return False

    """
    Restore a container from checkpoint data

    @params String c_name
    @params String cp_name='checkpoint'
    @return True|False
    """
    def restore(self, c_name, cp_name='checkpoint1', default_path=None):
        try:
            c= self.container_presence(c_name)
            if c is not None:
                if default_path is not None:
                    cmd='docker start --checkpoint {cp_name} --checkpoint-dir {cp_dir} {c_name}'.format(cp_name=cp_name, cp_dir=default_path, c_name=c_name)
                else:
                    cmd='docker start --checkpoint {cp_name} {c_name}'.format(cp_name=cp_name, c_name=c_name)
            else:
                raise
            result = sp.run(cmd.strip().split(" "), check=True)
            return True
        except Exception as e:
            print("args:", e.args)
            return False

    """
    Return default options of container initialization based on docker_settings
    The options include container default name and defaultmounting dir, and ipc_mode

    @params dict options(name, port(host, container))
    @return dict
    """
    def container_option(self, options):
        tmp_dir = self._basic_config['container']['volume_tmp_dir']
        volumes = {tmp_dir:  {'bind': tmp_dir, 'mode': 'rw'}}
        # set user defined values
        dict = { 'volumes': volumes,'ipc_mode': self._basic_config['container']['ipc_namespace']}
        dict['name'] = options['name'] if options['name'] is not None else self._basic_config['container']['default_name']
        if 'port' in options:
            dict['ports'] = { self.port_protocol_converter(options['port']['host']): options['port']['container'] }
        if 'volumes' in options:
            vo_options = {}
            for vo in volumes:
                vo_options[self._d_config['destination']['default_dir']] =  {'bind': vo.d_path, 'mode': 'rw'}
            dict['volumes'] = vo_options
        return dict

    """
    Convert name with version along with docker-py
    based on given two arguments

    @params String name
    @params String version
    @return String
    """
    def name_converter(self, name, version):
        return name + ':' + version

    """
    Convert prot with protocol along with docker-py

    @params Integer port
    @params String protocol='tcp'
    @return String
    """
    def port_protocol_converter(self, port, protocol='tcp'):
        return str(port) + '/' + protocol

