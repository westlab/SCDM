import grpc
import tool.gRPC.docker_migration_pb2 as docker_migration_pb2
import tool.gRPC.docker_migration_pb2_grpc as docker_migration_pb2_grpc

def run():
    channel = grpc.insecure_channel('localhost:50051')
    stub = docker_migration_pb2_grpc.DockerMigratorStub(channel)
    stub.PingDockerServer(docker_migration_pb2.Signal(name='default'))
    stub.SendCheckpoint(docker_migration_pb2.CheckpointSummary(cp_name="hoge", cp_path="hoghoge"))
    gen = stub.RequestMigration(docker_migration_pb2.DockerSummary(image_name="busybox",
                                                                   version="latest",
                                                                   container_name="hogehogehogehoge"))
    gen.next()
    gen.next()
    gen.next()

if __name__ == '__main__':
    run()