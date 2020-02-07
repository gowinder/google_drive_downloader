from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from pydrive.files import GoogleDriveFile
from anytree import Node, RenderTree
import os
import io
import sys
from googleapiclient.http import MediaIoBaseDownload


DRIVE_ID = ''

MIME_TYPE_FOLDER = 'application/vnd.google-apps.folder'


def sizeof_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)

def print_with_carriage_return(s):
    sys.stdout.write('\r' + s)
    sys.stdout.flush()


class file_info:
    def __init__(self, id, mime_type, title, is_folder:bool, size:int, ext, desc, download_url, parents, parent_node:Node):
        self.id = id
        self.mimeType = mime_type
        self.title = title
        self.is_folder = is_folder
        self.size = size
        self.ext = ext
        self.desc = desc
        self.download_url = download_url
        self.parents = parents
        self.parent_node = parent_node


class path_info:
    def __init__(self, id, title, parent):
        self.id = id
        self.title = title
        self.parent = parent
        self.path = ''


def get_root_info(files, file_id):
    metadata = files.FetchMetadata(fetch_all=True)
    print(metadata)


def get_file_list(parent_node: Node, file_info_list, drive, file_id):
    print('get_file_list...')
    file_list = drive.ListFile(
        {
            'q': "'%s' in parents and trashed=false" % file_id
            # 'q': 'sharedWithMe',
            # 'driveId': "xxxx",
            # 'includeItemsFromAllDrives': True,
            # 'corpora': 'drive',
            # 'supportsAllDrives': True
        }).GetList()

    for f in file_list:
        size = 0
        ext = ''
        desc = ''
        download_url = ''
        parents = []
        if 'fileSize' in f:
            size = int(f['fileSize'])
        if 'fileExtension' in f:
            ext = f['fileExtension']
        if 'description' in f:
            desc = f['description']
        if 'downloadUrl' in f:
            download_url = f['downloadUrl']
        if 'parents' in f:
            parents = f['parents']

        title = f['title']
        mime_type = f['mimeType']
        id = f['id']

        if f['mimeType'] == MIME_TYPE_FOLDER:
            folder = file_info(id=id,
                               mime_type=mime_type,
                               title=title,
                               is_folder=True,
                               size=size,
                               ext=ext, desc=desc,
                               download_url=download_url,
                               parents=parents,
                               parent_node=parent_node)
            print('discovery folder ', title)                               
            file_info_list.append(folder)

            child_node = Node(name=title, parent=parent_node,
                              data=path_info(id, title, parent_node.data))
            get_file_list(child_node, file_info_list, drive, id)
        else:
            info = file_info(id=id,
                             mime_type=mime_type,
                             title=title,
                             is_folder=False,
                             size=size,
                             ext=ext, desc=desc,
                             download_url=download_url,
                             parents=parents,
                             parent_node=parent_node)
            print('discovery file ', title)                             
            file_info_list.append(info)


def mkdir_in_tree(parent_path, parent_node):
    path = os.path.join(parent_path, parent_node.data.title)
    parent_node.data.path = path
    if not os.path.exists(path):
        os.mkdir(path)

    print('{}'.format(path))

    for child_node in parent_node.children:
        mkdir_in_tree(path, child_node)


def download_file(override:bool, drive, file_info: file_info):
    f = drive.CreateFile({'id': file_info.id})
    fullname = os.path.join(file_info.parent_node.data.path, file_info.title)
    print('# downloading {}, size={}'.format(fullname, file_info.size))
    # f.GetContentFile(fullname)

    need_override = False
    resume_pos = 0
    if not override:
        if os.path.isfile(fullname):
            size = os.path.getsize(fullname)
            if size == file_info.size:
                print(' already downloaded')
                return
            elif size > file_info.size:
                print(' local size:{} not match remote:{}, will override local'.format(size, file_info.size))
                need_override = True
            else:
                resume_pos = size
                print(' downloaded {}/{}  {:.2%}, will continue'.format(size, file_info.size, size / file_info.size))
    else:
        need_override = True

    if need_override:
        os.remove(fullname)
        print(' deleted!')

    local_file = io.FileIO(fullname, mode='ab')
    request = drive.auth.service.files().get_media(fileId=file_info.id)
    
    
    downloader = MediaIoBaseDownload(local_file, request, chunksize=1024*1024)
    if resume_pos is not 0:
        downloader._progress = resume_pos
    done = False
    while done is False:
        status, done = downloader.next_chunk()
        print_with_carriage_return('     status{:.2%}, {}/{}'.format(status.progress(), sizeof_fmt(status.resumable_progress), sizeof_fmt(status.total_size)))


def pydrive_load(args):
    gauth = GoogleAuth()

    code = gauth.CommandLineAuth()
    if code != None:
        gauth.Auth(code)

    drive = GoogleDrive(gauth)
    files = GoogleDriveFile(gauth)

    # about = drive.GetAbout()
    # print(about)

    # get_root_info(files, DRIVE_ID)

    root_node = Node('root', data=path_info(id=DRIVE_ID, title='', parent=''))

    # drive_id = DRIVE_ID
    drive_id = args.driveid

    l = []
    get_file_list(root_node, l, drive, drive_id)

    # list path tree
    if args.showtree:
        print('path tree is:')
        for pre, fill, node in RenderTree(root_node):
            print('{}{}'.format(pre, node.name))

    # make dir
    base_dir = os.path.join(args.downdir, drive_id)
    mkdir_in_tree(base_dir, root_node)

    # list file
    if args.showlist:
        print('file list is:')

    current = 0
    total = len(l)    
    for i in l:
        if args.showlist:
            print('id: {}, is_folder: {}, title: {},  desc: {}, ext: {}, size: {}'.
                    format(i.id, i.is_folder, i.title, i.desc, i.ext, i.size))
        if len(i.parents) > 0:
            index = 0
            for parent in i.parents:
                if args.showlist:
                    print('     parents:{}={}, isRoot:{}'.format(
                        index, parent['id'], parent['isRoot']))
                index += 1
            if args.showlist:
                print('     parent path={}'.format(i.parent_node.data.path))

            retry = 0
            if not i.is_folder:
                while retry < args.retry_count:
                    try:
                        print('# {}/{} begin!'.format(current, total))
                        download_file(args.override, drive, i)
                        print_with_carriage_return('# {}/{} done!'.format(current, total))
                        break
                    except: 
                        retry += 1
                        print('unexpeted error, retry={}'.format(retry))

                current += 1

    # download fire
