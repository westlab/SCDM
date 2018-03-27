import argparse
import configparser

from tool.common.logging.logger_factory import LoggerFactory

description = """
Rest server for Smart Community Docker Manger
"""
parser = argparse.ArgumentParser(description)
parser.add_argument('program',
                    type=str,
                    choices=('rest', 'rpc', 'codegen', 'client'),
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

    port = config.getint('rpc_server', 'port')
    addr = "localhost"
    grpc_server.serve(addr, port)

def rpc_client():
    from tool.gRPC import grpc_client
    grpc_client.run()

def codegen():
    from service import codegen
    codegen.run()

if __name__ == "__main__":
    if args.program == 'rest':
        rest_server()
    if args.program == 'rpc':
        rpc_server()
    if args.program == 'codegen':
        codegen()
    if args.program == 'client':
        rpc_client()
