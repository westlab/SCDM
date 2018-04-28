import socket
from enum import Enum

"""
Message Type for sending a socket server
refer to: https://github.com/westlab/door_vnf_platform/blob/master/platform_manager/service_api/headers_API/client_man_shared.hpp#L17-L18
"""
class ClientMessageCode(Enum):
    BUF_LOCATION = 0
    RULE_INS = 1
    RULE_DEL = 2
    ACK = 3
    MSG_WAIT = 4
    MSG_OTHER = 5
    SIG_CHG = 6

class RemoteComClient:
    BUFFER_SIZE = 200

    def __init__(self, path='/tmp/dms'):
        self.socket_path = path
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    def connect(self):
        self.socket.connect(self.socket_path)

    def close(self):
        self.socket.close()

    """
    Send a message to socket server
    @params Integer app_id
    @params Integer message_type
    """

    def send_formalized_message(self, app_id, message_type, payload=''):
        message = self.formalize_message(app_id, message_type, payload)
        print(message)
        self.socket.send(message.encode())

    def send(self):
        self.socket.send(message.encode())

    """
    Read socket data, and return the returned data

    @params Integer app_id
    @params Integer message_type
    @return String message
    """

    def read(self):
        data = self.socket.recv(RemoteComClient.BUFFER_SIZE)
        message = self.interpret_message(data)
        print(message)
        return message

    """
    Formalize a message passing to vnf_platform

    @params Integer app_id
    @params Integer message_no
    @params Integer message_type
    @params String payload
    @return string message
    """
    def formalize_message(self, app_id, message_type, payload=''):
        message_no =0
        message = '{app_id},{no},{type},{payload}'.format(app_id=str(app_id),
                                                          no=str(message_no),
                                                          type=str(message_type),
                                                          payload=payload)
        return message

    """
    Interpret a message from socket server

    @params String message
    @return dict
    """
    def interpret_message(self, data):
        key_arr = ["app_id", "message_no", "message_type", "payload"]
        str_message = data.decode("utf-8", "ignore")
        arr = str_message.split(",")
        formatted_message = { key_arr[i]: arr[i] for i in range(len(key_arr)) }
        return formatted_message

