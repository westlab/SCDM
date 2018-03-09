import grpc
import tool.gRPC.helloworld_pb2 as helloworld_pb2
import tool.gRPC.helloworld_pb2_grpc as helloworld_pb2_grpc

def run():
    channel = grpc.insecure_channel('localhost:50051')
    stub = helloworld_pb2_grpc.GreeterStub(channel)
    response = stub.SayHello(helloworld_pb2.HelloRequest(name='you'))
    print("Greeter client received: " + response.message)

if __name__ == '__main__':
    run()