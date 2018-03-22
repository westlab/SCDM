from concurrent import futures
import grpc
import time
import os

from settings.docker import CODE_SUCCESS, CODE_HAS_IMAGE, CODE_NO_IMAGE
from tool.docker_api import DockerApi

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
def dict_conveter(options):
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
        self._cli = DockerApi()

    """
    Notify whether Dockerd is running or not
    Returns 0 if the server is running, but 122(errrno: Host is down) if not running.

    @params request
    @return Status(Integer code)
    """
    def PingDockerServer(self, request, context):
        print("PingDockerServer")
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
        print("RequestMigration")
        result = self._cli.inspect_material(i_name=req.image_name,
                                            version=req.version,
                                            c_name=req.options.container_name)
        options = dict_conveter(req.options)
        print("Inspect local image and container belongings")
        first_code = CODE_HAS_IMAGE if result['image'] is True else CODE_NO_IMAGE
        yield  docker_migration_pb2.Status(code=first_code)
        print("Fetch the Image if host has not the image")
        second_code = CODE_SUCCESS if self._cli.fetch_image(name=req.image_name, version=req.version) is not None else os.errno.EHOSTDOWN
        yield docker_migration_pb2.Status(code=second_code)
        print("Create the container from the image with given options")
        c = self._cli.create(req.image_name, options, req.version)
        third_code = CODE_SUCCESS if c is not None else os.errno.EHOSTDOWN
        yield docker_migration_pb2.Status(code=third_code)

    """
    Check checkpoint data sent from src to dst node
    and restore a container with the checkpoint
    """
    def RestoreContainer(self, req, context):
        print("RestoreContainer")
        code = CODE_SUCCESS if self._cli.restore(req.c_name) is True else os.errno.EHOSTDOWN
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
