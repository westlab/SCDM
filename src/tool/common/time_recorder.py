from timeit import default_timer as timer
from datetime import datetime
from pathlib import Path
import csv

"""
TimeRecorder is used for tracking elapsed time for each designed phase with timeit library
"""

class ProposedMigrationConst:
    MIGRATION_TIME=0
    SERVICE_DOWNTIME=1
    CHECKPOINT=2
    RSYNC_C_FS=3
    SYNC_C=4
    RESTORE=5

class ConservativeMigrationConst:
    MIGRATION_TIME=0
    SERVICE_DOWNTIME=1
    COMMIT=2
    RYSNC_I_FS=3
    SYNC_I=4
    CHECKPOINT=5
    RSYNC_C_FS=6
    SYNC_C=7
    RESTORE=8

class TimeRecorder:
    DEFAULT_PATH = "/home/miura/programming/SCDM/logs/recorders"
    # Those columns accords with system flow of a migration worker
    DEFAULT_COLS = [
        "migration_time",                   #0
        "service_downtime",                 #1
        "checkpoint",                       #2
        "rsync_c_fs",                       #3
        "sync_i",                           #4
        "restore",                          #5
    ]

    CON_COLS= [
        "migration_time",                   #0
        "service_downtime",                 #1
        "commit",                           #2
        "rsync_i_fs",                       #3
        "sync_i",                           #4
        "checkpoint",                       #5
        "rsync_c_fs",                       #6
        "c_sync",                           #7
        "restore",                          #8
    ]

    def __init__(self, cols=DEFAULT_COLS, migration_type='proposed'):
        base_file_name = 'time_{time}.csv'.format(time=datetime.now().strftime('%Y%m%d_%H%M%S'))
        self._cols = self.CON_COLS if migration_type is 'conservative' else self.DEFAULT_COLS
        self._file_path = self.default_path()/base_file_name
        self._track_time = dict((i, []) for i in range(len(self._cols)))

    def default_path(self):
        return Path('/home/miura/programming/SCDM/logs/recorders')

    """
    Track time

    @params String key
    @return Dict track_time: an attribute including the track time
    """

    def track(self, key):
        self._track_time[key].append(timer())
    """
    Write down the track_time to csv file,
    Figure out the track time to elasped_time each phases

    @params None
    @return None
    """
    def write(self):
        formatted_data = []
        print(self._track_time)

        for i in self._track_time.keys():
            if len(self._track_time[i]) is not 0:
                elapsed_time = self._track_time[i][1] - self._track_time[i][0]
                formatted_data.append(elapsed_time)

        with open(str(self._file_path), 'a') as f:
            writer = csv.writer(f)
            writer.writerow(self._cols)
            writer.writerow(formatted_data)

