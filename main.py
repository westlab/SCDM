import argparse
import configparser

description = """
Rest server for Smart Community Docker Manger
"""
parser = argparse.ArgumentParser(description)
parser.add_argument('program',
                    type=str,
                    choices=('server'),
                    help='program that you want to run')
parser.add_argument('conf',
                    type=str,
                    help='directory path to config file')
args = parser.parse_args()
config = configparser.ConfigParser()
config.read(args.conf)

def rest_server():
    from flask import Flask
    from api import v1

    port = config.getint('rest_server', 'port')
    debug = config.getboolean('rest_server','debug')

    app = Flask(__name__)
    # create url prefix for corresponding docker api
    app.register_blueprint(v1, url_prefix='/v1')
    app.run(port=port, debug=debug)

if __name__ == "__main__":
    if args.program == 'server':
        rest_server()
