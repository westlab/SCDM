from grpc.tools import protoc

def run():
    protoc.main(
        (
            '-I.',
            '--python_out=.',
            '--grpc_python_out=.',
            './src/tool/gRPC/docker_migration.proto'
        )
    )


    # TODO: helloworldのgrpc側のcodeのpathの書き換えの必要性あり
    # http://greennoah.hatenablog.jp/entry/20090216/1234784592
