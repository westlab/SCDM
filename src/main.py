import argparse
import configparser
from time import sleep

from tool.common.logging.logger_factory import LoggerFactory

description = """
Rest server for Smart Community Docker Manger
"""
parser = argparse.ArgumentParser(description)
parser.add_argument('program',
                    type=str,
                    choices=('rest', 'rpc', 'codegen', 'client', 'cli_soc', 'sync', 'debug'),
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
    from tool.migration_worker import MigrationWorker
    from tool.docker.docker_api import DockerApi

    docker_api = DockerApi()
    docker_api.login()

    checkpoint_option_keys = ['ports']
    migration_option_keys = ['host', 'dst_addr']
    image_name = 'busybox'
    container_name = 'cr_test'
    version = 'latest'

    ports =[]
    dst_addr = '192.168.1.2'
    host = 'miura'
    checkpoint_option = dict(zip(checkpoint_option_keys, [ports]))
    migration_option = dict(zip(migration_option_keys, [host, dst_addr]))
    worker = MigrationWorker(cli=docker_api,
                             i_name=image_name, version=version, c_name=container_name,
                             m_opt=migration_option, c_opt=checkpoint_option)
    data = worker.run()

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
    i = DockerLayer()
    i.execute_remapping('elasticsearch')

def debug():
    from tool.common.time_recorder import TimeRecorder, ProposedMigrationConst
    from tool.common.resource_recorder import ResourceRecorder
    from tool.common.disk_recorder import DiskRecorder
    from tool.docker.docker_container_extraction import DockerContainerExtraction, DockerVolume
    from tool.docker.docker_layer import DockerLayer
    import docker

    #r = ResourceRecorder()
    #r.insert_init_cond()
    #r.track_on_subp()
    #r.terminate_subp()
    #r.write()
    i_name = 'elasticsearch:latest'
    c_name = 'es1'
    c_id='7b288f57cfce55e9cc8cde12df1e9555b9c80e90df7dc0ccbaf915c6947c1c12'
    i = DockerLayer()
    i_layer_ids = i.get_local_layer_ids(i_name)
    c_layer_ids = i.get_container_layer_ids(c_name)
    extractor = DockerContainerExtraction(c_name, c_id, i_layer_ids, c_layer_ids)
    recorder = DiskRecorder(c_name)
    recorder.track_all(extractor)
    recorder.write()

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
    if args.program == 'debug':
        debug()

