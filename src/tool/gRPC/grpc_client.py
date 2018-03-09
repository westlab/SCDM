import grpc
import tool.gRPC.docker_migration_pb2 as docker_migration_pb2
import tool.gRPC.docker_migration_pb2_grpc as docker_migration_pb2_grpc

def run():
    channel = grpc.insecure_channel('localhost:50051')
    stub = docker_migration_pb2_grpc.DockerMigratorStub(channel)
    stub.PingDockerServer(docker_migration_pb2.Signal(name='you'))
    stub.RequestMigration(docker_migration_pb2.DockerSummary(image_name="hoge", version="2", container_name="hoge2"))
    stub.SendCheckpoint(docker_migration_pb2.CheckpointSummary(cp_name="hoge", cp_path="hoghoge"))

if __name__ == '__main__':
    run()