import dropbox
import os
from updown import DropboxSyncer
from settings import settings


app_key = settings['dropbox-app-key']
app_secret = settings['dropbox-app-secret']

access_token = settings['dropbox-access-token']
dropbox_folder = os.path.expanduser(settings['dropbox-folder'])


def ensure_dir(dirname):
    if not os.path.exists(dirname):
        os.makedirs(dirname)

def ensure_file_location(path):
    dirname = os.path.dirname(path)
    ensure_dir(dirname)

def start_flow():
    flow = dropbox.client.DropboxOAuth2FlowNoRedirect(app_key, app_secret)
    authorize_url = flow.start()
    print authorize_url
    return flow


def end_flow(flow, code):
    new_access_token, user_id = flow.finish(code)
    print new_access_token


from rx import Observable, Observer
def sync_dropbox_task(start_from_clean_tree):
    syncer = DropboxSyncer(dropbox_folder, access_token, start_from_clean_tree)
    def sync(x):
        syncer.sync()
        # try:
        #     syncer.sync()
        # except Exception as e:
        #     print "Error in main sync loop! " + str(e)

    return Observable.timer(5000, 5000).subscribe(sync), syncer.changes_from_remote_signal


