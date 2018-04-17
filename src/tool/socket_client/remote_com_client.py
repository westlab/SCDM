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

    def __init__(self, path='/tmp/dms'):
        self.socket_path = path
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    def connect(self):
        self.socket.connect(self.socket_path)

    """
    Formalize a message passing to vnf_platform

    @params Integer app_id
    @params Integer message_no
    @params Integer message_type
    @params String payload
    @string message
    """
    def formalize_message(self, app_id, message_type, message_no=0, payload=''):
        message = '{app_id},{no},{type},{payload}'.format(app_id=str(app_id),
                                                          no=str(message_no),
                                                          type=str(message_type),
                                                          payload=payload)
        return message
