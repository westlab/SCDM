from concurrent import futures
import grpc
import time

from tool.docker_api import DockerApi

import tool.gRPC.docker_migration_pb2 as docker_migration_pb2
import tool.gRPC.docker_migration_pb2_grpc as docker_migration_pb2_grpc

_ONE_DAY_IN_SECONDS = 60 * 60 * 24

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
        status_code = 0 if self._cli.ping() is True else 112
        return docker_migration_pb2.Status(code=status_code)

    """
    Request migration from src node to dst node
    Returns status code when inspecting image
    and container situation and finishing download the image
    , and starting the container.

    @params DockerSummary(String image_name,
                          String version,
                          String container_name)
    @return Status(Integer code)
    """
    def RequestMigration(self, req, context):
        print("RequestMigration")
        # TODO: return first sth
        result = self._cli.inspect_material(i_name=req.image_name,
                                            version=req.version,
                                            c_name=req.container_name)

        second_code = 0 if self._cli.fetch_image(name=req.image_name, version=req.version) is not None else 112
        yield docker_migration_pb2.Status(code=second_code)

        c = self._cli.create(name=req.image_name, c_name=req.container_name, version=req.version)
        third_code = 0 if c is not None else 112
        yield docker_migration_pb2.Status(code=third_code)

    """
    Send checkpoint data from src to dst node
    Returns status code for representing finish of restoring an app
    """
def SendCheckpoint(self, request, context):
        print("SendCheckpoint")
        status_codes = [0, 1]
        for code in status_codes:
            yield docker_migration_pb2.Status(code=code)

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
