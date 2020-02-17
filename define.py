import queue
from enum import Enum, unique

import tornado
from anytree import Node

from util import sizeof_fmt

main_queue = tornado.queues.Queue()
maintain_queue = tornado.queues.Queue()

@unique
class message_type(Enum):     
    control = 1     # control message
    worker_status = 2 # worker status notify message
    maintainer_status = 3 # maintainer status

@unique
class control_type(Enum):
    start_worker = 1 # start worker, this may not needed
    stop_worker = 2 # stop worker
    query_id = 3 # query a drive id, prepare to start a worker

class queue_message():
    def __init__(self, type, subtype, data):
        super().__init__()
        self.type = type
        self.subtype = subtype
        self.data = data


class control_data():
    def __init__(self, drive_id:str):
        super().__init__()
        self.drive_id = drive_id


class file_info:
    def __init__(self, id, mime_type, title, is_folder:bool, size:int, ext, desc, download_url, parents, parent_node:Node):
        self.id = id
        self.mimeType = mime_type
        self.title = title
        self.is_folder = is_folder
        self.size = size
        self.ext = ext
        self.desc = desc
        self.download_url = download_url
        self.parents = parents
        self.parent_node = parent_node


class path_info:
    def __init__(self, id, title, parent):
        self.id = id
        self.title = title
        self.parent = parent
        self.path = ''

@unique
class worker_status_type(Enum):
    error = 0
    initing = 1    # worker is initing
    listing = 2     # worker is listing drive 
    downloading = 3 # worker is downloading
    done = 4
    cancel = 5

@unique
class order_type(Enum):
    start = 1
    stop = 2
    cancel = 3
    restart = 4

class order():
    def __init__(self):
        super().__init__()
        self.id = ''
        self.type = order_type.start

class worker_progress():
    def __init__(self, status:worker_status_type, current, total_file_count, current_file:file_info, offset):
        super().__init__()
        self.status = status
        self.current_index = current
        self.total_file_count = total_file_count
        self.current_file = current_file
        self.offset = offset
        self.current_progress = 0.0
        self.logs = queue.Queue(maxsize=50)

    def add_log(self, f, *values):
        s = f % values
        print(f)
        self.logs.put(s)

    def set_total_progress(self, current_index, total_file_count, current_file:file_info):
        self.status = worker_status_type.downloading
        self.current_index = current_index
        self.total_file_count = total_file_count
        self.current_file = current_file
        self.offset = 0
        self.file_total_size = current_file.size
    
    def set_current_progress(self, progress, offset, file_total_size):
        self.current_progress = progress
        self.offset = offset
        self.file_total_size = file_total_size
        
    def current_progress(self):
        s = '{:.%2}, {}/{}'.format(self.current_progress, sizeof_fmt(self.offset), sizeof_fmt(self.file_total_size))
        return s

    def total_progress(self):
        s = '{:.%2}, {}/{}'.format(self.current_index / self.total_file_count, self.current_index, self.total_file_count)
        return s

class download_args():
    def __init__(self, drive_id:str, down_dir:str, show_list:bool, show_tree:bool, progress:worker_progress):
        self.drive_id = str(drive_id)
        self.down_dir = down_dir
        self.show_list = show_list
        self.show_tree = show_tree
        self.retry_count = 10
        self.over_write = True
        self.worker_progress = progress
        super().__init__()
