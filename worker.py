from tornado import queues
from enum import Enum, unique
import sqlite3
from datetime import datetime
from drive import download_args, gdrive, pydrive_load
from pydrive.auth import GoogleAuth

from define import worker_progress, worker_status_type

class worker:
    def __init__(self, gauth:GoogleAuth):
        super().__init__()
        self._new = True
        self.gauth = gauth
        self.down_dir = ''
        self.progress = worker_progress(worker_status_type.initing, 0, 0, None, 0)
    
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
        args = download_args(self.id, self.down_dir, True, True, self.progress)
        gd = gdrive(self.gauth, args)
        await gd.pydrive_load()

        # notify maintainer
        self.status = worker_status_type.done
