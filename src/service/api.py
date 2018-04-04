from flask import Blueprint, request, json, Response

from tool.docker_api import DockerApi
from tool.migration_worker import MigrationWorker
from tool.common.time_recorder import TimeRecorder

v1 = Blueprint('v1', __name__)
docker_api = DockerApi()
docker_api.login()

@v1.route("/test")
def test():
    repo = 'tatsukitatsuki/busybox'
    tag = '20180403_185150'
    hoge = docker_api.push(repo, tag)
    print(hoge)
    return "hello from api.py"

@v1.route("/docker/check", methods=['GET'])
def check():
    recorder = TimeRecorder('check', ['total_time', 'check'])
    recorder.track(0)
    recorder.track(1)
    is_alive = docker_api.ping()
    recorder.track(1)
    recorder.track(0)
    recorder.write()
    return Response(json.dumps({'server': is_alive}),
                    mimetype='application/json')

@v1.route("/ping")
def ping():
    from tool.gRPC.grpc_client import RpcClient
    rpc_client = RpcClient("10.24.129.91")
    rpc_client.ping()
    return "hello from api.py"


@v1.route("/docker/inspect", methods=['GET'])
def inspect():
    # TODO: 例外処理の追加 (no parameterの場合)
    image_name = request.args.get('image_name')
    version = request.args.get('version')
    container_name = request.args.get('container_name')
    data = docker_api.inspect_artifacts(image_name, version, container_name)
    return Response(json.dumps(data),
                    mimetype='application/json')

# TODO: 非同期にするかどうか/同期型にするかどうか
@v1.route("/docker/migrate", methods=['POST'])
def migrate():
    checkpoint_option_keys = ['ports']
    migration_option_keys = ['host', 'dst_addr']
    image_name = request.form['image_name']
    container_name = request.form['container_name']
    version = request.form.get('version', 'latest')
    checkpoint_name = request.form.get('checkpoint_name', 'checkpoint')
    # checkpoint options
    # TODO: portがうまく取得できない request, recieve側どちらが問題かは不明
    ports = request.form.getlist('ports', [])
    checkpoint_option = dict(zip(checkpoint_option_keys, [ports]))
    # migration options
    dst_addr = request.form[migration_option_keys[1]]
    host = request.form.get(migration_option_keys[0], 'host')
    migration_option = dict(zip(migration_option_keys, [host, dst_addr]))


    worker = MigrationWorker(cli=docker_api,
                             i_name=image_name, version=version, c_name=container_name,
                             cp_name=checkpoint_name,
                             m_opt=migration_option, c_opt=checkpoint_option)
    data = worker.run()
    return Response(json.dumps(data['data']),
                    status=data['status'],
                    mimetype='application/json'
                    )

