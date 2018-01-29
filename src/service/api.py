from flask import Blueprint, request, json, Response
from tool.docker_api import DockerApi
from tool.logger_factory import LoggerFactory

v1 = Blueprint('v1', __name__)
wrapper = DockerApi()
logger = LoggerFactory.create_logger(DockerApi)

@v1.route("/test")
def test():
    logger.info('hello')
    return "hello from api.py"

@v1.route("/docker/build", methods=['POST'])
def build():
    filename = request.form['filename']
    if filename:
        data = wrapper.build(filename)
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


@v1.route('/docker/migrate', methods=['GET'])
def migrate():
    #dst_addr = request.from['dst_addr']
    #service_id = request.from['service_id']
    wrapper.migrate()
    return Response(json.dumps({'message': 'migration done'}),
                    status=200,
                    mimetype='application/json'
                    )

