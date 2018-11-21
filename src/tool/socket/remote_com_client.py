import socket
from enum import Enum
import pdb

"""
Message Type for sending a socket server
refer to: https://github.com/westlab/door_vnf_platform/blob/master/platform_manager/service_api/headers_API/client_man_shared.hpp#L17-L18
"""
class ClientMessageCode(Enum):
    BUF_LOCATION = 0
    RULE_INS = 1
    RULE_DEL = 2
    BULK_RULE_INS = 3
    BULK_RULE_DEL = 4
    ACK = 5
    MSG_WAIT = 6
    MSG_OTHER = 7
    SERV_CHG_SIG = 8
    SERV_CHG_APP_BUF_R_OFFSET = 9
    DM_ASK_APP_INFO = 10
    DM_INIT_BUF = 11
    CLI_REINIT=14

class ClientSignalCode(Enum):
    NONE=0
    SRC_MIG_REQUESTED=1
    SRC_BUF_EMPTY=2
    DST_BUF_INIT_COMP=3

class SmartCommunityRouterAPI:
    def __init__(self):
        self._soc_cli = RemoteComClient()

    def connect(self):
        self._soc_cli.connect()

    def get_app_info_dict(self, app_id):
        i_message_type = ClientMessageCode.DM_ASK_APP_INFO.value
        ret = self._soc_cli.send_formalized_message(app_id, i_message_type)
        message = self._soc_cli.read()
        info = { 
                "buf_loc": message['payload'].split('|')[:1][0],
                "sig_loc": message['payload'].split('|')[1:2][0],
                "rules": message['payload'].split('|')[2:]
                }
        return info

    def prepare_app_launch(self, buf, sig, rules):
        app_id = 0
        i_message_type = ClientMessageCode.DM_INIT_BUF.value
        ret = self._soc_cli.send_formalized_message(app_id, i_message_type, payload='/tmp/serv_buffer0')
        dst_app_id = self._soc_cli.read()['payload']

        i_message_type = ClientMessageCode.BULK_RULE_INS.value
        ret = self._soc_cli.send_formalized_message(dst_app_id, i_message_type, '|'.join(rules))
        message =self._soc_cli.read()

        return int(dst_app_id)

    def prepare_for_checkpoint(self, app_id):
        i_message_type = ClientMessageCode.SERV_CHG_SIG.value
        ret = self._soc_cli.send_formalized_message(app_id, i_message_type, payload=ClientSignalCode.SRC_MIG_REQUESTED.value)
        message = self._soc_cli.read()
        return message

    def update_buf_read_offset(self, app_id, s_packet_ids):
        i_message_type = ClientMessageCode.SERV_CHG_APP_BUF_R_OFFSET.value
        ret = self._soc_cli.send_formalized_message(app_id, i_message_type, '|'.join(s_packet_ids))
        pdb.set_trace()
        message = self._soc_cli.read()
        return True

class RemoteComClient:
    BUFFER_SIZE = 1024

    def __init__(self, path='/tmp/dms'):
        self.socket_path = path
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    def connect(self):
        self.socket.connect(self.socket_path)

    def send(self):
        self.socket.send(message.encode())

    def close(self):
        self.socket.close()

    """
    Send a message to socket server
    @params Integer app_id
    @params Integer message_type
    """
    def send_formalized_message(self, app_id, message_type, payload=''):
        message = self.formalize_message(app_id, message_type, payload)
        print("message: {0}".format(message))
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
        print("============================data=======================================")
        print(data)
        print("read")
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
        message = '{app_id},{no},{type},{payload},'.format(app_id=str(app_id),
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


