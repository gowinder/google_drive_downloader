import tornado
from enum import Enum, unique

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