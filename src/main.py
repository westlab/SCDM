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
                    choices=('rest', 'rpc', 'codegen', 'run_prop', 'run_con', 'run_scr', 'run_multi', 'cli_soc', 'sync', 'debug'),
                    help='program that you want to run')
parser.add_argument('conf',
                    type=str,
                    help='directory path to config file')
parser.add_argument('image_name',type=str, help='image name', default='busybox')
parser.add_argument('container_name',type=str, help='container name', default='cr_test1')
parser.add_argument('bandwidth',type=int, help='bandwdith', default=0)
parser.add_argument('packet_rate',type=int, help='bandwdith', default=1)
args = parser.parse_args()
config = configparser.ConfigParser()
config.read(args.conf)

from tool.docker.docker_api import DockerApi

docker_api = DockerApi()
docker_api.login()

def debug():
    from tool.redis.redis_client import RedisClient
    from tool.gRPC.grpc_client import RpcClient
    from tool.common.eval.buffer_logger import BufferLogger 
    from tool.socket.remote_com_client import SmartCommunityRouterAPI, ClientMessageCode, ClientMessageCode, RemoteComClient, ClientBufInfo

    dst_addr = '10.24.12.141' # miura-router1 
    checker = BufferLogger(dst_addr, "hoge")
    checker.run()

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
    dst_addr = '192.168.1.3'
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
    dst_addr = '192.168.1.3'
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
    dst_addr = '10.24.12.143' # miura-router3
    #dst_addr = '10.24.12.141' # miura-router1
    host = 'miura'
    checkpoint_option = dict(zip(checkpoint_option_keys, [ports]))
    migration_option = dict(zip(migration_option_keys, [host, dst_addr]))
    worker = MigrationWorker(cli=docker_api,
                             i_name=args.image_name, version=version, c_name=args.container_name,
                             m_opt=migration_option, c_opt=checkpoint_option, bandwidth=args.bandwidth, packet_rate=args.packet_rate)
    data = worker.run_with_scr()

def run_with_multi_scrs():
    from tool.migration_worker import MigrationWorker

    checkpoint_option_keys = ['ports']
    migration_option_keys = ['host', 'dst_addrs']
    version = 'latest'

    ports =[]
    dst_addrs = ['10.24.12.142', '10.24.12.143'] # miura-router2,3
    #dst_addr = '10.24.12.141' # miura-router1
    host = 'miura'
    checkpoint_option = dict(zip(checkpoint_option_keys, [ports]))
    migration_option = dict(zip(migration_option_keys, [host, dst_addrs]))
    worker = MigrationWorker(cli=docker_api,
                             i_name=args.image_name, version=version, c_name=args.container_name,
                             m_opt=migration_option, c_opt=checkpoint_option, bandwidth=args.bandwidth, packet_rate=args.packet_rate)
    data = worker.run_with_multi_scrs()

def codegen():
    from service import codegen
    codegen.run()

def cli_soc():
    from tool.socket.remote_com_client import RemoteComClient, SmartCommunityRouterAPI, ClientMessageCode,ClientBufInfo, ClientSignalCode, ScrDirection
    from tool.redis.redis_client import RedisClient
    from tool.gRPC.grpc_client import RpcClient
    from tool.common.extensions.rdict import rdict

    app_id=0
    dst_addr = "127.0.0.1"
    addr = "192.168.3.33"

    local_rpc_cli = RpcClient(dst_addr=dst_addr)
    redis_cli = RedisClient()
    rd = rdict(redis_cli.hgetall(app_id))
    C2S_info = {"direction": ScrDirection.C2S.value, "packet_id": rd["{0}.*{1}".format(ScrDirection.C2S.value, addr)][0]}
    S2C_info = {"direction": ScrDirection.S2C.value, "packet_id": rd["{0}.*{1}".format(ScrDirection.S2C.value, addr)][0]}
    packets = [C2S_info, S2C_info]
    print(packets)
    code = local_rpc_cli.update_buf_read_offset(app_id, packets)


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
    if args.program == 'run_multi':
        run_with_multi_scrs()
    if args.program == 'debug':
        debug()

