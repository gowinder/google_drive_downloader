from tornado import gen, ioloop, queues, util
from enum import Enum, unique
import sqlite3
from worker import worker, order_type, worker_status_type
from define import queue_message, message_type, control_type, control_data
from pydrive.auth import GoogleAuth
from drive import gdrive



async def download_worker(drive_id:str, worker_queue:queues.Queue):
    pass

@unique
class maintainer_status(Enum):
    error = 0
    start = 1
    load_db = 2

class maintainer:
    def __init__(self):
        """

        ``maintainer_queue``

        ``main_queue`` 
        """
        self.down_dir = ''
        self.gauth = gauth
        self.last_error = ''
        self.conn:sqlite3.Connection = None
        self.done_worker = dict()
        self.working_worker = dict()
        self.cancel_worker = dict()
        self.update_status(maintainer_status.start)


    def update_status(self, status:maintainer_status):
        self.status = status
 
    def send_error(self, error_msg):
        self.last_error = error_msg

    async def clean(self):
        self.done_worker = dict()
        self.working_worker = dict()
        self.cancel_worker = dict()
        

    async def start(self):
        retry_count = 0
        while True:
            try:
                await self.clean()
                await self.load_worker_from_database()

                io_loop = ioloop.IOLoop.current()
                io_loop.add_callback(self.process)

                return
            except Exception as e:
                print('maintainer start error:', e)
                print('sleep 5s for next round')
                await gen.sleep(5)
                retry_count += 1

        return

    async def process(self):
        try:
            for did in self.working_worker.keys():
                w = self.working_worker[did]
                if w.status == worker_status_type.done:
                    del self.working_worker[did]
                    self.done_worker[did] = w
        except Exception as e:
            print('maintain.process error:', e)
        finally:
            await gen.sleep(1)
            ioloop.IOLoop.current().add_callback(self.process)

    async def add(self, drive_id:str):
        valid, did = gdrive.check_id(drive_id)
        if not valid:
            return False, 'drive id or drive url invalid, check it again'
        # check all
        if did in self.working_worker \
        or did in self.done_worker \
        or did in self.cancel_worker:
            s = ('driveid=%s already exsits' % did)
            return False, s

        w = worker(self.gauth)
        w.down_dir = self.down_dir
        w.new(did)
        self.working_worker[did] = w
        ioloop.IOLoop.current().add_callback(w.do_job)

        return True, '%s add ok' % did

    async def check_db_table(self):
        try:
            cursor = await self.conn.cursor()
            await cursor.execute(''' create table if not exists worker (
                id text PRIMARY KEY,
                status integer,
                error text,
                last_order integer,
                last_update text
            ) ''')
            await self.conn.commit()
            
            await cursor.execute(''' create table if not exists drive_list (
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
            await self.conn.commit()
            
            print('check table done!')   
        except Exception as e:
            await self.conn.rollback()
            self.send_error('check_db_table error:' + e)
            raise e

    async def load_all_from_db(self):
        try:
            cursor = await self.conn.cursor()
            await cursor.execute(''' select * from worker; ''')
            rows = await cursor.fetchall()

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

            await self.conn.commit()
        except Exception as e:
            await self.conn.rollback()
            self.send_error('load_all_from_db error:' + e)
            raise e


    # load stored data from sqlite3
    async def load_worker_from_database(self):
        self.update_status(maintainer_status.load_db)

        self.conn = None
        try:
            self.conn = await sqlite3.connect('db/sqlite.db')
        except Exception as e:
            self.send_error('load_worker_from_database connect db error error:' + e)
            raise e
        
        await self.check_db_table()
        
        await self.load_all_from_db()



g_maintainer = maintainer()