from pathlib import Path
from timeit import default_timer as timer
from datetime import datetime
import csv
import os.path
import glob
import pdb # for debug

class DiskRecorder:
    ROOTFS = 0
    ROOTFS_INIT = 1
    CONTAINERS=2
    CHECKPOINT=3
    MOUNTS=4
    VOLUME=5
    TOTAL=6

    COLS= [
        'rootfs',             #0
        'rootfs-init',        #1
        'container',           #2
        'checkpoint',          #3
        'mount',               #4
        'volume',              #5
        'total'                #6
    ]

    DEFAULT_PATH = "/home/miura/programming/SCDM/logs/recorders"

    def __init__(self, name):
        base_file_name = '{name}_disk_{time}.csv'.format(name=name, time=datetime.now().strftime('%Y%m%d_%H%M%S'))
        self._file_path = Path(self.DEFAULT_PATH + '/' + base_file_name)
        self._cols = self.COLS
        self._track_size = dict((i, 0) for i in range(len(self._cols)))

    def get_size(self, path):
        files = glob.glob(os.path.join(path, "**"), recursive = True)
        return  sum((os.path.getsize(f) for f in files if not os.path.isdir(f)))

    def track(self, key, path=None):
        size = self.get_size(path) if Path is not None else 0
        self.add_total(size)
        self._track_size[key] = size

    def add_total(self, size):
        self._track_size[self.TOTAL] += size

    def track_all(self, extractor):
        artifact_hash = extractor.extract_container_related_artifacts()
        artifact_hash['checkpoint'] = extractor.checkpoint_path(extractor._c_id)
        self.track(self.ROOTFS, str(artifact_hash['rootfs']))
        self.track(self.ROOTFS_INIT, str(artifact_hash['rootfs-init']))
        self.track(self.CONTAINERS, str(artifact_hash['containers']))
        self.track(self.CHECKPOINT, str(artifact_hash['checkpoint']))
        self.track(self.MOUNTS, str(artifact_hash['mounts']))
        if 'volumes_0' in artifact_hash:
            total_size = 0
            for i in range(5):
                if 'volumes_{0}'.format(i) in artifact_hash:
                    total_size += self.get_size(str(artifact_hash['volumes_{0}'.format(i)]))
            self._track_size[self.VOLUME] = total_size
            self.add_total(total_size)

    def write(self):
        with open(str(self._file_path), 'a') as f:
            writer = csv.writer(f)
            writer.writerow(self._cols)
            writer.writerow(self._track_size.values())

