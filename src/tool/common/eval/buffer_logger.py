from pathlib import Path
from tool.common.rsync import Rsync
from timeit import default_timer as timer
from datetime import datetime
from enum import Enum
import json
import csv
import pdb 
class Direction(Enum):
    src=1
    dst=2

class BufferLogger:

    DEFAULT_LOG_FILE_PATH = "/tmp/processed_packets.log"
    DEFAULT_OUTPUT_PATH = "/home/miura/p/SCDM/logs/recorders"
    DST_LOG_FILE_PATH = "/tmp/dst_processed_packets.log"

    def __init__(self, name, dst_addr): 
        self._dst_addr = dst_addr

        dupli_checker_file = '{name}_dupli_checker_{time}.csv'.format(name=name, time=datetime.now().strftime('%Y%m%d_%H%M%S'))
        buf_log_file = '{name}_buf_logger_{time}.csv'.format(name=name, time=datetime.now().strftime('%Y%m%d_%H%M%S'))

        self._base_file_path = Path(self.DEFAULT_LOG_FILE_PATH)
        self._dst_log_file_path = Path(self.DST_LOG_FILE_PATH)
        self._dupli_checker_file_path = Path(self.DEFAULT_OUTPUT_PATH + '/' + dupli_checker_file)
        self._buf_log_file_path = Path(self.DEFAULT_OUTPUT_PATH + '/' + buf_log_file)
        self._dup_counter = { 1: [], 2: [], 3:[]}
        self._buf_logger = {"src_w": [], "scr_r": [], "dst_w": [], "dst_r":[] }

    def get_dst_log_file(self):
        dst_path = str(self._base_file_path)
        src_path = str(self._dst_log_file_path)
        return  Rsync.call(dst_path, src_path, 'miura', self._dst_addr, None)

    def convert_csv_to_dict(self, direction):
        log_data = str(self._base_file_path) if direction is Direction.src.value else str(self._dst_log_file_path)
        with open(log_data, "r") as f:
            reader = csv.reader(f)
            for row in reader:
                dic = {}
                dic['direction'] = row[0]
                dic['w_buf'] = row[2]
                dic['r_buf'] = row[3]

                msg = ','.join(row[4:])
                json_data = json.loads(msg)

                dic['id'] = json_data['id']
                dic['counter'] = json_data['counter']
                self._dup_counter[dic['id']].append(dic['counter'])

    def compare_duplication(self):
        has_dupli = False
        for i in range(1, len(self._dup_counter)):
            j = 0
            for j in range(len(self._dup_counter[i])):
                if  j is self._dup_counter[i][j]:
                    continue
                else:
                    print("id: {0}, counter: {1}".format(i,j))
                    return False
            print("id: {0}, total: {1} okay".format(i,j))
        return True

    def write(self, file_name, data):
        with open(str(file_name), 'a') as f:
            writer = csv.writer(f)
            writer.writerow(data)

    def run(self):
        self.get_dst_log_file()
        self.convert_csv_to_dict(Direction.src.value)
        self.convert_csv_to_dict(Direction.dst.value)
        has_no_dupli =  self.compare_duplication()
        self.write(self._dupli_checker_file_path, has_no_dupli)



