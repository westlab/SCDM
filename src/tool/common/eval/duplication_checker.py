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

class DuplicationChecker:

    DEFAULT_LOG_FILE_PATH = "/tmp/processed_packets.log"
    DEFAULT_OUTPUT_PATH = "/home/miura/p/SCDM/logs/recorders"
    DST_LOG_FILE_PATH = "/tmp/dst_processed_packets.log"

    def __init__(self, dst_addr):#,name):
        #output_file = '{name}_dupli_checker_{time}.csv'.format(name=name, time=datetime.now().strftime('%Y%m%d_%H%M%S'))
        self._dst_addr = dst_addr
        self._base_file_path = Path(self.DEFAULT_LOG_FILE_PATH)
        self._dst_log_file_path = Path(self.DST_LOG_FILE_PATH)

        #self._output_file_path = Path(self.DEFAULT_OUTPUT_PATH + '/' + output_file)

    def get_dst_log_file(self):
        dst_path = str(self._base_file_path)
        src_path = str(self._dst_log_file_path)
        return  Rsync.call(dst_path, src_path, 'miura', self._dst_addr, None)

    def convert_csv_to_dict(self, direction, counter):
        log_data = str(self._base_file_path) if direction is Direction.src.value else str(self._dst_log_file_path)
        with open(log_data, "r") as f:
            reader = csv.reader(f)
            for row in reader:
                dic = {}
                dic['direction'] = row[0]
                msg = ','.join(row[2:])
                json_data = json.loads(msg)
                dic['id'] = json_data['id']
                dic['counter'] = json_data['counter']
                counter[dic['id']].append(dic['counter'])

    def compare_duplication(self, counter):
        has_dupli = False
        for i in range(1, len(counter)):
            j = 0
            for j in range(len(counter[i])):
                if  j is counter[i][j]:
                    continue
                else:
                    print("id: {0}, counter: {1}".fomart(i,j))
                    return False
            print("id: {0}, total: {1} okay".format(i,j))
        return True

    def run(self):
        self.get_dst_log_file()
        counter = { 1: [], 2: [], 3: [] }
        self.convert_csv_to_dict(Direction.src.value, counter)
        self.convert_csv_to_dict(Direction.dst.value, counter)
        return self.compare_duplication(counter)

