import argparse
import configparser

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
    dst_addr = '10.24.129.91'
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

    image_name = "tatsuki/test"
    c_name = "cr_test"

    c_id = '546fd2f98b5a4f54c8824c007f1d5a4cee5a6ed762e24bc16382ed72495fd94d'
    is_success = DockerContainerExtraction.create_target_tmp_dir(c_id)
    print(is_success)

    #src
    #i = DockerLayer()
    #dst_addr='10.24.129.91'
    #layer_ids = i.get_local_layer_ids(image_name)
    #i.execute_remapping(image_name)
    #ii = DockerContainerExtraction(c_name, layer_ids)
    #ii.transfer_container_artifacts(c_name)

    #dst
    #c_id = '97b8c43f61b30f83bc7a7ddb4302aa42cb6e682f9032159ea6b61c315c88a863'
    #i = DockerLayer()
    #layer_ids = i.get_local_layer_ids(image_name)
    #ii = DockerContainerExtraction(c_name, layer_ids, c_id=c_id, c_layer_ids=['258ff3804982fa669a511fba24dff99a5a0553ef208896bfde1139b5a4128026-init', '258ff3804982fa669a511fba24dff99a5a0553ef208896bfde1139b5a4128026'])
    #ii.allocate_container_artifacts()
    #ii.get_container_layer_ids(c_name)

def debug():
    from tool.common.time_recorder import TimeRecorder, ProposedMigrationConst
    r = TimeRecorder('hoge')
    r.track(ProposedMigrationConst.MIGRATION_TIME)
    r.track(ProposedMigrationConst.SERVICE_DOWNTIME)
    r.track(ProposedMigrationConst.CHECKPOINT)
    r.track(ProposedMigrationConst.CHECKPOINT)
    r.track(ProposedMigrationConst.SERVICE_DOWNTIME)
    r.track(ProposedMigrationConst.MIGRATION_TIME)
    r.write()

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
