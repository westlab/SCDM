import grpc
import tool.gRPC.docker_migration_pb2 as docker_migration_pb2
import tool.gRPC.docker_migration_pb2_grpc as docker_migration_pb2_grpc

def run():
    channel = grpc.insecure_channel('localhost:50051')
    stub = docker_migration_pb2_grpc.DockerMigratorStub(channel)
    stub.PingDockerServer(docker_migration_pb2.Signal(name='default'))
    stub.RestoreContainer(docker_migration_pb2.CheckpointSummary(c_name="cr_test"))

    port = docker_migration_pb2.Port(host=9999, container=9999)
    options = docker_migration_pb2.ContainerOptions(container_name="hogehogehoge", port=port)
    #gen = stub.RequestMigration(docker_migration_pb2.DockerSummary(image_name="busybox",
    #                                                               version="latest",
    #                                                               options=options))
    #gen.next()
    #gen.next()
    #gen.next()

if __name__ == '__main__':
    run()
