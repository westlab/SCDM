from flask import Blueprint, request, json, Response

from docker_api.wrapper import DockerWrapper

v1 = Blueprint('v1', __name__)
wrapper = DockerWrapper()

@v1.route("/test")
def test():
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
