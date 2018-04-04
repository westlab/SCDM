import grpc
import tool.gRPC.docker_migration_pb2 as docker_migration_pb2
import tool.gRPC.docker_migration_pb2_grpc as docker_migration_pb2_grpc

class RpcClient:
    def __init__(self, dst_addr='localhost', port=50051):
        dst = '{0}:{1}'.format(dst_addr, str(port))
        channel = grpc.insecure_channel(dst)
        self._stub = docker_migration_pb2_grpc.DockerMigratorStub(channel)

    def ping(self):
        status = self._stub.PingDockerServer(docker_migration_pb2.Signal(name='default'))
        return status.code

    def restore(self, c_name):
        status = self._stub.RestoreContainer(docker_migration_pb2.CheckpointSummary(c_name=c_name))
        return status.code

    def inspect(self, i_name, version, c_name):
        port = docker_migration_pb2.Port(host=9999, container=9999)
        c_opt = docker_migration_pb2.ContainerOptions(container_name=c_name, port=port)
        status = self._stub.InspectArtifacts(docker_migration_pb2.DockerSummary(image_name=i_name, version=version, options=c_opt))
        return status.code

    def create_container(self, i_name, version, c_name):
        port = docker_migration_pb2.Port(host=9999, container=9999)
        c_opt = docker_migration_pb2.ContainerOptions(container_name=c_name, port=port)
        status_with_c_id = self._stub.CreateContainer(docker_migration_pb2.DockerSummary(image_name=i_name, version=version, options=c_opt))
        return  status_with_c_id


    def request_migration(self, i_name, version, c_name, c_opt):
        port = docker_migration_pb2.Port(host=9999, container=9999)
        c_opt = docker_migration_pb2.ContainerOptions(container_name=c_name, port=port)
        gen = self._stub.RequestMigration(docker_migration_pb2.DockerSummary(image_name=i_name,
                                                                             version=version,
                                                                             options=c_opt))
        return gen

