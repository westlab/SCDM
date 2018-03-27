from timeit import default_timer as timer
from datetime import datetime
import csv

"""
TimeRecorder is used for tracking elapsed time for each designed phase with timeit library
"""
class TimeRecorder:
    DEFAULT_PATH = "./logs/recorders"
    # Those columns accords with system flow of a migration worker
    DEFAULT_COLS=[
        "total_time",                       #0
        #"clone",                            #1
        #"create_c",                         #2
        "checkpoint",                       #1
        "rsync_in_memory",                  #2
        "rsync_filesystem"                  #3
        "restore",                          #4
    ]

    def __init__(self, filename, cols=DEFAULT_COLS):
        file_path = '{path}/{filename}_{time}.csv'.format(path=self.DEFAULT_PATH,
                                                          filename=filename,
                                                          time=datetime.now().strftime('%Y%m%d_%H%M%S'))
        self._cols = cols
        self._file_path = file_path
        self._track_time = dict((i, []) for i in range(len(self._cols)))

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

        for i in self._track_time.keys():
            elapsed_time = self._track_time[i][1] - self._track_time[i][0]
            formatted_data.append(elapsed_time)

        with open(self._file_path,'a') as f:
            writer = csv.writer(f)
            writer.writerow(self._cols)
            writer.writerow(formatted_data)
