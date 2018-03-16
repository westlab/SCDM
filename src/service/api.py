from flask import Blueprint, request, json, Response
from tool.docker_api import DockerApi

v1 = Blueprint('v1', __name__)
docker_api = DockerApi()

@v1.route("/test")
def test():
    from tool.migration_worker import MigrationWorker
    #print(docker_api.create("busybox", "tatsukitatsuki", "latest"))
    #migration_worker = MigrationWorker(i_name="busybox", cp_name="checkpoint", dst_addr="10")
    is_success= docker_api.checkpoint("cr_test", "checkpoint")
    print(is_success)
    return "hello from api.py"

@v1.route("/test2")
def test2():
    from tool.migration_worker import MigrationWorker
    is_success= docker_api.restore("cr_test", "checkpoint")
    print(is_success)
    return "hello from api.py"

@v1.route("/docker/check", methods=['GET'])
def check():
    is_alive = docker_api.ping()
    return Response(json.dumps({'server': is_alive}),
                    mimetype='application/json')

@v1.route("/docker/inspect", methods=['GET'])
def inspect():
    image_name = request.args.get('image_name')
    version = request.args.get('version')
    container_name = request.args.get('container_name')
    data = docker_api.inspect_material(image_name, version, container_name)
    return Response(json.dumps(data),
                    mimetype='application/json')

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
