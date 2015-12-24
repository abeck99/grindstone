if __name__ == "__main__":
    import txt_processing
    import dropbox_sync
    import os
    import pycouchdb
    from settings import settings
    import shutil
    import collections
    from rx.subjects import Subject
    import reactive


    couch_server = pycouchdb.Server(settings['couchdb-server'])
    try:
        couch_db = couch_server.database(settings['couchdb-tasks-database'])
    except pycouchdb.exceptions.NotFound:
        couch_db = couch_server.create(settings['couchdb-tasks-database'])


    is_updating_dropbox = [False]

    file_name = '.uuids'
    def get_uuid():
        if os.path.exists(file_name):
            with open(file_name, 'r') as f:
                uuid = int(f.read())
        else:
            uuid = 0
        uuid += 1
        with open(file_name, 'w') as f:
            f.write(str(uuid))
        return format(uuid, 'x')

    dropbox_disposable, changes_signal = dropbox_sync.sync_dropbox_task(True)

    def update_object_with_project_info(project_name, obj):
        obj['project'] = project_name
        if obj['_id'] is None:
            obj['_id'] = get_uuid()
        return obj

    def changes_from_dropbox(notif):
        is_updating_dropbox[0] = True
        local_folder = dropbox_sync.dropbox_folder
        local_folder = os.path.abspath(local_folder)

        obj_list = []
        for dirname, dirs, files in os.walk(local_folder):
            for file in files:
                if not file.endswith('.txt'):
                    continue

                full_filename = os.path.join(dirname, file)
                relative_path = os.path.relpath(full_filename, local_folder)
                project_name, extension = os.path.splitext(relative_path)
                project_name.replace('\\', '/')

                with open(full_filename) as f:
                    root_object = txt_processing.convert_txt_to_json(f.read())

                obj_list.extend([update_object_with_project_info(project_name, obj) for obj in root_object])

        old_obj_ids = set([obj['doc']['_id'] for obj in couch_db.all() if 'project' in obj['doc']])
        new_obj_ids = set([obj['_id'] for obj in obj_list])

        removed_ids = old_obj_ids-new_obj_ids

        for obj_id in removed_ids:
            print 'Deleting db doc: ' + obj_id
            couch_db.delete(obj_id)

        if len(obj_list) > 0:
            print 'Adding: ' + str([obj['_id'] for obj in obj_list])
            try:
                couch_db.save_bulk(obj_list)
            except Conflict as c:
                print c

        is_updating_dropbox[0] = False


    changes_signal.subscribe(changes_from_dropbox)

    db_changes_signal = Subject()

    def changes_from_server(dbs):
        if is_updating_dropbox[0]:
            print 'This could be a problem!! I thought we were signal threaded, but it appears interupts are happening'
        dbs = set(dbs)
        print 'DBs Changed: ' + str(dbs)

        local_folder = dropbox_sync.dropbox_folder

        if os.path.exists(local_folder):
            shutil.rmtree(local_folder)
        dropbox_sync.ensure_dir(local_folder)
        objs_by_project = collections.defaultdict(list)
        for obj in couch_db.all():
            obj = obj['doc']
            if 'project' not in obj:
                continue

            objs_by_project[obj['project']].append(obj)

        for project_name, project_obj_list in objs_by_project.iteritems():
            content_str = txt_processing.convert_json_to_txt(project_obj_list)
            os_project_name = project_name.replace('/', os.path.sep)
            project_filename = os.path.join(dropbox_sync.dropbox_folder, os_project_name)

            dropbox_sync.ensure_file_location(project_filename)
            with open(project_filename+'.txt', 'w') as f:
                f.write(content_str)

    db_changes_signal.accumulated_debounce(
        1.0).subscribe(changes_from_server)



    def feed_reader(message, db):
        print 'This guy: '+str(message)
        db_changes_signal.on_next(db)

    couch_db.changes_feed(feed_reader)
    print 'FEED ENDED????'

    """
    path = sys.argv[1]
    repo = git.repo.Repo(path.replace('$HOME', '~'))
    
    def process_files(file_list):
        print 'Updated: ' + str(file_list)
        human_readable_timestamp = datetime.datetime.now(
            ).strftime('%Y-%m-%d %H:%M:%S')
        repo.git.add('-A')
        repo.index.commit('Pre Process: ' + human_readable_timestamp)

        for fn in file_list:
            try:
                with open(fn) as f:
                    out_json = txt_processing.convert_txt_to_json(f.read())
                with open(fn, 'w') as f:
                    f.write(txt_processing.convert_json_to_txt(out_json))
            except IOError as e:
                print 'Error: ' + str(e)

        repo.git.add('-A')
        repo.index.commit('Post Process: ' + human_readable_timestamp)

    observer = watch_file.new_observer(process_files, path)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    """
