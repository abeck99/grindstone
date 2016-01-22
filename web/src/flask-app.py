from flask import Flask, render_template
import pycouchdb
from settings import settings
import urllib

app = Flask("Grindstone")

couch_server = pycouchdb.Server(settings['couchdb-server'])
try:
    couch_db = couch_server.database(settings['couchdb-tasks-database'])
except pycouchdb.exceptions.NotFound:
    couch_db = couch_server.create(settings['couchdb-tasks-database'])


@app.route('/')
def home():
    view_obj = couch_db.get('_design/common')
    links = [
        {
            'url': '/queries/' + query_name,
            'title': query_name,
        } for query_name in view_obj.get('views', {}).keys()
    ]

    return render_template('home.html', links=[
        {
            'url': '/available-actions',
            'title': 'Available Actions',
        }
    ])


@app.route('/available-actions')
def available_actions():
    valid_ids = [
        res['key']
        for res in couch_db.query("common/available-actions", group=True)
        if res['value']
    ]

    tasks = list([
        {
            'name': res['doc']['name'],
            'description': res['doc']['description'],
            'quoted_id': urllib.quote(res['doc']['_id']),
        } for res in couch_db.all(keys=valid_ids)])

    return render_template('action-list.html', tasks=tasks)


@app.route('/tasks/<quoted_obj_id>/complete')
def complete_task(quoted_obj_id):
    obj_id = urllib.unquote(quoted_obj_id)

    try:
        obj = couch_db.get(obj_id)
        obj['status'] = 'Complete'
        couch_db.save(obj)
        return "Success"
    except:
        return "Failure"


@app.route('/queries/<query_name>')
def run_query(query_name):
    return str(list(couch_db.query("common/"+query_name, group=True)))

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=False)
