from flask import Blueprint, request, json, Response

from tool.docker.docker_api import DockerApi
from tool.docker.docker_layer import DockerLayer
from tool.migration_worker import MigrationWorker
import pdb
import json

v1 = Blueprint('v1', __name__)
docker_api = DockerApi()
docker_api.login()
DockerLayer.execute_all_remapping()

@v1.route("/docker/check", methods=['GET'])
def check():
    is_alive = docker_api.ping()
    return Response(json.dumps({'server': is_alive}),
                    mimetype='application/json')

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
@v1.route("/docker/migrate/<method>", methods=['POST'])
def migrate(method):
    data = request.json

    # have optional values
    res = {}
    checkpoint_option_keys = ['port']
    migration_option_keys = ['host', 'dst_addr', 'pkt_dst_addr']
    version = data['version'] if 'version' in data else 'latest'
    ports = data['port'] if 'port' in data else []
    host = data['host'] if 'host' in data else 'host'

    # Give values
    try:
        dst_addr = data['dst_addr']
        pkt_dst_addr = data['pkt_dst_addr'] if method == 'cgm' else ""

        checkpoint_option = dict(zip(checkpoint_option_keys, [ports]))
        migration_option = dict(zip(migration_option_keys, [host, dst_addr, pkt_dst_addr]))
        worker = MigrationWorker(cli=docker_api,
                                i_name=data['image_name'], 
                                version=version, 
                                c_name=data['container_name'],
                                m_opt=migration_option, 
                                c_opt=checkpoint_option)
        if method == 'llm':
            res = worker.run_llm()
        elif method == 'cgm':
            res = worker.run_cgm()
        else:
            raise Exception
    except Exception as e:
        return Response(json.dumps({'error': e}),
                        status=400,
                        mimetype='application/json'
                        )
    return Response(json.dumps(res['data']),
                    status=res['status'],
                    mimetype='application/json'
                    )


