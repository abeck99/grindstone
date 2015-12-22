import datetime
import os
import shutil
import git
import time

import dropbox
from dropbox.files import FileMetadata, FolderMetadata, DeletedMetadata
import hashlib
import contextlib


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
        self.files_synced_from_dropbox = {}
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

    @contextlib.contextmanager
    def sync_context(self):
        try:
            self.pending_sync = True
            yield
        finally:
            self.pending_sync = False

    def initial_sync(self):
        with self.sync_context():
            print 'Starting INITIAL Sync'
            result = self.client.files_list_folder('', recursive=True, include_deleted=True)
            self.cursor = result.cursor
            self.sync_folder_with_entries(result.entries)
            print 'Ending INITIAL Sync'

    def sync(self):
        if self.pending_sync:
            print "Well that's nice, it seems to work with a single thread somehow?"
            return
        with self.sync_context():
            print 'Syncing...'
            result = self.client.files_list_folder_continue(self.cursor)
            self.cursor = result.cursor
            self.sync_folder_with_entries(result.entries)
            self.pending_sync = False

    def normalize_file_path(self, fn):
        return unicode(fn.replace('\\', os.path.sep).replace('/', os.path.sep))

    def local_to_remote_name(self, local_name):
        relative_path = os.path.relpath(local_name, self.local_folder)
        return '/' + relative_path.replace('\\', '/')

    def remote_to_local_name(self, remote_name):
        return self.normalize_file_path(os.path.join(self.local_folder, remote_name[1:]))

    def sync_folder_with_entries(self, entries):
        changes = False
        id_to_name, deleted_names = self.dropbox_entries_to_case_sensitive_names(entries)

        local_deleted_names = [self.remote_to_local_name(name) for name in deleted_names]
        local_names_to_download = {}
        for d in entries:
            if isinstance(d, FileMetadata):
                local_names_to_download[d.path_lower] = self.remote_to_local_name(id_to_name[d.id])

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
                        full_path = self.normalize_file_path(full_path)
                        if not os.path.islink(full_path) and os.path.isdir(full_path):
                            shutil.rmtree(full_path, ignore_errors=True)
                        else:
                            os.remove(full_path)
                        print '\tDelete Success!'
                        if full_path in self.files_synced_from_dropbox:
                            del self.files_synced_from_dropbox[full_path]
                        changes = True

        for remote_name, local_name in local_names_to_download.iteritems():
            if not remote_name.endswith('.txt') or '.git' in remote_name:
                continue
            # TODO: This blocks everything, maybe a better way to do this???
            skip = False
            while True:
                try:
                    print 'Downloading: ' + remote_name
                    md, res = self.client.files_download(remote_name)
                    break
                except dropbox.exceptions.HttpError as err:
                    print err
                    print 'Failed downloading from dropbox, trying again in 10s...'
                    time.sleep(10.0)
                except dropbox.exceptions.ApiError as err:
                    skip = True
                    print "Error when downloading, skipping.. " + str(err)
                    break
            if skip:
                continue


            data = res.content
            ensure_file_location(local_name)
            if os.path.exists(local_name):
                mtime = os.path.getmtime(local_name)
                with open(local_name, 'rb') as f:
                    local_data = f.read()
                    if data != local_data:
                        print "Conflict with existing file! Backing it up"
                        while True:
                            try:
                                print 'Uploading backup of: ' + remote_name
                                self.client.files_upload(local_data, remote_name + ".CONFLICT", dropbox.files.WriteMode.add,
                                                         False,
                                                         datetime.datetime(*time.gmtime(mtime)[:6]), False)
                                break
                            except dropbox.exceptions.HttpError as err:
                                print err
                                print 'Failed uploading conflict file to dropbox, trying again in 10s...'
                                time.sleep(10.0)
                            except dropbox.exceptions.ApiError as err:
                                print "Error when backing up, just saving locally... " + str(err)
                                with open(local_name+".CONFLICT", 'wb') as f1:
                                    f1.write(local_data)
                                break

            try:
                with open(local_name, 'wb') as f:
                    f.write(data)
            except OSError:
                print "Failed saving file!"
                pass
            self.files_synced_from_dropbox[local_name] = hashlib.sha224(data).hexdigest()
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

                fn = self.normalize_file_path(fn)

                with open(fn, 'rb') as f:
                    existing_file_data = f.read()
                    existing_file_hash = hashlib.sha224(existing_file_data).hexdigest()

                previous_hash = self.files_synced_from_dropbox.get(fn, None)

                if previous_hash != existing_file_hash:
                    mode = dropbox.files.WriteMode.add if previous_hash is None else dropbox.files.WriteMode.overwrite
                    mtime = os.path.getmtime(fn)
                    with open(fn, 'rb') as f:
                        data = f.read()
                    server_path = self.local_to_remote_name(fn)

                    while True:
                        try:
                            print 'Uploading: ' + server_path
                            self.client.files_upload(data, server_path, mode, False,
                                                     datetime.datetime(*time.gmtime(mtime)[:6]), False)
                            self.files_synced_from_dropbox[fn] = existing_file_hash
                            break
                        except dropbox.exceptions.HttpError as err:
                            print err
                            print 'Failed uploading to dropbox, trying again in 10s...'
                            time.sleep(10.0)
                        except dropbox.exceptions.ApiError as err:
                            print "Error when uploading (probably a mode issue?)... Saving a backup" + str(err)
                            with open(fn+".FAILED_UPLOAD", 'wb') as f1:
                                f1.write(data)
                            break

        files_from_dropbox = self.files_synced_from_dropbox.keys()
        for fn in files_from_dropbox:
            if not os.path.exists(fn):
                remote_name = self.local_to_remote_name(fn)
                print "Deleting remote file: " + remote_name
                while True:
                    try:
                        self.client.files_delete(remote_name)
                        del self.files_synced_from_dropbox[fn]
                        break
                    except dropbox.exceptions.HttpError as err:
                        print err
                        print 'Failed deleting on dropbox, trying again in 10s...'
                        time.sleep(10.0)
                    except dropbox.exceptions.ApiError as err:
                        print "Error when marking file as deleted... " + str(err)
                        break
