from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from pydrive.files import GoogleDriveFile
from anytree import Node, RenderTree
import os
import io
import sys
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError
from tornado import ioloop

TEMP_ROOT = '__downloader_temp__'

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


async def get_file_list(parent_node: Node, file_info_list, drive, file_id):
    current_loop = ioloop.IOLoop.current()
    print('get_file_list...')
    l = drive.ListFile(
        {
            'q': "'%s' in parents and trashed=false" % file_id
            # 'q': 'sharedWithMe',
            # 'driveId': "xxxx",
            # 'includeItemsFromAllDrives': True,
            # 'corpora': 'drive',
            # 'supportsAllDrives': True
        })
    file_list = await current_loop.run_in_executor(None, l.GetList)

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
            await get_file_list(child_node, file_info_list, drive, id)
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


async def mkdir_in_tree(parent_path, parent_node):
    current_loop = ioloop.IOLoop.current()
    path = os.path.join(parent_path, parent_node.data.title)
    parent_node.data.path = path
    if not await current_loop.run_in_executor(None, os.path.exists, path):
        await current_loop.run_in_executor(None, os.mkdir, path)
        
    print('{}'.format(path))

    for child_node in parent_node.children:
        await mkdir_in_tree(path, child_node)


async def download_file(file_path, override:bool, drive, file_id, file_title, file_size):
    # f = drive.CreateFile({'id': file_info.id})
    # file_title = file_info['title']
    # file_size = file_info['size']
    current_loop = ioloop.IOLoop.current()
    fullname = os.path.join(file_path, file_title)
    print('# downloading {}, size={}'.format(fullname, file_size))
    # f.GetContentFile(fullname)

    need_override = False
    resume_pos = 0
    if not override:
        if await current_loop.run_in_executor(None, os.path.isfile, fullname):
            size = current_loop.run_in_executor(None, os.path.getsize, fullname)
            if size == file_size:
                print(' already downloaded')
                return
            elif size > file_size:
                print(' local size:{} not match remote:{}, will override local'.format(size, file_size))
                need_override = True
            else:
                resume_pos = size
                print(' downloaded {}/{}  {:.2%}, will continue'.format(size, file_size, size / file_size))
    else:
        need_override = True

    if need_override:
        if await current_loop.run_in_executor(None, os.path.exists, fullname):
            await current_loop.run_in_executor(None, os.remove, fullname)
            print(' deleted!')

    local_file = await current_loop.run_in_executor(None, io.FileIO, fullname, 'ab')
    request = drive.auth.service.files().get_media(fileId=file_id)
        
    downloader = await current_loop.run_in_executor(None, MediaIoBaseDownload, local_file, request, 1024*1024)
    if resume_pos is not 0:
        downloader._progress = resume_pos
    done = False
    while done is False:
        status, done = await current_loop.run_in_executor(None, downloader.next_chunk)
        print_with_carriage_return('     status{:.2%}, {}/{}'.format(status.progress(), sizeof_fmt(status.resumable_progress), sizeof_fmt(status.total_size)))

async def copy_file(service, source_id, dest_title, dest_root):
    copied_file = {'title': dest_title, 'parents': [{'id': dest_root['id']}]}
    copy = service.files().copy(fileId=source_id, body=copied_file)
    f = await ioloop.IOLoop.current().run_in_executor(None, copy.execute)
    return f

# make a copy and than download copy
async def make_copy_and_download(file_path, service, override:bool, drive, file_id, pro_temp, file_title, file_size):
    new_file = await copy_file(service, file_id, file_title, pro_temp)
    print('made new file title={}, id={}, origin id={}'.format(file_title, new_file['id'], file_id))
    await download_file(file_path, override, drive, new_file['id'], file_title, file_size)

    # remove copy file
    print('delete copy file ', new_file['id'])
    ioloop.IOLoop.current().run_in_executor(None, new_file.Delete)

# get share id temp folder in TEMP_FOLDER, if not exsits, create one
async def get_project_temp(drive, files, driveid:str, create=True):
    temp_root = None
    current_loop = ioloop.IOLoop.current()
    # file_list = drive.ListFile({'q': "'root' in parents and mimeType={MIME_TYPE_FOLDER} and trashed=false and title={TEMP_FOLDER}"}).GetList()
    query_str = "'root' in parents and title='%s' and mimeType='%s'" % (TEMP_ROOT, MIME_TYPE_FOLDER)
    l = drive.ListFile({'q': query_str})
    file_list = await current_loop.run_in_executor(None, l.GetList)
    for f in file_list:
        print('title: %s, id: %s' % (f['title'], f['id']))
        if f['title'] == TEMP_ROOT:
            temp_root = f
    
    # no temp root, make one
    if temp_root == None:
        print('create root temp folder {}', TEMP_ROOT)
        temp_root = drive.CreateFile({'title': TEMP_ROOT,
            # 'parents': [{'root'}],
            'mimeType': MIME_TYPE_FOLDER})
        await current_loop.run_in_executor(None, temp_root.Upload)


    if temp_root != None:
        # query_str = "title='%s' and parents in [{'id': '%s'}]" % (driveid, temp_root['id'])
        query_str = "'%s' in parents and title='%s'" % (temp_root['id'], driveid)
        l = drive.ListFile({'q': query_str})
        file_list = await current_loop.run_in_executor(None, l.GetList)

        if len(file_list) == 1:
            # delete old project temp folder
            await current_loop.run_in_executor(None, file_list[0].Delete)
        

        if create == True:
            # make a new dir named as driveid
            pro_temp = drive.CreateFile({'title': driveid,
                'parents': [{'id': temp_root['id']}],
                'mimeType': MIME_TYPE_FOLDER})
            await current_loop.run_in_executor(None, pro_temp.Upload)
            print('create project temp folder {} in {}', driveid, TEMP_ROOT)
            return pro_temp

    return None

class download_args():
    def __init__(self, drive_id:str, down_dir:str, show_list:bool, show_tree:bool):
        self.drive_id = str(drive_id)
        self.down_dir = down_dir
        self.show_list = show_list
        self.show_tree = show_tree
        self.retry_count = 10
        self.over_write = True
        super().__init__()

async def pydrive_load(gauth:GoogleAuth, args:download_args):
    # gauth = GoogleAuth()

    # code = gauth.CommandLineAuth()
    # if code != None:
    #     gauth.Auth(code)

    drive = GoogleDrive(gauth)
    files = GoogleDriveFile(gauth)

    # remove temp file for this share id
    pro_temp = await get_project_temp(drive, files, args.drive_id)

    # about = drive.GetAbout()
    # print(about)

    # get_root_info(files, DRIVE_ID)

    root_node = Node('root', data=path_info(id=DRIVE_ID, title='', parent=''))

    # drive_id = DRIVE_ID
    drive_id = args.drive_id

    l = []
    await get_file_list(root_node, l, drive, drive_id)

    # list path tree
    if args.show_tree:
        print('path tree is:')
        for pre, fill, node in RenderTree(root_node):
            print('{}{}'.format(pre, node.name))

    # make dir
    base_dir = os.path.join(args.down_dir, drive_id)
    await mkdir_in_tree(base_dir, root_node)

    # list file
    if args.show_list:
        print('file list is:')

    current = 0
    total = len(l)    
    for i in l:
        if args.show_list:
            print('id: {}, is_folder: {}, title: {},  desc: {}, ext: {}, size: {}'.
                    format(i.id, i.is_folder, i.title, i.desc, i.ext, i.size))
        if len(i.parents) > 0:
            index = 0
            for parent in i.parents:
                if args.show_list:
                    print('     parents:{}={}, isRoot:{}'.format(
                        index, parent['id'], parent['isRoot']))
                index += 1
            if args.show_list:
                print('     parent path={}'.format(i.parent_node.data.path))

            retry = 0
            if not i.is_folder:
                while retry < args.retry_count:
                    try:
                        print('# {}/{} begin!'.format(current, total))
                        try:
                            file_path = i.parent_node.data.path
                            file_title = i.title
                            file_size = i.size
                            file_id = i.id
                            await download_file(file_path, args.over_write, drive, file_id, file_title, file_size)
                        except HttpError as http_error:
                            if http_error.resp.status == 403 and str(http_error.content).find('The download quota for this file has been exceeded') != -1:
                                await make_copy_and_download(file_path, drive.auth.service, args.over_write, 
                                    drive, file_id, pro_temp, file_title, file_size)

                        print_with_carriage_return('# {}/{} done!'.format(current, total))
                        break
                    except Exception as e: 
                        retry += 1
                        print('unexpeted error={}, retry={}'.format(e, retry))

                current += 1

    # remove temp
    print('job done! remove project temp folder...')
    await get_project_temp(drive, files, args.drive_id, False)
    # download fire
