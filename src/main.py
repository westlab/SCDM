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
                    choices=('rest', 'rpc', 'codegen', 'run_prop', 'run_con', 'cli_soc', 'sync', 'debug'),
                    help='program that you want to run')
parser.add_argument('conf',
                    type=str,
                    help='directory path to config file')
parser.add_argument('image_name',type=str, help='image name', default='busybox')
parser.add_argument('container_name',type=str, help='container name', default='cr_test1')
parser.add_argument('bandwidth',type=int, help='bandwdith', default=0)
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
    version = 'latest'

    ports =[]
    dst_addr = '192.168.1.2'
    host = 'miura'
    checkpoint_option = dict(zip(checkpoint_option_keys, [ports]))
    migration_option = dict(zip(migration_option_keys, [host, dst_addr]))
    worker = MigrationWorker(cli=docker_api,
                             i_name=args.image_name, version=version, c_name=args.container_name,
                             m_opt=migration_option, c_opt=checkpoint_option, bandwidth=args.bandwidth)
    data = worker.run()
    #data = worker.run_involving_commit()

def codegen():
    from service import codegen
    codegen.run()

def cli_soc():
    from tool.socket.remote_com_client import RemoteComClient
    from tool.socket.remote_com_client import ClientMessageCode

    cli = RemoteComClient()
    cli.connect()

    app_id = 0;
    i_message_type = ClientMessageCode.DM_ASK_APP_INFO.value
    ret = cli.send_formalized_message(app_id, i_message_type)
    message = cli.read()
    buf_arr = message['payload'].split('|')[:1]
    rule_arr = message['payload'].split('|')[2:]

    ## delete all rules
    #i_message_type = ClientMessageCode.BULK_RULE_DEL.value
    #ret = cli.send_formalized_message(app_id, i_message_type, '|'.join(rule_arr))
    #message = cli.read()

    ### Add all rules 
    #i_message_type = ClientMessageCode.BULK_RULE_INS.value
    #ret = cli.send_formalized_message(app_id, i_message_type, '|'.join(rule_arr))
    #message = cli.read()

    # Init buf
    i_message_type = ClientMessageCode.DM_INIT_BUF.value
    ret = cli.send_formalized_message(app_id, i_message_type, payload='/tmp/serv_buf')
    message = cli.read()

    cli.close()

def sync():
    from tool.docker.docker_layer import DockerLayer
    from tool.docker.docker_container_extraction import DockerContainerExtraction
    i = DockerLayer()
    i.execute_remapping('busybox')

def debug():
    from tool.common.time_recorder import TimeRecorder, ProposedMigrationConst
    from tool.common.resource_recorder import ResourceRecorder
    from tool.common.disk_recorder import DiskRecorder
    from tool.docker.docker_container_extraction import DockerContainerExtraction, DockerVolume
    from tool.common.recorder.collectd_iostat_python.collectd_iostat_python import IOStat
    from tool.docker.docker_layer import DockerLayer
    import docker

    r_recorder = ResourceRecorder('{0}_{1}'.format('hoge', 'hogehoge'))
    r_recorder.insert_init_cond()
    r_recorder.track_on_subp()
    sleep(5)
    r_recorder.terminate_subp()
    r_recorder.write()

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

