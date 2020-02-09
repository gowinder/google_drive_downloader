import argparse

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

def get_drive_handle():
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()
    drive = GoogleDrive(gauth)
    return drive

def copy_file(service, source_id, dest_title):
    copied_file = {'title': dest_title}
    f = service.files().copy(fileId=source_id, body=copied_file).execute()
    return f['id']
                            
def main():
    parser = argparse.ArgumentParser(description='Google Drive file copy.')
    parser.add_argument('source_id',
                        help='source file id')
    parser.add_argument('-t', '--title',
                        help='destination title')
    args = parser.parse_args()

    drive = get_drive_handle()

    source = drive.CreateFile({'id': args.source_id})
    source.FetchMetadata('title')

    print(source)

    dest_title = args.title if args.title else source['title']
    dest_id = copy_file(drive.auth.service, args.source_id, dest_title)
    
    dest = drive.CreateFile({'id': dest_id})
    dest.FetchMetadata('title')
    
    print(dest)
    
if __name__ == '__main__':
    main()