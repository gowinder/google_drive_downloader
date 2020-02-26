import re

import tornado.ioloop
import tornado.queues
import tornado.web
import json

from define import (control_data, control_type, main_queue, message_type,
                    queue_message)
from maintainer import g_maintainer
from worker import worker, worker_encoder


class main_handler(tornado.web.RequestHandler):
    def get(self):
        # self.render('main.html', working=g_maintainer.working_worker,
        #     done=g_maintainer.done_worker,
        #     canelled=g_maintainer.cancel_worker)
        self.render('main.html')


class worker_list_handler(tornado.web.RequestHandler):
    def get(self):
        new = {
            **g_maintainer.working_worker,
            **g_maintainer.cancel_worker,
            **g_maintainer.done_worker
        }
        s = json.dumps(new, cls=worker_encoder)
        self.set_header('Content-Type:', 'application/json')
        self.write(s)


class new_handler(tornado.web.RequestHandler):
    async def get(self):
        self.render('new.html', error='')

    async def post(self):
        driveid = tornado.escape.utf8(self.get_argument('driveid',
                                                        '')).decode('utf-8')
        if driveid == '':
            self.render('new.html', error='no drive id or share url')
        else:
            # 'https://drive.google.com/open?id=1BhJ-uTk-bgd_0AxpepXRJZXr520o6mo0'
            # result = re.sub(r"https://drive\.google\.com/open?id=/(.*?)/.*?\?usp=sharing", driveid)

            succ, error = await g_maintainer.add(driveid)

            # self.redirect('/')


class action_handler(tornado.web.RequestHandler):
    async def get(self):
        driveid = tornado.escape.utf8(self.get_argument('id',
                                                        '')).decode('utf-8')
        action_type = tornado.escape.utf8(self.get_argument(
            'type', '')).decode('utf-8')
        if driveid == '':
            self.render('new.html', error='no drive id or share url')
        else:
            if action_type == 'cancel':
                await g_maintainer.do_cancel_worker(driveid)
                pass
            elif action_type == 'del':
                await g_maintainer.do_del_worker(driveid)
                pass
            elif action_type == 'resume':
                await g_maintainer.do_resume_worker(driveid)
            else:
                pass
