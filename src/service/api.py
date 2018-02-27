from flask import Blueprint, request, json, Response
from tool.docker_api import DockerApi
from tool.migration_worker import MigrationWorker

v1 = Blueprint('v1', __name__)
docker_api = DockerApi()

@v1.route("/test")
def test():
    return "hello from api.py"

@v1.route("/docker/build", methods=['POST'])
def build():
    filename = request.form['filename']
    if filename:
        data = docker_api.build(filename)
        return Response(json.dumps(data),
                        mimetype='application/json',
                        )
    else:
        return Response(json.dumps({'message': 'No filename is given'}),
                        status=400,
                        mimetype='application/json'
                        )

@v1.route('/docker/run', methods=['POST'])
def run():
    image_id = request.form['image_id']

# TODO: 非同期にするかどうか/同期型にするかどうか
# いまの状態では同期とする
# そのためmigration workerは別プロセスではなく同じプロセスで処理を行う
@v1.route('/docker/migrate', methods=['POST'])
def migrate():
    image_name = request.form['image_name']
    dst_addr = request.form['dst_addr']

    migration_worker = MigrationWorker(image_name, dst_addr)
    migration_worker.start()

    return Response(json.dumps({'message': 'Accepted'}),
                    status=202,
                    mimetype='application/json'
                    )
