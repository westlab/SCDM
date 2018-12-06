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
    RELOAD=5
    RESTORE=6

class ConservativeMigrationConst:
    MIGRATION_TIME=0
    SERVICE_DOWNTIME=1
    COMMIT=2
    PUSH=3
    PULL=4
    CHECKPOINT=5
    RSYNC_C_FS=6
    CREATE_C=7
    RESTORE=8

class DataConsistencyMigrationConst:
    MIGRATION_TIME=0
    SERVICE_DOWNTIME=1
    SRC_GET_APP_INFO=2
    DST_CREATE_BUF=3
    SRC_CHECK_DST_PACKET_ARRAIVAL=4
    SRC_DEL_RULES_AND_BUF=5
    DST_CHECK_SRC_PACKET_ARRAIVAL=6
    DST_CHECK_STATUS=7
    CHECKPOINT=8
    RSYNC_C_FS=9
    ALLOCATE_FS=10
    RELOAD=11
    DST_UPDATE_OFFSET=12
    RESTORE=13

class TimeRecorder:
    DEFAULT_PATH = "/home/miura/p/SCDM/logs/recorders"
    # Those columns accords with system flow of a migration worker
    DEFAULT_COLS = [
        "Migration_time",                   #0
        "Service_downtime",                 #1
        "Checkpoint",                       #2
        "Sync_container_fs",                #3
        "Allocate_fs",                      #4
        "Reload",                           #5
        "Restore",                          #6
    ]

    CON_COLS= [
        "Migration_time",                   #0
        "Service_downtime",                 #1
        "Commit",                           #2
        "Push",                             #3
        "Pull",                             #4
        "Checkpoint",                       #5
        "Sync_container_fs",                #6
        "Create_container",                 #7
        "Restore",                          #8
    ]

    DCM_COLS = [
        "Migration_time",                   #0
        "Service_downtime",                 #1
        "Dst_get_app_information",          #2
        "Dst_create_buffer",                #3
        "Src_check_dst_packet_arrival",     #4
        "Src_delete_rules_and_buffer",      #5
        "Dst_check_src_packet_arrival",     #6
        "Dst_check_status",                 #7
        "Checkpoiont",                      #8
        "Rsync_container_fs",               #9
        "Allocate_fs",                      #10
        "Reload",                           #12
        "Dst_update_offset",                #11
        "Restore",                          #13
    ]

    def __init__(self, name, migration_type='proposed'):
        base_file_name = '{name}_time_{time}.csv'.format(name=name, time=datetime.now().strftime('%Y%m%d_%H%M%S'))
        if migration_type is 'proposed':
            self._cols = self.DEFAULT_COLS
        elif migration_type is 'conservative':
            self._cols = self.CON_COLS
        elif migration_type is 'dcm':
            self._cols = self.DCM_COLS

        self._file_path = self.default_path()/base_file_name
        self._track_time = dict((i, []) for i in range(len(self._cols)))

    def default_path(self):
        return Path('/home/miura/p/SCDM/logs/recorders')

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

