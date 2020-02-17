from tornado import gen, ioloop, queues, util
from enum import Enum, unique
import sqlite3
from worker import worker, order_type, worker_status_type
from define import queue_message, message_type, control_type, control_data
from pydrive.auth import GoogleAuth


async def download_worker(drive_id:str, worker_queue:queues.Queue):
    pass

@unique
class maintainer_status(Enum):
    error = 0
    start = 1
    load_db = 2

class maintainer:
    def __init__(self, main_queue:queues.Queue, maintainer_queue:queues.Queue, gauth:GoogleAuth):
        """

        ``maintainer_queue``

        ``main_queue`` 
        """
        self.down_dir = ''
        self.gauth = gauth
        self.conn:sqlite3.Connection = None
        self.done_worker = dict()
        self.working_worker = dict()
        self.cancel_worker = dict()
        self.main_queue = main_queue
        self.maintainer_queue = maintainer_queue
        self.update_status(maintainer_status.start)


    def update_status(self, status:maintainer_status):
        self.status = status
        self.maintainer_queue.put(queue_message(message_type.maintainer_status, self.status, None))
    
    def send_error(self, error_msg):
        self.maintainer_queue.put(queue_message(message_type.maintainer_status, maintainer_status.error, error_msg))

    def clean(self):
        self.done_worker = dict()
        self.working_worker = dict()
        self.cancel_worker = dict()
        

    async def start(self):
        retry_count = 0
        while True:
            try:
                self.clean()
                self.load_worker_from_database()

                io_loop = ioloop.IOLoop.current()
                io_loop.add_callback(self.process)

                return
            except Exception as e:
                print('maintainer start error:', e)
                print('sleep 5s for next round')
                await gen.sleep(5)
                retry_count += 1

        return

    def process(self):
        try:
            has_msg = False
            msg = self.main_queue.get_nowait()
            has_msg = True
            if msg.type == message_type.control:
                if msg.subtype == control_type.query_id:
                    d:control_data = msg.data
                    w = worker(self.gauth, self.main_queue)
                    w.down_dir = self.down_dir
                    w.new(d.drive_id)
                    ioloop.IOLoop.current().add_callback(w.do_job)
                    self.working_worker[d.drive_id] = w
            elif msg.type == message_type.worker_status:
                pass
            elif msg.type == message_type.maintainer_status:
                pass
                
        except queues.QueueEmpty:
            pass
        except Exception as e:
            print('maintain.process error:', e)
        finally:
            if has_msg:
                self.main_queue.task_done()
            gen.sleep(0.3)
            ioloop.IOLoop.current().add_callback(self.process)


    def check_db_table(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute(''' create table if not exists worker (
                id text PRIMARY KEY,
                status integer,
                error text,
                last_order integer,
                last_update text
            ) ''')
            self.conn.commit()
            
            cursor.execute(''' create table if not exists drive_list (
                id text PRIMARY KEY,
                worker_id text,
                parent_id text,
                mime_type str,
                size integer,
                status integer,
                error text,
                copy_id text,
                download_flag int
            ) ''')
            self.conn.commit()
            
            print('check table done!')   
        except Exception as e:
            self.conn.rollback()
            self.send_error('check_db_table error:' + e)
            raise e

    def load_all_from_db(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute(''' select * from worker; ''')
            rows = cursor.fetchall()

            for row in rows:
                # check status
                worker = worker(self.gauth, self.main_queue)
                worker.parse_from_db_row(row)                
                if worker.status == worker_status_type.cancel:
                    self.cancel_worker[worker.id] = worker
                elif worker.status == worker_status_type.done:
                    self.done_worker[worker.id] = worker
                else:
                    self.working_worker[worker.id] = worker
                    # TODO load all file from dababase

            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            self.send_error('load_all_from_db error:' + e)
            raise e


    # load stored data from sqlite3
    def load_worker_from_database(self):
        self.update_status(maintainer_status.load_db)

        self.conn = None
        try:
            self.conn = sqlite3.connect('db/sqlite.db')
        except Exception as e:
            self.send_error('load_worker_from_database connect db error error:' + e)
            raise e
        
        self.check_db_table()
        
        self.load_all_from_db()
