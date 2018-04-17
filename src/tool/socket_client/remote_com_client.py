import socket
import configparser

class RemoteComClient:

    def __init__(self, path='/tmp/dms'):
        self.socket_path = path
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    def connect(self):
        s.connect(self.socket_path)

    def formalize_message(self):


