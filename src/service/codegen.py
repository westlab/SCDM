from grpc.tools import protoc

def run():
    protoc.main(
        (
            '-I.',
            '--python_out=.',
            '--grpc_python_out=.',
            './src/tool/gRPC/helloworld.proto'
        )
    )


    # TODO: helloworldのgrpc側のcodeのpathの書き換えの必要性あり
