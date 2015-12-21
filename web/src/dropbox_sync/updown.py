import datetime
import os
import shutil
import git
import time

import dropbox
from dropbox.files import FileMetadata, FolderMetadata, DeletedMetadata


def ensure_file_location(path):
    dirname = os.path.dirname(path)
    ensure_dir(dirname)


def ensure_dir(dirname):
    if not os.path.exists(dirname):
        os.makedirs(dirname)


# TODO: Make this use gevents
class DropboxSyncer(object):
    def __init__(self, local_folder, access_token):
        self.pending_sync = True
        self.local_folder = os.path.expanduser(local_folder)
        ensure_dir(self.local_folder)

        try:
            self.repo = git.repo.Repo(self.local_folder)
        except git.exc.InvalidGitRepositoryError:
            self.repo = git.repo.Repo.init(self.local_folder)

        self.initial_names = {}
        self.files_synced_from_dropbox = set([])
        self.client = dropbox.Dropbox(access_token)
        self.cursor = None
        self.initial_sync()

    # Note: deleted_names, final path component is always all lower case
    def dropbox_entries_to_case_sensitive_names(self, entries):
        self.initial_names.update({d.path_lower: d.name for d in entries})
        final_names = {}
        deleted_names = []
        for d in entries:
            lower_name = d.path_lower
            upper_name = ''
            while True:
                upper_case_name = self.initial_names[lower_name]
                upper_name = '/' + upper_case_name + upper_name
                lower_name = os.path.dirname(lower_name)
                if lower_name == '/':
                    break
            if isinstance(d, DeletedMetadata):
                deleted_names.append(upper_name)
            else:
                final_names[d.id] = upper_name
        return final_names, deleted_names

    def initial_sync(self):
        self.pending_sync = True
        print 'Starting INITIAL Sync'
        result = self.client.files_list_folder('', recursive=True, include_deleted=True)
        self.cursor = result.cursor
        self.sync_folder_with_entries(result.entries)
        print 'Ending INITIAL Sync'
        self.pending_sync = False

    def sync(self):
        if self.pending_sync:
            print "Well that's nice, it seems to work with a single thread somehow?"
            return
        print '......... Starting Sync'
        self.pending_sync = True
        result = self.client.files_list_folder_continue(self.cursor)
        self.cursor = result.cursor
        self.sync_folder_with_entries(result.entries)
        self.pending_sync = False
        print '......... Ending Sync'

    def sync_folder_with_entries(self, entries):
        changes = False
        id_to_name, deleted_names = self.dropbox_entries_to_case_sensitive_names(entries)

        local_deleted_names = [os.path.join(self.local_folder, name[1:]) for name in deleted_names]
        local_names_to_download = {}
        for d in entries:
            if isinstance(d, FileMetadata):
                local_names_to_download[d.path_lower] =\
                    os.path.join(self.local_folder, id_to_name[d.id][1:])

        for local_deleted_name in local_deleted_names:
            dirname, filename = os.path.split(local_deleted_name)
            files_in_path = None
            try:
                files_in_path = os.listdir(dirname)
            except Exception:
                pass
            print 'Attempting to delete: ' + local_deleted_name
            if files_in_path is not None:
                for existing_file_name in files_in_path:
                    if existing_file_name.lower() == filename.lower():
                        full_path = os.path.join(dirname, existing_file_name)
                        if not os.path.islink(full_path) and os.path.isdir(full_path):
                            shutil.rmtree(full_path, ignore_errors=True)
                        else:
                            os.remove(full_path)
                        print '\tDelete Success!'
                        if full_path in self.files_synced_from_dropbox:
                            self.files_synced_from_dropbox.remove(full_path)
                        changes = True

        for remote_name, local_name in local_names_to_download.iteritems():
            if not remote_name.endswith('.txt') or '.git' in remote_name:
                continue
            # TODO: This blocks everything, maybe a better way to do this???
            while True:
                try:
                    print 'Downloading: ' + remote_name
                    md, res = self.client.files_download(remote_name)
                    break
                except dropbox.exceptions.HttpError as err:
                    print err
                    print 'Failed downloading from dropbox, trying again in 10s...'
                    time.sleep(10.0)

            data = res.content
            ensure_file_location(local_name)
            with open(local_name, 'wb') as f:
                f.write(data)
            self.files_synced_from_dropbox.add(local_name)
            changes = True

        if changes:
            self.repo.git.add('-A')
            human_readable_timestamp = datetime.datetime.now(
                ).strftime('%Y-%m-%d %H:%M:%S')
            self.repo.index.commit('Pulled from Dropbox: ' + human_readable_timestamp)

        for dirname, dirs, files in os.walk(self.local_folder):
            for fn in files:
                fn = os.path.join(dirname, fn)
                if not fn.endswith('.txt') or '.git' in fn:
                    continue
                if unicode(fn) not in self.files_synced_from_dropbox:
                    mode = dropbox.files.WriteMode.add
                    mtime = os.path.getmtime(fn)
                    with open(fn, 'rb') as f:
                        data = f.read()
                    relative_path = os.path.relpath(fn, self.local_folder)
                    server_path = '/' + relative_path.replace('\\', '/')

                    while True:
                        try:
                            print 'Uploading: ' + server_path
                            self.client.files_upload(data, server_path, mode, False,
                                                     datetime.datetime(*time.gmtime(mtime)[:6]), False)
                            break
                        except dropbox.exceptions.HttpError as err:
                            print err
                            print 'Failed uploading to dropbox, trying again in 10s...'
                            time.sleep(10.0)
                    self.files_synced_from_dropbox.add(fn)
