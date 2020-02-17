import tornado.ioloop
import tornado.web
import tornado.queues
from maintainer import maintainer
from worker import worker
import re
from define import main_queue, queue_message, message_type, control_type, control_data

class main_handler(tornado.web.RequestHandler):
    def get(self):
        self.render('main.html')
        


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
            # TODO verify url
            print(driveid)      
            msg = queue_message(message_type.control, control_type.query_id, control_data(driveid))
            await main_queue.put(msg)
            self.redirect('/')