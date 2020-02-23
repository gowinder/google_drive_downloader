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
from define import download_args, file_info, path_info, worker_progress, worker_status_type
import datetime

TEMP_ROOT = '__downloader_temp__'

DRIVE_ID = ''

MIME_TYPE_FOLDER = 'application/vnd.google-apps.folder'


class gdrive():
    def __init__(self, gauth: GoogleAuth, args: download_args):
        super().__init__()
        self.args = args
        self.gauth = gauth

    @classmethod
    def check_id(cls, drive_id: str):
        # TODO check url or drive id
        return True, drive_id

    async def get_root_info(self, files, file_id):
        metadata = files.FetchMetadata(fetch_all=True)
        self.args.progress.add_log(metadata)

    async def get_file_list(self, parent_node: Node, file_info_list, drive,
                            file_id):
        current_loop = ioloop.IOLoop.current()
        self.args.progress.add_log('get_file_list...')
        l = drive.ListFile({
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
                                   ext=ext,
                                   desc=desc,
                                   download_url=download_url,
                                   parents=parents,
                                   parent_node=parent_node)
                print('discovery folder ', title)
                file_info_list.append(folder)

                child_node = Node(name=title,
                                  parent=parent_node,
                                  data=path_info(id, title, parent_node.data))
                await self.get_file_list(child_node, file_info_list, drive, id)
            else:
                info = file_info(id=id,
                                 mime_type=mime_type,
                                 title=title,
                                 is_folder=False,
                                 size=size,
                                 ext=ext,
                                 desc=desc,
                                 download_url=download_url,
                                 parents=parents,
                                 parent_node=parent_node)
                self.args.progress.add_log('discovery file %s', title)
                file_info_list.append(info)

    async def mkdir_in_tree(self, parent_path, parent_node):
        current_loop = ioloop.IOLoop.current()
        path = os.path.join(parent_path, parent_node.data.title)
        parent_node.data.path = path
        if not await current_loop.run_in_executor(None, os.path.exists, path):
            await current_loop.run_in_executor(None, os.mkdir, path)

        self.args.progress.add_log('{}'.format(path))

        for child_node in parent_node.children:
            await self.mkdir_in_tree(path, child_node)

    async def download_file(self, file_path, override: bool, drive, file_id,
                            file_title, file_size):
        # f = drive.CreateFile({'id': file_info.id})
        # file_title = file_info['title']
        # file_size = file_info['size']
        current_loop = ioloop.IOLoop.current()
        fullname = os.path.join(file_path, file_title)
        self.args.progress.set_current_progress('', 0, file_size)
        self.args.progress.add_log('# downloading {}, size={}'.format(
            fullname, file_size))
        # f.GetContentFile(fullname)

        need_override = False
        resume_pos = 0
        if not override:
            if await current_loop.run_in_executor(None, os.path.isfile,
                                                  fullname):
                size = await current_loop.run_in_executor(
                    None, os.path.getsize, fullname)
                if size == file_size:
                    self.args.progress.add_log(' already downloaded')
                    return
                elif size > file_size:
                    self.args.progress.add_log(
                        ' local size:{} not match remote:{}, will override local'
                        .format(size, file_size))
                    need_override = True
                else:
                    resume_pos = size
                    self.args.progress.add_log(
                        ' downloaded {}/{}  {:.2%}, will continue'.format(
                            size, file_size, size / file_size))
        else:
            need_override = True

        if need_override:
            if await current_loop.run_in_executor(None, os.path.exists,
                                                  fullname):
                await current_loop.run_in_executor(None, os.remove, fullname)
                self.args.progress.add_log(' deleted!')

        local_file = await current_loop.run_in_executor(
            None, io.FileIO, fullname, 'ab')
        request = drive.auth.service.files().get_media(fileId=file_id)

        downloader = await current_loop.run_in_executor(
            None, MediaIoBaseDownload, local_file, request, 1024 * 1024)
        if resume_pos is not 0:
            downloader._progress = resume_pos
        done = False
        while done is False:
            status, done = await current_loop.run_in_executor(
                None, downloader.next_chunk)
            self.args.progress.set_current_progress(status.progress(),
                                                    status.resumable_progress,
                                                    status.total_size)
            # print_with_carriage_return('     status{:.2%}, {}/{}'.format(status.progress(), sizeof_fmt(status.resumable_progress), sizeof_fmt(status.total_size)))

    async def copy_file(self, service, source_id, dest_title, dest_root):
        copied_file = {
            'title': dest_title,
            'parents': [{
                'id': dest_root['id']
            }]
        }
        copy = service.files().copy(fileId=source_id, body=copied_file)
        f = await ioloop.IOLoop.current().run_in_executor(None, copy.execute)
        return f

    # make a copy and than download copy
    async def make_copy_and_download(self, file_path, service, override: bool,
                                     drive, file_id, pro_temp, file_title,
                                     file_size):
        new_file = await self.copy_file(service, file_id, file_title, pro_temp)
        self.args.progress.add_log(
            'made new file title={}, id={}, origin id={}'.format(
                file_title, new_file['id'], file_id))
        await self.download_file(file_path, override, drive, new_file['id'],
                                 file_title, file_size)

        # remove copy file
        self.args.progress.add_log('delete copy file ', new_file['id'])
        ioloop.IOLoop.current().run_in_executor(None, new_file.Delete)

    # get share id temp folder in TEMP_FOLDER, if not exsits, create one
    async def get_project_temp(self, drive, files, driveid: str, create=True):
        temp_root = None
        current_loop = ioloop.IOLoop.current()
        # file_list = drive.ListFile({'q': "'root' in parents and mimeType={MIME_TYPE_FOLDER} and trashed=false and title={TEMP_FOLDER}"}).GetList()
        query_str = "'root' in parents and title='%s' and mimeType='%s'" % (
            TEMP_ROOT, MIME_TYPE_FOLDER)
        l = drive.ListFile({'q': query_str})
        file_list = await current_loop.run_in_executor(None, l.GetList)
        for f in file_list:
            self.args.progress.add_log('title: %s, id: %s' %
                                      (f['title'], f['id']))
            if f['title'] == TEMP_ROOT:
                temp_root = f

        # no temp root, make one
        if temp_root == None:
            self.args.progress.add_log('create root temp folder {}', TEMP_ROOT)
            temp_root = drive.CreateFile({
                'title': TEMP_ROOT,
                # 'parents': [{'root'}],
                'mimeType': MIME_TYPE_FOLDER
            })
            await current_loop.run_in_executor(None, temp_root.Upload)

        if temp_root != None:
            # query_str = "title='%s' and parents in [{'id': '%s'}]" % (driveid, temp_root['id'])
            query_str = "'%s' in parents and title='%s'" % (temp_root['id'],
                                                            driveid)
            l = drive.ListFile({'q': query_str})
            file_list = await current_loop.run_in_executor(None, l.GetList)

            if len(file_list) == 1:
                # delete old project temp folder
                await current_loop.run_in_executor(None, file_list[0].Delete)

            if create == True:
                # make a new dir named as driveid
                pro_temp = drive.CreateFile({
                    'title':
                    driveid,
                    'parents': [{
                        'id': temp_root['id']
                    }],
                    'mimeType':
                    MIME_TYPE_FOLDER
                })
                await current_loop.run_in_executor(None, pro_temp.Upload)
                self.args.progress.add_log(
                    'create project temp folder {} in {}'.format(
                        driveid, TEMP_ROOT))
                return pro_temp

        return None

    async def pydrive_load(self):

        try:

            drive = GoogleDrive(self.gauth)
            files = GoogleDriveFile(self.gauth)

            # remove temp file for this share id
            pro_temp = await self.get_project_temp(drive, files,
                                                   self.args.drive_id)

            # about = drive.GetAbout()
            # print(about)

            # get_root_info(files, DRIVE_ID)

            root_node = Node('root',
                             data=path_info(id=DRIVE_ID, title='', parent=''))

            # drive_id = DRIVE_ID
            drive_id = self.args.drive_id

            l = []
            await self.get_file_list(root_node, l, drive, drive_id)

            # list path tree
            if self.args.show_tree:
                self.args.progress.add_log('path tree is:')
                for pre, fill, node in RenderTree(root_node):
                    self.args.progress.add_log('{}{}'.format(pre, node.name))

            # make dir
            base_dir = os.path.join(self.args.down_dir, drive_id)
            await self.mkdir_in_tree(base_dir, root_node)

            # list file
            if self.args.show_list:
                self.args.progress.add_log('file list is:')

            current = 0
            total = len(l)
            for i in l:
                if self.args.show_list:
                    self.args.progress.add_log(
                        'id: {}, is_folder: {}, title: {},  desc: {}, ext: {}, size: {}'
                        .format(i.id, i.is_folder, i.title, i.desc, i.ext,
                                i.size))
                if len(i.parents) > 0:
                    index = 0
                    for parent in i.parents:
                        if self.args.show_list:
                            self.args.progress.add_log(
                                '     parents:{}={}, isRoot:{}'.format(
                                    index, parent['id'], parent['isRoot']))
                        index += 1
                    if self.args.show_list:
                        self.args.progress.add_log('     parent path={}'.format(
                            i.parent_node.data.path))

                    retry = 0
                    if not i.is_folder:
                        while retry < self.args.retry_count:
                            try:
                                self.args.progress.set_total_progress(
                                    current, total, i)
                                self.args.progress.add_log(
                                    '# {}/{} begin!'.format(current, total))
                                try:
                                    file_path = i.parent_node.data.path
                                    file_title = i.title
                                    file_size = i.size
                                    file_id = i.id
                                    await self.download_file(
                                        file_path, self.args.over_write, drive,
                                        file_id, file_title, file_size)
                                except HttpError as http_error:
                                    if http_error.resp.status == 403 and str(
                                            http_error.content
                                    ).find('The download quota for this file has been exceeded'
                                           ) != -1:
                                        await self.make_copy_and_download(
                                            file_path, drive.auth.service,
                                            self.args.over_write, drive,
                                            file_id, pro_temp, file_title,
                                            file_size)

                                print('# {}/{} done!'.format(current, total))
                                break
                            except Exception as ex:
                                retry += 1
                                self.args.progress.add_log(
                                    'unexpeted error={}, retry={}'.format(
                                        ex, retry))

                        current += 1
            self.args.progress.status = worker_status_type.done
            self.args.progress.add_log(
                'job done! remove project temp folder...')
            await self.get_project_temp(drive, files, self.args.drive_id,
                                        False)

        except Exception as ex:
            self.args.progress.add_log(
                'pydrive_load except, error={}'.format(ex))
            self.args.progress.error = str(ex)
            self.args.progress.last_update = datetime.datetime.now()

        # remove temp

    # download fire
