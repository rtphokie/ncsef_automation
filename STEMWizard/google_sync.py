import json
import os
from datetime import datetime, timezone
from pprint import pprint

import pytz
from dateutil import parser
from pydrive2.auth import GoogleAuth, ServiceAccountCredentials
from pydrive2.drive import GoogleDrive
from tqdm import tqdm

from logstuff import get_logger


class NCSEFGoogleDrive(object):
    FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"
    common_mime_types = {'pdf': 'application/pdf',
                         'zip': 'application/zip',
                         'avi': 'video/x-msvideo',
                         'xls': 'application/vnd.ms-excel',
                         'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         'csv': 'text/csv',
                         'gif': 'image/gif',
                         'jpg': 'image/jpeg',
                         'jpeg': 'image/jpeg',
                         'png': 'image/png',
                         'tif': 'image/tiff',
                         'txt': 'text/plain',
                         'tiff': 'image/tiff',
                         'mp3': 'audio/mpeg',
                         'wav': 'audio/wav',
                         'mov': 'video/mov',
                         'doc': 'application/msword',
                         'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                         'rtf': 'application/rtf',
                         'ppt': 'application/vnd.ms-powerpoint',
                         'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',

                         }

    def __init__(self, cache_file_name='caches/GoogleDriveCache.json'):
        ''' instantiate object'''
        self.logger = get_logger('google')
        self.cache_file_name = cache_file_name
        self.drive = self._auth()
        self.ids = None
        self.last_updated = None
        self.last_checked = None
        self.list_all(force=False)

    def __str__(self, indent_character=' ', show_emoji=True, root=None):
        '''output object as a string'''
        indent = 0
        response = ""
        for id, node in self.ids.items():
            if node['labels']['trashed']:
                continue  # ignore trash, we shouldn't be working with it from the API anyway
            elif root is not None:
                if node['fullpath'] == root:
                    response += self._node_output(node, root=root, indent_character=indent_character,
                                                  show_emoji=show_emoji)
            elif len(node['parents']) == 0:
                response += self._node_output(node)
        return response

    def dump(self, root, indent_character=' ', show_emoji=True, ):
        return (self.__str__(root=root, indent_character=indent_character, show_emoji=show_emoji))

    def _auth(self):
        ''' authenticate with Google Drive API '''
        gauth = GoogleAuth()
        scope = ['https://www.googleapis.com/auth/drive']
        gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name('client_secrets.json', scope)
        drive = GoogleDrive(gauth)
        return drive

    def _node_output(self, node, indent=0, indent_character=" ", show_emoji=True, root=None):
        response = ''
        if root is None or node['fullpath'].startswith(root):
            mt = ''
            if show_emoji:
                if 'folder' in node['mimeType']:
                    emoji = '📁'
                elif 'zip' in node['mimeType'] or 'tar' in node['mimeType']:
                    emoji = '🗜️'
                elif 'image' in node['mimeType']:
                    emoji = '🖼️'
                elif 'pdf' in node['mimeType']:
                    emoji = '🅿️'
                elif 'sheet' in node['mimeType']:
                    emoji = '🔢'
                elif 'text' in node['mimeType']:
                    emoji = '📄'
                else:
                    emoji = '📄'
            response = (f"{indent_character * indent}{emoji}{node['fullpath']}\n")
            for child in set(node['children']):
                response += self._node_output(self.ids[child], indent=indent + 1, indent_character=indent_character)
        return response

    def _buildpath(self, node, path):
        node['fullpath'] = f"{path}/{node['title']}"
        for child in set(node['children']):
            if child in self.ids.keys():
                self._buildpath(self.ids[child], node['fullpath'])
            else:
                raise ValueError(f"{child} id not found under {node['title']}")

    def _write_cache(self):
        fp = open(self.cache_file_name, 'w')
        json.dump({'ids': self.ids,
                   'last_updated': self.last_updated,
                   'last_checked': self.last_checked}, fp, indent=2)
        fp.close()


    def _find_file(self, fullpath, refresh=False):
        found = False
        isafolder = False
        elements = fullpath.split('/')
        parentpath = '/'.join(elements[:-1])
        title = None
        parentid = None
        nodeid = None
        nodedata = None

        for id, data in self.ids.items():
            if data['fullpath'] == parentpath:
                parentid = id
            if data['fullpath'] == fullpath:
                found = True
                nodeid = id
                title = data['title']
                nodedata = data
                isafolder = data['mimeType'] == NCSEFGoogleDrive.FOLDER_MIME_TYPE
        if not found and refresh:
            self.list_all(force=True)
            nodeid, parentid, parentpath, title, isafolder = self._find_file(fullpath, refresh=False)
        return nodeid, parentid, parentpath, title, isafolder

    def list_all(self, id=None, cache_checked_ttl=660, cache_update_ttl=21600, force=False):
        try:
            fp = open(self.cache_file_name, 'r')
            cache = json.loads(fp.read())
            fp.close()
            cache_by_id = cache['ids']
            last_updated = cache['last_updated']
            last_checked = cache['last_checked']
        except Exception as e:
            print(f'error {e}')
            cache_by_id = {}
            cache_by_tree = {}
            last_updated = '1970-01-01T00:00:00.000Z'
            last_checked = '1970-01-01T00:00:00.000Z'
        utcnow = datetime.utcnow().replace(tzinfo=timezone.utc)
        checked_delta = utcnow - parser.isoparse(last_checked)
        updated_delta = utcnow - parser.isoparse(last_updated)

        if force or checked_delta.total_seconds() > cache_checked_ttl or updated_delta.total_seconds() > cache_update_ttl:
            self.logger.info(f'refetching file info, last checked {checked_delta.total_seconds() / 60:.1f} minutes ago')
            last_checked = utcnow.isoformat()
            for file_list in self.drive.ListFile({'q': 'trashed=false', 'maxResults': 500}):
                for fileinfo in file_list:
                    # if fileinfo['mimeType'] == NCSEFGoogleDrive.FOLDER_MIME_TYPE:
                    #     pass
                    # elif 'shortcut' in fileinfo['mimeType']:
                    #     continue
                    cache_by_id[fileinfo['id']] = fileinfo
                    cache_by_id[fileinfo['id']]['children'] = []
                    cache_by_id[fileinfo['id']]['fullpath'] = ''
        else:
            self.logger.debug(
                f'using cached file info, last checked {checked_delta.total_seconds() / 60:.1f} minutes ago')

        for id, data in cache_by_id.items():
            if data['modifiedDate'] > last_updated:
                last_updated = data['modifiedDate']

            for parent in data['parents']:
                if parent['id'] not in cache_by_id.keys():
                    continue  # likely in trash
                cache_by_id[parent['id']]['children'].append(id)

        self.ids = cache_by_id
        self.last_updated = last_updated
        self.last_checked = last_checked

        # add full path to all nodes, de-dupe children
        for id, data in cache_by_id.items():
            if len(data['parents']) == 0:
                self._buildpath(data, '')
            data['children'] = list(set(data['children']))

        self._write_cache()

    def create_shortcut(self, fullpath_link_to, folder_to_put_link_in, title):
        shortcut, _, _, _, _ = self._find_file(f"{folder_to_put_link_in}/{title}", refresh=False)
        if not shortcut:
            id_to_link_to, _, _, _, _ = self._find_file(fullpath_link_to)
            id_to_create_link_in, _, _, _, _ = self._find_file(folder_to_put_link_in)
            if id_to_create_link_in is None:
                item = self.create_folder(folder_to_put_link_in)
                id_to_create_link_in = item['id']

            shortcut_metadata = {
                "title": title,
                'mimeType': 'application/vnd.google-apps.shortcut',
                "parents": [{"id": id_to_create_link_in}],
                "shortcutDetails": {"targetId": id_to_link_to,
                                    "targetMimeType": 'application/vnd.google-apps.folder'}
            }
            shortcut = self.drive.CreateFile(shortcut_metadata)
            try:
                shortcut.Upload()
                self.logger.info(f'create link to  to  {fullpath_link_to} in {folder_to_put_link_in} as {title}')
            except Exception as e:
                self.logger.error(
                    f"error creating link to  {fullpath_link_to} in {folder_to_put_link_in} as {title} id {id_to_create_link_in} {e}")
        else:
            self.logger.debug(f'shortcut to {fullpath_link_to} already in {folder_to_put_link_in}')

        return shortcut

    def create_file(self, localpath, remotepath, mimeType='application/vnd.google-apps.file', update_on='newer'):
        nodeid, parentid, parentpath, title, isafolder = self._find_file(remotepath)
        upload = None
        if nodeid and update_on == 'newer':
            remotemtime = parser.parse(self.ids[nodeid]['modifiedDate'])
            # OS returns timezone unaware in the local timezone, gotta make it aware for comparison
            localmtime = datetime.fromtimestamp(os.path.getmtime(localpath))
            localmtime = localmtime.replace(tzinfo=pytz.timezone('America/New_York'))
            upload = update_on == 'newer' and localmtime > remotemtime
        else:
            upload = True

        if upload:
            elements = remotepath.split('/')
            title = elements[-1]
            if not parentid:
                self.logger.debug(f'creating {parentpath}')
                parentitem = self.create_folder(parentpath)
                parentid = parentitem['id']
            if nodeid:
                item = self.drive.CreateFile({'id': nodeid})
                item.SetContentFile(localpath)
                item.Upload()
                self.logger.info(f'updated {remotepath} {nodeid} from {localpath}')
            else:
                for ext, mtype in NCSEFGoogleDrive.common_mime_types.items():
                    if localpath.endswith(f'.{ext}'):
                        mimeType = mtype
                metadata = {"title": title, "parents": [{"id": parentid}], "mimeType": mimeType}
                item = self.drive.CreateFile(metadata)
                item.SetContentFile(localpath)
                try:
                    item.Upload()
                except:
                    print(localpath)
                    pprint(metadata)
                self.logger.info(f'created {remotepath}')
        elif update_on == 'newer' and localmtime < remotemtime:
            self.logger.debug(f'no update needed for {remotepath}')
        else:
            self.logger.error('create_file unknown error')

    def create_folder(self, full_remote_path, expectedroot='Automation', refresh=False):
        item = {}
        nodeid, parentid, parentpath, title, isafolder = self._find_file(full_remote_path)
        if nodeid and not isafolder:
            self.logger.error(f"{full_remote_path} already exists as a non-folder")
        elif nodeid:
            metadata = {"title": title, "parents": [{"id": parentid}], 'id': id}
            return metadata
        else:
            elements = full_remote_path.split('/')
            parentpath = '/'.join(elements[:-1])
            title = elements[-1]
            if parentid is None:
                raise ValueError(f'parent folder {parentpath} not found')
            metadata = {"title": title, "parents": [{"id": parentid}],
                        "mimeType": NCSEFGoogleDrive.FOLDER_MIME_TYPE}
            item = self.drive.CreateFile(metadata)
            item.Upload()

            # update local cache
            item['fullpath'] = full_remote_path
            item['children'] = []
            self.ids[item['id']] = item
            self._write_cache()

            parentid = item['id']
            self.logger.info(f"created {title} in {parentpath} {item['id']}")

            if refresh:
                self.list_all(cache_update_ttl=0)
        return item

    def clean_empty_dirs(self, parentid=None):
        ids = set()
        for id, data in self.ids.items():
            if 'folder' not in data['mimeType']:
                continue
            if len(data['parents']) == 0:
                continue
            if data['parents'][0]['id'] != parentid:
                continue
            if len(data['children']) > 0:
                continue
            ids.add(id)
        for id in tqdm(ids):
            item = self.drive.CreateFile({'id': data['id']})
            item.Trash()

    def clean_single_file_dirs(self, parentid=None):
        idstopurge = set()
        for id, data in tqdm(self.ids.items()):
            if 'folder' not in data['mimeType']:
                continue
            if len(data['parents']) == 0:
                continue
            if data['parents'][0]['id'] != parentid:
                continue
            if len(data['children']) > 1:
                continue
            print(id, data['title'])
            idstopurge.add(id)
        for id in tqdm(idstopurge):
            if id == parentid:
                raise ValueError('no not this one')
            item = self.drive.CreateFile({'id': data['id']})
            item.Trash()
