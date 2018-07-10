from concurrent import futures
import grpc
import time
import os

from settings.docker import CODE_SUCCESS, CODE_HAS_IMAGE, CODE_NO_IMAGE
from tool.docker.docker_api import DockerApi
from tool.common.logging.logger_factory import LoggerFactory

import tool.gRPC.docker_migration_pb2 as docker_migration_pb2
import tool.gRPC.docker_migration_pb2_grpc as docker_migration_pb2_grpc

_ONE_DAY_IN_SECONDS = 60 * 60 * 24

"""
Convert ContainerOptions to dict
for making easy to pass variable to next functon

@params ContainerOptions options
        (referred to ./tool/gRPC/docker_migration.proto)
@return dict (name, port)
"""
def dict_convetor(options):
    # O means that a developer does not specify a port number
    dict = {
        'name': options.container_name,
        'port': {'host': options.port.host, 'container': options.port.container} if options.port is not 0 else None,
    }
    return dict

class DockerMigrator(docker_migration_pb2_grpc.DockerMigratorServicer):
    """
    Provides methods that implement functionality of docker migration server.
    """
    def __init__(self):
        LoggerFactory.init()
        self._cli = DockerApi()
        self._logger = LoggerFactory.create_logger(self)

        self._cli.login()

    """
    Notify whether Dockerd is running or not
    Returns 0 if the server is running, but 122(errrno: Host is down) if not running.

    @params request
    @return Status(Integer code)
    """
    def PingDockerServer(self, request, context):
        self._logger.info("ping docker server")
        status_code = CODE_SUCCESS if self._cli.ping() is True else os.errno.EHOSTDOWN
        return docker_migration_pb2.Status(code=status_code)

    """
    Request migration from src node to dst node following tasks:
    1. Inspect local image and container belongings, and Return results
    2. Fetch Image if host has not the image
    3. Create the container from the image with given options

    @params DockerSummary(String image_name,
                          String version,
                          String container_name)
    @return Status(Integer code)
    """
    def RequestMigration(self, req, context):
        self._logger.info("Request migration")
        options = dict_convetor(req.options)
        result = self._cli.inspect_artifacts(i_name=req.image_name,
                                            version=req.version,
                                            c_name=req.options.container_name)
        first_code = CODE_HAS_IMAGE if result['image'] is True else CODE_NO_IMAGE
        yield  docker_migration_pb2.Status(code=first_code)

        self._logger.info("Fetch the image if host has not the image")
        second_code = CODE_SUCCESS if self._cli.fetch_image(name=req.image_name, version=req.version) is not None else os.errno.EHOSTDOWN
        yield docker_migration_pb2.Status(code=second_code)

        #TODO: 存在している場合には、削除/オプションを付け加えて再生成する必要あり
        self._logger.info("Create the container from the image with given options")
        c = self._cli.create(req.image_name, options, req.version)
        if c is not None:
            self._logger.info("Create the container from scratch")
            third_code = CODE_SUCCESS if c is not None else os.errno.EHOSTDOWN
            yield docker_migration_pb2.Status(code=third_code, c_id=c.id)
        else:
            self._logger.info("***Re-Create the container with the option***")
            third_code = os.errno.EHOSTDOWN
            yield docker_migration_pb2.Status(code=third_code)

    """
    Check checkpoint data sent from src to dst node
    and restore a container with the checkpoint
    """
    def RestoreContainer(self, req, context):
        self._logger.info("Restore Container")
        code = CODE_SUCCESS if self._cli.restore(req.c_name) is True else os.errno.EHOSTDOWN
        return docker_migration_pb2.Status(code=code)

    """
    Inspect local image and container artifacts, and Return results
    @params DockerSummary(String image_name,
                          String version,
                          String container_name)
    @return Status(Integer code):
    """
    def InspectArtifacts(self, req, context):
        self._logger.info("Inspect local image and container artifacts")
        result = self._cli.inspect_artifacts(i_name=req.image_name,
                                            version=req.version,
                                            c_name=req.options.container_name)
        code = CODE_HAS_IMAGE if result['image'] is True else CODE_NO_IMAGE
        return docker_migration_pb2.Status(code=code)

    """
    Create a container create,
    and if the host has not the container, host will pull it
    @params DockerSummary(String image_name,
                          String version,
                          String container_name)
    @return Status(Integer code):
    """
    def CreateContainer(self, req, context):
        self._logger.info("Create Container")
        options = dict_convetor(req.options)
        pulled_image = self._cli.fetch_image(name=req.image_name, version=req.version)

        if pulled_image is not None:
            self._logger.info("Create the container from the image with given options")
            c = self._cli.create(req.image_name, options, req.version)
            if c is not None:
                self._logger.info("Create the container from scratch")
                code = CODE_SUCCESS if c is not None else os.errno.EHOSTDOWN
                return docker_migration_pb2.Status(code=code, c_id=c.id)
            else:
                self._logger.info("***Re-Create the container with the option***")
                code = os.errno.EHOSTDOWN
                return docker_migration_pb2.Status(code=code)
        else:
            self._logger.info("Cannot get the specified image")
            code =  os.errno.EHOSTDOWN
            return docker_migration_pb2.Status(code=code)

"""
Start gRPC server based on given addr and port number.

@params String addr
@params Integer port
"""
def serve(addr, port):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
    docker_migration_pb2_grpc.add_DockerMigratorServicer_to_server(DockerMigrator(), server)
    addr_with_port = addr + ':' + str(port)
    server.add_insecure_port(addr_with_port)
    server.start()

    try:
        while True:
            time.sleep(_ONE_DAY_IN_SECONDS)
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == '__main__':
    serve()
