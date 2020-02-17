from tornado import queues
from enum import Enum, unique
import sqlite3
from datetime import datetime
from drive import pydrive_load, download_args
import future
from pydrive.auth import GoogleAuth

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

class worker:
    def __init__(self, gauth:GoogleAuth, main_queue:queues.Queue):
        super().__init__()
        self._new = True
        self.gauth = gauth
        self.down_dir = ''
        self.main_queue = main_queue
        self.queue = queues.Queue() # control queue
        self.last_order:order_type = order_type.start
        self.f:future = None
    
    def new(self, id):
        self.id = id

    def parse_from_db_row(self, row:list):
        self.id = row[0]
        self.title = row[1]
        self.status = row[2]
        self.error = row[3]
        self.last_update = datetime.fromisoformat(row[4])
        self._new = False

    def save_to_db(self, conn:sqlite3.Connection):
        try:
            sql = ''
            if self._new == True:
                sql = "insert into worker values('%s', '%s', %d, '%s', '%s')" % (self.id, self.title, self.status, self.error, datetime.isoformat(self.last_update))
            else:
                sql = "update worker set status = %d, error = '%s', last_order=%d, last_update='%s where id='%s'" \
                    % (self.status, self.error, self.last_order, datetime.isoformat(self.last_update), self.id)

            cursor = conn.Cursor()
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            raise e

    # def start_worker(self):
    #     try:
    #         o:order = self.queue.get_nowait()            
    #         if o.type == order_type.cancel or o.type == order_type.stop:
    #             return

                            
    #     except queues.QueueEmpty:
    #         return

    async def do_job(self):
        args = download_args(self.id, self.down_dir, True, True)
        await pydrive_load(self.gauth, args)
