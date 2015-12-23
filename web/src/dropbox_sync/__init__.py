import dropbox
import json
import os
from updown import DropboxSyncer
import yaml


settings_file = '/web-app-settings/config.ini'
settings = yaml.load(open(settings_file).read())

app_key = settings['dropbox-app-key']
app_secret = settings['dropbox-app-secret']

access_token = settings['dropbox-access-token']
dropbox_folder = settings['dropbox-folder']


def ensure_dir(dirname):
    if not os.path.exists(dirname):
        os.makedirs(dirname, exist_ok=True)


def start_flow():
    flow = dropbox.client.DropboxOAuth2FlowNoRedirect(app_key, app_secret)
    authorize_url = flow.start()
    print authorize_url
    return flow


def end_flow(flow, code):
    new_access_token, user_id = flow.finish(code)
    print new_access_token


from rx import Observable, Observer
def sync_dropbox_task():
    syncer = DropboxSyncer(dropbox_folder, access_token)
    def sync(x):
        syncer.sync()
        # try:
        #     syncer.sync()
        # except Exception as e:
        #     print "Error in main sync loop! " + str(e)

    return Observable.timer(5000, 5000).subscribe(sync), syncer.changes_from_remote_signal


