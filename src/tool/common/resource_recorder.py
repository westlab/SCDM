from timeit import default_timer as timer
from datetime import datetime
from pathlib import Path
import psutil
import csv

"""
ResourceRecorder is used for tracking cpu and mem usage during migration
"""

class ResourceRecorder:
    DEFAULT_PATH = "/home/miura/programming/SCDM/logs/recorders"

    INIT_MEM_USED=0
    MEM_USED=1
    MEM_DIFF=2
    MEM_USED_RATE=3
    CPU_USED_RATE=4

    COLS = [
        'init_mem_used',            #0
        'mem_used',                 #1
        'mem_diff',                 #2
        'mem_usage_rate',           #3
        'cpu_usage_rate',           #4
    ]

    def __init__(self, filename):
        base_file_name = 'resource_{filename}_{time}.csv'.format(filename=filename,
                                                        time=datetime.now().strftime('%Y%m%d_%H%M%S'))
        self._file_path = Path(self.DEFAULT_PATH + '/' + base_file_name)
        self._cols = self.COLS
        self._continued = True
        self._mem = psutil.virtual_memory()
        self._track_resources = dict((i, []) for i in range(len(self._cols)))

    @property
    def continued(self):
        return self._continued

    @continued.setter
    def continued(self, boolean):
        if type(boolean) is bool:
            self._continued = boolean
            return
        raise ValuError('Please insert valid type of boolean')

    def insert_init_cond(self):
        self._track_resources[self.INIT_MEM_USED].append(self._mem.used)
        self._track_resources[self.MEM_USED_RATE].append(self._mem.percent)
        self._track_resources[self.CPU_USED_RATE].append(psutil.cpu_percent())

    def track(self):
        self.track_mem_used()
        self.track_mem_usage_rate()
        self.track_cpu_usage_rate()

    def track_mem_used(self):
        self._track_resources[self.MEM_USED].append(self._mem.used)

    def track_mem_usage_rate(self):
        self._track_resources[self.MEM_USED_RATE].append(self._mem.percent)

    def track_cpu_usage_rate(self):
        self._track_resources[self.CPU_USED_RATE].append(psutil.cpu_percent())

    def write(self):
        formatted_2d_data = []
        print(self._track_resources)

        for col_num in self._track_resources.keys():
            if col_num is self.MEM_DIFF:
                elapsed_mem_usages = [ mem_usage - self._track_resources[self.INIT_MEM_USED] for mem_usage in self._track_resources[col_num]]
                formatted_2d_data.append(elapsed_mem_usages)
            else:
                formatted_2d_data.append(self._track_resources[col_num])

        with open(str(self._file_path), 'a') as f:
            writer = csv.writer(f)
            writer.writerow(self._cols)
            writer.writerows(formatted_2d_data)



