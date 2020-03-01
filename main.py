from __future__ import print_function

import argparse
import os.path
import pickle

import tornado.ioloop
import tornado.queues
import tornado.web
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from pydrive.auth import GoogleAuth

from define import main_queue, maintain_queue
from fake import fake_list, fake_maintainer
from handler import (action_handler, main_handler, new_handler,
                     worker_list_handler)
from maintainer import g_maintainer

VERSION = '0.4.1'

# ClientID = '727451349002-s8hs5qb8sk85fsieknsf4hskh955rb2q.apps.googleusercontent.com'
# ClientSecret = 'AG4As4AngdqGhN9hmcwSG9Uz'

ClientID = '645615562882-e8p1tr02061sfkodmmsr26ob1ale1obs.apps.googleusercontent.com'
ClientSecret = 'Y8c2TjFYF0TnktcztHBrM76X'

# If modifying these scopes, delete the file token.pickle.
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.appdata',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive.metadata',
    'https://www.googleapis.com/auth/drive.scripts'
]


def auth():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server()
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('drive', 'v3', credentials=creds)
    return service


def print_my_drive(service, path):
    # Call the Drive v3 API
    results = service.files().list(
        pageSize=10, fields="n extPageToken, files(id, name)").execute()
    items = results.get('files', [])

    if not items:
        print('No files found.')
    else:
        print('Files:')
        for item in items:
            print(u'{0} ({1})'.format(item['name'], item['id']))


def main():
    """Shows basic usage of the Drive v3 API.
    Prints the names and ids of the first 10 files the user has access to.
    """

    service = auth()

    #print_my_drive(service, '/')


# https://drive.google.com/open?id=1Q5YF1Dh9X3BOvTKG5yrqbnwPygnNAx5D


def download_share(drive_id, download_dir):
    service = auth()

    print(service)

    #print_my_drive(service, '/')

    results = service.files().list(
        corpora='drive',
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
        driveId=drive_id,
        pageSize=10,
        fields="nextPageToken, files(id, name)").execute()
    items = results.get('files', [])

    # drives = service.drives()
    # results = drives.get(driveId=drive_id).execute()
    # print('drive=', results.list('id'))


class fake_handler(tornado.web.RequestHandler):
    def get(self):
        # main_queue.put('exit')
        self.render('fake.html', fake_list=fake_list)

        # l = {}
        # for msg in fake_list.values():
        #     l[msg.i] = msg.value
        # self.render('fake.html', fake_list=l)


def make_app():
    return tornado.web.Application([
        (r'/fake', fake_handler),
    ])


class application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r'/fake', fake_handler),
            (r'/', main_handler),
            (r'/new', new_handler),
            (r'/action', action_handler),
            (r'/worker_list', worker_list_handler),
        ]
        settings = dict(
            debug=True,
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
        )
        super(application, self).__init__(handlers, **settings)


if __name__ == '__main__':
    print('version:', VERSION)

    port = os.getenv('LISTEN_PORT', default='8261')
    down_dir = os.getenv('DOWN_DIR', default='down')

    app = application()
    app.listen(int(port))

    gauth = GoogleAuth()
    gauth = GoogleAuth()
    # Try to load saved client credentials
    gauth.LoadCredentialsFile("cred.json")
    if gauth.credentials is None:
        # Authenticate if they're not there
        gauth.LocalWebserverAuth()
    elif gauth.access_token_expired:
        # Refresh them if expired
        gauth.Refresh()
    else:
        # Initialize the saved creds
        gauth.Authorize()
    # Save the current credentials to a file
    gauth.SaveCredentialsFile("cred.json")
    # code = gauth.CommandLineAuth()
    # if code != None:
    #     gauth.Auth(code)

    io_loop = tornado.ioloop.IOLoop.current()
    # m = maintainer(main_queue, maintain_queue, gauth)
    g_maintainer.gauth = gauth
    g_maintainer.down_dir = down_dir
    io_loop.spawn_callback(g_maintainer.start)
    io_loop.start()

    exit(0)
