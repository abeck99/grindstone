import dropbox
import json
import os
from updown import DropboxSyncer

app_key = '***REMOVED***'
app_secret = '***REMOVED***'

fn = '~/.ab-todo-dropbox'
dropbox_folder = '~/dropbox-notes'
access_token = [None]
try:
    with open(fn) as f:
        access_token[0] = json.loads(f.read())['access_token']
except Exception as e:
    access_token[0] = '***REMOVED***'
    print 'Error loading access token: ' + str(e)


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
    access_token[0] = new_access_token
    with open('~/.ab-todo-dropbox', 'w') as f:
        f.write(json.dumps({
            "access_token": new_access_token,
            "user_id": user_id,
        }))


from rx import Observable, Observer
def sync_dropbox_task():
    syncer = DropboxSyncer(dropbox_folder, access_token[0])
    def sync(x):
        try:
            syncer.sync()
        except Exception as e:
            print "Error in main sync loop! " + str(e)

    return Observable.timer(5000, 5000).subscribe(sync)


