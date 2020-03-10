import aiosqlite
from datetime import datetime, timezone
from enum import Enum, unique

from pydrive.auth import GoogleAuth
from tornado import queues

from define import download_args, worker_progress, worker_status_type
from drive import gdrive
from util import db_commit, db_execute
from json import JSONEncoder


class worker_encoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, worker):
            return {
                "id": o.id,
                "title": o.title,
                "status": o.status,
                "error": o.error,
                "last_update": datetime.isoformat(o.last_update.astimezone()),
                "progress": o.progress,
            }
        elif isinstance(o, worker_progress):
            title = ''
            if o.current_file is not None:
                title = o.current_file.title
            return {
                "status": o.status,
                "current_index": o.current_index,
                "total_file_count": o.total_file_count,
                "current_file_title": title,
                "logs": list(o.logs),
                "error": o.error,
                "offset": o.offset,
                "file_total_size": o.file_total_size,
                "current_progress": o.current_progress,
                "current_progress_desc": o.get_current_progress(),
                "total_progress": o.total_progress,
                "total_progress_desc": o.get_total_progress(),
            }
        else:
            return JSONEncoder.default(self, o)


class worker:
    def __init__(self, gauth: GoogleAuth):
        super().__init__()
        self.gd = None
        self.id = ''
        self._new = True
        self.gauth = gauth
        self.down_dir = ''
        self.title = ''
        self.status = worker_status_type.initing
        self.error = ''
        self.last_update = datetime.now().astimezone()
        self.progress = worker_progress(worker_status_type.initing, 0, 0, None,
                                        0)
        self.progress.update_callback = self.update_callback
        print(self.progress.update_callback)

    def new(self, id):
        self.id = id
        self.status = worker_status_type.downloading

    def update_callback(self):
        self.last_update = datetime.now().astimezone()

    def parse_from_db_row(self, row: list):
        self.id = row[0]
        self.status = row[1]
        self.error = row[2]
        self.last_update = datetime.fromisoformat(row[4])
        self._new = False

    async def save_to_db(self, conn: aiosqlite.Connection):
        try:
            sql = ''
            if self._new == True:
                sql = "insert into worker values('%s', %d, '%s', %d, '%s')" % (
                    self.id, int(self.status), self.error, 0,
                    datetime.isoformat(self.last_update))
            else:
                sql = "update worker set status = %d, error = '%s', last_update='%s' where id='%s'" \
                    % (int(self.status), self.error, datetime.isoformat(self.last_update), self.id)

            await conn.execute(sql)
            await conn.commit()
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
        self.gd = gdrive(self.gauth, args)
        await self.gd.pydrive_load()

        # notify maintainer
        self.status = worker_status_type.done

    async def do_cancel(self, conn):
        self.gd.cancel()
        self.status = worker_status_type.cancel
        await self.save_to_db(conn)