import grpc
import tool.gRPC.docker_migration_pb2 as docker_migration_pb2
import tool.gRPC.docker_migration_pb2_grpc as docker_migration_pb2_grpc

def run():
    channel = grpc.insecure_channel('localhost:50051')
    print("===============================Greeter client received:===========================================")
    stub = docker_migration_pb2_grpc.DockerMigratorStub(channel)
    print("===============================Greeter client received:===========================================")
    stub.PingDockerServer(docker_migration_pb2.Signal(name='you'))

if __name__ == '__main__':
    run()