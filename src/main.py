import argparse
import configparser
from time import sleep
import pdb

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

def run_prop():
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

def run_con():
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
    #data = worker.run()
    #data = worker.run_involving_commit()
    data = worker.run_with_scr()

def codegen():
    from service import codegen
    codegen.run()

def cli_soc():
    from tool.socket.remote_com_client import RemoteComClient
    from tool.socket.remote_com_client import ClientMessageCode, ClientSignalCode

    cli = RemoteComClient()
    cli.connect()

    app_id = 0;

    ## =============== SRC-1 =================
    print("================= SRC-1====================")
    i_message_type = ClientMessageCode.DM_ASK_APP_INFO.value
    ret = cli.send_formalized_message(app_id, i_message_type)
    message = cli.read()
    buf_arr = message['payload'].split('|')[:1]
    rule_arr = message['payload'].split('|')[2:]

    ## =============== DST-1 =================
    # Init buf
    print("================= DST-1====================")
    i_message_type = ClientMessageCode.DM_INIT_BUF.value
    ret = cli.send_formalized_message(app_id, i_message_type, payload='/tmp/serv_buf0')
    dst_app_id = cli.read()['payload']
    print(dst_app_id)

    # Add all rules  skip rule because of testing same host
    i_message_type = ClientMessageCode.BULK_RULE_INS.value
    ret = cli.send_formalized_message(app_id, i_message_type, '|'.join(rule_arr))
    message = cli.read()

    ## =============== SRC-2 =================
    # Add all rules  skip rule because of testing same host
    print("================= SRC-2====================")
    i_message_type = ClientMessageCode.SERV_CHG_SIG.value
    ret = cli.send_formalized_message(app_id, i_message_type, payload=ClientSignalCode.SRC_MIG_REQUESTED.value)
    message = cli.read()

    # delete all rules
    i_message_type = ClientMessageCode.BULK_RULE_DEL.value
    ret = cli.send_formalized_message(app_id, i_message_type, '|'.join(rule_arr))
    message = cli.read()

    cli.close()

def sync():
    from tool.docker.docker_layer import DockerLayer
    from tool.docker.docker_container_extraction import DockerContainerExtraction
    i = DockerLayer()
    i.execute_remapping(args.image_name)

def debug():
    from tool.redis.redis_client import RedisClient
    from tool.socket.remote_com_client import RemoteComClient
    from tool.gRPC.grpc_client import RpcClient

    app_id = 0

    rpc_client = RpcClient()
    redis = RedisClient()

    last_packet_ids =  [ b_id.decode('utf-8') for b_id in redis.hvals(app_id)]
    code = rpc_client.update_buf_read_offset(app_id, last_packet_ids)
    print(redis.hvals(1))

if __name__ == "__main__":
    if args.program == 'rest':
        rest_server()
    if args.program == 'rpc':
        rpc_server()
    if args.program == 'codegen':
        codegen()
    if args.program == 'cli_soc':
        cli_soc()
    if args.program == 'sync':
        sync()
    if args.program == 'run_prop':
        run_prop()
    if args.program == 'run_con':
        run_con()
    if args.program == 'debug':
        debug()

