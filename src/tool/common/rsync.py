import configparser
import subprocess as sp

from settings.docker import CREDENTIALS_SETTING_PATH

class Rsync:

    """
    Call rsync with ssh command based on given arguments 
    **PREMISE** Please setup public-private key between src and dst host

    @params String src_path
    @params String dst_path
    @params String host
    @params String src_addr=None
    @params String dst_path=None
    @return True|False
    """

    @classmethod
    def call(cls, src_path, dst_path, host, src_addr=None, dst_addr=None):
        config = configparser.ConfigParser()
        config.read(CREDENTIALS_SETTING_PATH)
        is_remote_path = (dst_addr is not None) and (dst_addr not in 'localhost')

        s_arg = "{host}@{src_addr}:{src_path}".format(host=host, src_addr=src_addr, src_path=src_path) if src_addr is not None else src_path
        d_arg = "{host}@{dst_addr}:{dst_path}".format(host=host, dst_addr=dst_addr, dst_path=dst_path) if is_remote_path else dst_path
        cmd = "sshpass -p {passwd} rsync -avzr -e ssh {s_arg} {d_arg}".format(passwd=config['dst_host']['password'], s_arg=s_arg, d_arg=d_arg)
        #cmd = "sshpass -p {passwd} rsync -avzr -e ssh {s_arg} {d_arg}".format(passwd=config['dst_host']['password'], s_arg=s_arg, d_arg=d_arg)
        try:
            #print(cmd)
            sp.run(cmd.strip().split(" "), check=True)
            return True
        except Exception as e:
            print('args:', e.args)
            return False

