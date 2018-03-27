from grpc.tools import protoc
import os

def run():
    protoc.main(
        (
            '-I.',
            '--python_out=.',
            '--grpc_python_out=.',
            './src/tool/gRPC/docker_migration.proto'
        )
    )
    replace()

def replace():
    DEFAULT_PATH='./src/tool/gRPC'
    GRPC_FILENAME = 'docker_migration_pb2_grpc.py'
    GENERATED_FILE_PATH = '{0}/{1}'.format(DEFAULT_PATH, GRPC_FILENAME)
    TMP_FILE_PATH = '{0}/tmp.py'.format(DEFAULT_PATH)
    try:
        if os.path.isfile(GENERATED_FILE_PATH):
            with open(GENERATED_FILE_PATH) as src, open(TMP_FILE_PATH, 'a') as dst:
                data = src.read()
                tmp_data = data.replace('src.tool.gRPC', 'tool.gRPC', 1)
                dst.write(tmp_data)

                if os.path.isfile(TMP_FILE_PATH):
                    os.remove(GENERATED_FILE_PATH)
                    os.rename(TMP_FILE_PATH, GENERATED_FILE_PATH)
                else:
                    raise Exception

        else:
            raise Exception
    except:
        print("Please create gRPC file correctly")

