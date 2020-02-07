
from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import argparse

from drive import pydrive_load


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

    results = service.files().list(corpora='drive',
                                   supportsAllDrives=True,
                                   includeItemsFromAllDrives=True,
                                   driveId=drive_id, pageSize=10,
                                   fields="nextPageToken, files(id, name)").execute()
    items = results.get('files', [])

    # drives = service.drives()
    # results = drives.get(driveId=drive_id).execute()
    # print('drive=', results.list('id'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--driveid', help='set the google drive id')
    parser.add_argument('--downdir', help='set download dir here')
    parser.add_argument('--showtree', default=True)
    parser.add_argument('--showlist', default=True)
    parser.add_argument('--override', default=False)
    parser.add_argument('--retry_count', default=10)
    parser.parse_args()
    args = parser.parse_args()

    pydrive_load(args)

    exit(0)

    print('share id is: %s, download dir is: %s' %
          (args.driveid, args.downdir))

    download_share(args.driveid, args.downdir)
