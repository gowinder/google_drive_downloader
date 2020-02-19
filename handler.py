import re

import tornado.ioloop
import tornado.queues
import tornado.web

from define import (control_data, control_type, main_queue, message_type,
                    queue_message)
from maintainer import g_maintainer
from worker import worker


class main_handler(tornado.web.RequestHandler):
    def get(self):
        self.render('main.html', working=g_maintainer.working_worker,
            done=g_maintainer.done_worker,
            canelled=g_maintainer.cancel_worker)
        


class new_handler(tornado.web.RequestHandler):
    async def get(self):
        self.render('new.html', error='')

    async def post(self):
        driveid = tornado.escape.utf8(self.get_argument('driveid', '')).decode('utf-8')
        if driveid == '':
            self.render('new.html', error='no drive id or share url')
        else:
            # 'https://drive.google.com/open?id=1BhJ-uTk-bgd_0AxpepXRJZXr520o6mo0'
            # result = re.sub(r"https://drive\.google\.com/open?id=/(.*?)/.*?\?usp=sharing", driveid)
            
            succ, error = await g_maintainer.add(driveid)

            self.redirect('/')


class action_handler(tornado.web.RequestHandler):
    async def get(self):
        driveid = tornado.escape.utf8(self.get_argument('id', '')).decode('utf-8')
        action_type = tornado.escape.utf8(self.get_argument('type', '')).decode('utf-8')
        if driveid == '':
            self.render('new.html', error='no drive id or share url')
        else:
            if action_type == 'cancel':
                pass
            elif action_type == 'del':
                pass
            else:
                pass
        
        self.render('/')