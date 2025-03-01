import socket
from enum import Enum
from time import sleep
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
    SERV_CHK_SIG = 9
    SERV_CHG_APP_BUF_R_OFFSET = 10
    DM_ASK_APP_INFO = 11
    DM_INIT_BUF = 12
    DM_ASK_WRITE_BUF_INFO = 13
    DM_ASK_PACKET_ARRIVAL = 14
    CLI_REINIT=17
    ERROR=18

class ClientSignalCode(Enum):
    NONE=0
    SRC_MIG_REQUESTED=1
    SRC_BUF_EMPTY=2
    SRC_WAITING=3
    DST_BUF_INIT_COMP=4

class ClientBufInfo(Enum):
    BUF_FIRST=0
    BUF_LAST=1

class ScrDirection(Enum):
    NEW=0
    C2S=1
    S2C=2

class SmartCommunityRouterAPI:
    def __init__(self):
        self._soc_cli = RemoteComClient()

    def connect(self):
        self._soc_cli.connect()

    def has_no_error(self, message):
        if  int(message['message_type']) is ClientMessageCode.ERROR.value:
            return False
        else:
            return True

    def get_message_from_scr(self, app_id, message_type, payload=''):
        counter = 0
        try:
            while (counter <= 100):
                ret = self._soc_cli.send_formalized_message(app_id, message_type, payload)
                message = self._soc_cli.read()
                if (self.has_no_error(message)):
                    return message
                else:
                    sleep(0.0001) # 100μs
                    counter+=1
            raise Exception("Check whether manager is running")
        except Exception as inst:
            print(inst)

    def get_app_info_dict(self, app_id):
        message = self.get_message_from_scr(app_id, ClientMessageCode.DM_ASK_APP_INFO.value)
        buf_info = { 
            "buf_loc": message['payload'].split('|')[:1][0],
            "sig_loc": message['payload'].split('|')[1:2][0],
            "rules": message['payload'].split('|')[2:]
        }
        return buf_info

    def prepare_app_launch(self, app_id, buf, sig, rules):
        message = self.get_message_from_scr(app_id, ClientMessageCode.DM_INIT_BUF.value, payload=buf)
        dst_app_id = int(message['payload'])
        ret = self._soc_cli.send_formalized_message(dst_app_id, ClientMessageCode.BULK_RULE_INS.value, '|'.join(rules))
        message =self._soc_cli.read()
        return dst_app_id

    def prepare_for_checkpoint(self, app_id):
        i_message_type = ClientMessageCode.SERV_CHG_SIG.value
        ret = self._soc_cli.send_formalized_message(app_id, i_message_type, payload=str(ClientSignalCode.SRC_MIG_REQUESTED.value))
        message = self._soc_cli.read()
        return message

    def check_status(self, app_id):
        message = self.get_message_from_scr(app_id, ClientMessageCode.SERV_CHK_SIG.value, payload=str(ClientSignalCode.SRC_WAITING.value))
        return int(message['payload'])

    def update_buf_read_offset(self, app_id, packets):
        payload= '|'.join(['{0}-{1}'.format(ele.direction, ele.packet_id) for ele in packets])
        message = self.get_message_from_scr(app_id, ClientMessageCode.SERV_CHG_APP_BUF_R_OFFSET.value, payload=payload)
        return True

    def get_buf_info(self, app_id, kind, direction):
        i_message_type = ClientMessageCode.DM_ASK_WRITE_BUF_INFO.value
        ret = self._soc_cli.send_formalized_message(app_id, message_type=i_message_type, payload="{0}|{1}".format(str(kind), str(direction)))
        buf_info = self._soc_cli.read()['payload']
        return int(buf_info) if buf_info else 0

    def check_packet_arrival(self, app_id, identifier): #in this case, packet_id
        i_message_type = ClientMessageCode.DM_ASK_PACKET_ARRIVAL.value
        ret = self._soc_cli.send_formalized_message(app_id, message_type=i_message_type, payload=str(identifier))
        does_arrive = self._soc_cli.read()['payload']
        return int(does_arrive) if does_arrive else 0

    def bulk_rule_update(self, app_id, rules, insert):
        i_message_type = ClientMessageCode.BULK_RULE_INS if bool(insert) else ClientMessageCode.BULK_RULE_DEL
        ret = self._soc_cli.send_formalized_message(app_id, message_type=i_message_type, payload='|'.join(rules))
        message = self._soc_cli.read()
        return message

class RemoteComClient:
    BUFFER_SIZE = 1024

    def __init__(self, path='/tmp/dms'):
        self.socket_path = path
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    def connect(self):
        self.socket.connect(self.socket_path)

    def send(self, message):
        #print("=========send===============")
        #print(message.encode())
        #print("========================")
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
        self.send(message)

    """
    Read socket data, and return the returned data

    @params Integer app_id
    @params Integer message_type
    @return String message
    """
    def read(self):
        data = self.socket.recv(RemoteComClient.BUFFER_SIZE)
        message = self.interpret_message(data)
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

