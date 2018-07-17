import argparse
import configparser

from tool.common.logging.logger_factory import LoggerFactory

description = """
Rest server for Smart Community Docker Manger
"""
parser = argparse.ArgumentParser(description)
parser.add_argument('program',
                    type=str,
                    choices=('rest', 'rpc', 'codegen', 'client', 'cli_soc', 'sync'),
                    help='program that you want to run')
parser.add_argument('conf',
                    type=str,
                    help='directory path to config file')
args = parser.parse_args()
config = configparser.ConfigParser()
config.read(args.conf)

def rest_server():
    from flask import Flask
    from service.api import v1

    LoggerFactory.init()
    logger = LoggerFactory.create_logger('rest_server')
    port = config.getint('rest_server', 'port')
    debug = config.getboolean('rest_server','debug')

    app = Flask(__name__)
    # create url prefix for corresponding docker api
    app.register_blueprint(v1, url_prefix='/v1')
    logger.info("Rest server start")
    app.run(port=port, debug=debug, processes=3)

def rpc_server():
    from service import grpc_server

    LoggerFactory.init()
    logger = LoggerFactory.create_logger('rpc_server')
    addr = config['rpc_server']['addr']
    port = config.getint('rpc_server', 'port')

    logger.info("RPC server start")
    grpc_server.serve(addr, port)

def rpc_client():
    from tool.gRPC import grpc_client
    grpc_client.run()

def codegen():
    from service import codegen
    codegen.run()

def cli_soc():
    from tool.socket.remote_com_client import RemoteComClient
    from tool.socket.remote_com_client import ClientMessageCode

    cli = RemoteComClient()
    cli.connect()

    app_id = 0;
    i_message_type = ClientMessageCode.SIG_CHG.value
    ret = cli.send_formalized_message(app_id, i_message_type)
    print(ret)
    cli.read()
    cli.close()

def sync():
    from tool.docker.docker_layer import DockerLayer
    from tool.docker.docker_container_extraction import DockerContainerExtraction

    image_name = "busybox"
    c_name = "cr_test"

    #src
    i = DockerLayer()
    layer_ids = i.get_local_layer_ids(image_name)
    i.execute_remapping(image_name)
    ii = DockerContainerExtraction(c_name, layer_ids)
    ii.transfer_container_artifacts(c_name)

    #dst
    #c_id = None
    #i = DockerLayer()
    #layer_ids = i.get_local_layer_ids(image_name)
    #ii = DockerContainerExtraction(c_name, layer_ids, ['8ffabcbcba88c824b403e0ece2480eba869fd9a98135e94024cfccd1b761f400-init', '8ffabcbcba88c824b403e0ece2480eba869fd9a98135e94024cfccd1b761f400'])
    #ii.allocate_container_artifacts(c_name)
    #ii.get_container_layer_ids(c_name)

if __name__ == "__main__":
    if args.program == 'rest':
        rest_server()
    if args.program == 'rpc':
        rpc_server()
    if args.program == 'codegen':
        codegen()
    if args.program == 'client':
        rpc_client()
    if args.program == 'cli_soc':
        cli_soc()
    if args.program == 'sync':
        sync()
