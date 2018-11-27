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
                    choices=('rest', 'rpc', 'codegen', 'run_prop', 'run_con', 'run_scr', 'cli_soc', 'sync', 'debug'),
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

from tool.docker.docker_api import DockerApi

docker_api = DockerApi()
docker_api.login()

def debug():
    from tool.redis.redis_client import RedisClient
    from tool.gRPC.grpc_client import RpcClient
    from tool.socket.remote_com_client import SmartCommunityRouterAPI, ClientMessageCode, ClientMessageCode, RemoteComClient, ClientBufInfo

    dst_addr = '10.24.128.194' # miura-router1 
    local_rpc_cli = RpcClient()#dst_addr=dst_addr)
    remote_rpc_cli = RpcClient(dst_addr=dst_addr)
    redis = RedisClient()

    app_id = 0
    print("========get_buf_info==========")
    local_rpc_cli.ping()
    remote_rpc_cli.ping()
    dst_first_packet_id = remote_rpc_cli.get_buf_info(app_id, kind=ClientBufInfo.BUF_FIRST.value)  #in this case packet_id
    print(dst_first_packet_id)
    #print("========packet_arrival==========")
    print(local_rpc_cli.check_packet_arrival(app_id, dst_first_packet_id))
    print("========get last buffer info==========")
    src_last_packet_id = local_rpc_cli.get_buf_info(app_id, kind=ClientBufInfo.BUF_LAST.value)  #in this case packet_id
    print(src_last_packet_id)
    print("========packet_arrival==========")
    print(remote_rpc_cli.check_packet_arrival(app_id, src_last_packet_id))  #in this case packet_id
    print('fin')

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
    grpc_server.serve(addr, port, docker_api)

def run_prop():
    from tool.migration_worker import MigrationWorker

    checkpoint_option_keys = ['ports']
    migration_option_keys = ['host', 'dst_addr']
    version = 'latest'

    ports =[]
    dst_addr = '192.168.11.2'
    host = 'miura'
    checkpoint_option = dict(zip(checkpoint_option_keys, [ports]))
    migration_option = dict(zip(migration_option_keys, [host, dst_addr]))
    worker = MigrationWorker(cli=docker_api, i_name=args.image_name, version=version, c_name=args.container_name,
                             m_opt=migration_option, c_opt=checkpoint_option, bandwidth=args.bandwidth)
    data = worker.run()

def run_con():
    from tool.migration_worker import MigrationWorker

    checkpoint_option_keys = ['ports']
    migration_option_keys = ['host', 'dst_addr']
    version = 'latest'

    ports =[]
    dst_addr = '192.168.11.2'
    host = 'miura'
    checkpoint_option = dict(zip(checkpoint_option_keys, [ports]))
    migration_option = dict(zip(migration_option_keys, [host, dst_addr]))
    worker = MigrationWorker(cli=docker_api,
                             i_name=args.image_name, version=version, c_name=args.container_name,
                             m_opt=migration_option, c_opt=checkpoint_option, bandwidth=args.bandwidth)
    data = worker.run_involving_commit()


def run_with_scr():
    from tool.migration_worker import MigrationWorker

    checkpoint_option_keys = ['ports']
    migration_option_keys = ['host', 'dst_addr']
    version = 'latest'

    ports =[]
    dst_addr = '10.24.128.194' # miura-router1 
    host = 'miura'
    checkpoint_option = dict(zip(checkpoint_option_keys, [ports]))
    migration_option = dict(zip(migration_option_keys, [host, dst_addr]))
    worker = MigrationWorker(cli=docker_api,
                             i_name=args.image_name, version=version, c_name=args.container_name,
                             m_opt=migration_option, c_opt=checkpoint_option, bandwidth=args.bandwidth)
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

    # =============== SRC-1 =================
    print("================= SRC-1====================")
    i_message_type = ClientMessageCode.DM_ASK_APP_INFO.value
    ret = cli.send_formalized_message(app_id, i_message_type)
    message = cli.read()
    buf_arr = message['payload'].split('|')[:1]
    existing_rule_arr = message['payload'].split('|')[2:]
    print(existing_rule_arr)

    ## =============== DST-1 =================
    # Init buf
    #print("================= DST-1====================")
    #i_message_type = ClientMessageCode.DM_INIT_BUF.value
    #ret = cli.send_formalized_message(app_id, i_message_type, payload='/tmp/serv_buf0')
    #dst_app_id = cli.read()['payload']

    print("================= SRC-2====================")
    #i_message_type = ClientMessageCode.SERV_CHG_SIG.value
    #ret = cli.send_formalized_message(app_id, i_message_type, payload=ClientSignalCode.SRC_MIG_REQUESTED.value)
    #message = cli.read()
    # delete all rules

    # Add all rules  skip rule because of testing same host
    rule_arr = ['601:/Node/','602:/Hoge/','603:/FUGA/','604:/MIURA/','605:/TATSUKI/', '606:/KEIO/']
    i_message_type = ClientMessageCode.BULK_RULE_INS.value
    ret = cli.send_formalized_message(app_id, i_message_type, '|'.join(rule_arr))
    message = cli.read()


    pdb.set_trace()

    i_message_type = ClientMessageCode.BULK_RULE_DEL.value
    ret = cli.send_formalized_message(app_id, i_message_type, '|'.join(existing_rule_arr))
    message = cli.read()


    sleep(10)

    ## =============== SRC-2 =================
    # Add all rules  skip rule because of testing same host

    ## delete all rules
    #i_message_type = ClientMessageCode.BULK_RULE_DEL.value
    #ret = cli.send_formalized_message(app_id, i_message_type, '|'.join(rule_arr))
    #message = cli.read()

    cli.close()

def sync():
    from tool.docker.docker_layer import DockerLayer
    from tool.docker.docker_container_extraction import DockerContainerExtraction
    i = DockerLayer()
    i.execute_remapping(args.image_name)

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
    if args.program == 'cli_soc':
        cli_soc()
    if args.program == 'sync':
        sync()
    if args.program == 'run_prop':
        run_prop()
    if args.program == 'run_con':
        run_con()
    if args.program == 'run_scr':
        run_with_scr()
    if args.program == 'debug':
        debug()

