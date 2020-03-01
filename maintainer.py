from enum import Enum, unique

from pydrive.auth import GoogleAuth
from tornado import gen, ioloop, queues, util

from define import (control_data, control_type, message_type, queue_message,
                    worker_status_type)
from drive import gdrive
from worker import worker
from util import db_connect, db_commit, db_execute, db_rollback, db_fetchall
import aiosqlite


async def download_worker(drive_id: str, worker_queue: queues.Queue):
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
        self.gauth = None
        self.last_error = ''
        self.conn: aiosqlite.Connection = None
        self.done_worker = dict()
        self.working_worker = dict()
        self.cancel_worker = dict()
        self.update_status(maintainer_status.start)

    def update_status(self, status: maintainer_status):
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

    async def add(self, drive_id: str):
        valid, did = gdrive.check_id(drive_id)
        if not valid:
            return False, 'drive id or drive url invalid, check it again'
        # check all
        if did in self.working_worker \
        or did in self.done_worker \
        or did in self.cancel_worker:
            s = ('driveid=%s already exsits' % did)
            print(s)
            return False, s

        w = worker(self.gauth)
        w.down_dir = self.down_dir
        w.new(did)
        try:
            await w.save_to_db(self.conn)
        except Exception as e:
            s = 'driveid={} save database error={}'.format(did, e)
            print(s)
            return False, s
        self.working_worker[did] = w
        ioloop.IOLoop.current().add_callback(w.do_job)

        s = '%s add ok' % did
        print(s)
        return True, s

    async def check_db_table(self):
        try:
            await self.conn.execute(''' create table if not exists worker (
                id text PRIMARY KEY,
                title text,
                status integer,
                error text,
                last_order integer,
                last_update text
            ) ''')
            await self.conn.commit()

            await self.conn.execute(''' create table if not exists drive_list (
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
            cursor = await self.conn.execute(''' select * from worker; ''')
            rows = await cursor.fetchall()

            for row in rows:
                # check status
                w = worker(self.gauth)
                w.down_dir = self.down_dir
                w.parse_from_db_row(row)
                if w.status == worker_status_type.cancel:
                    self.cancel_worker[w.id] = w
                elif w.status == worker_status_type.done:
                    self.done_worker[w.id] = w
                else:
                    self.working_worker[w.id] = w
                    # TODO load all file from dababase

            await cursor.close()
            await self.conn.commit()
        except Exception as e:
            await self.conn.rollback()
            self.send_error('load_all_from_db error:' + e)
            raise e

        for w in self.working_worker.values():
            ioloop.IOLoop.current().add_callback(w.do_job)

    # load stored data from sqlite3
    async def load_worker_from_database(self):
        self.update_status(maintainer_status.load_db)

        self.conn = None
        try:
            self.conn = await aiosqlite.connect('db/sqlite.db')
        except Exception as e:
            self.send_error(
                'load_worker_from_database connect db error error:' + e)
            raise e

        await self.check_db_table()

        await self.load_all_from_db()

    async def find_worker(self, drive_id: str):
        if drive_id in self.working_worker:
            return self.working_worker[drive_id]
        if drive_id in self.cancel_worker:
            return self.cancel_worker[drive_id]
        if drive_id in self.done_worker:
            return self.done_worker[drive_id]

        return None

    async def do_cancel_worker(self, drive_id: str):
        if drive_id in self.working_worker:
            w = self.working_worker[drive_id]
            await w.do_cancel(self.conn)
            del (self.working_worker[drive_id])
            self.cancel_worker[drive_id] = w

    async def do_del_worker(self, drive_id: str):
        pass

    async def do_resume_worker(self, drive_id: str):
        pass


g_maintainer = maintainer()
