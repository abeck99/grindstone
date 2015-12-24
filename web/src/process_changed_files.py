if __name__ == "__main__":
    import txt_processing
    import dropbox_sync
    import os
    import pycouchdb
    import pycouchdb.exceptions
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

    updating_dropbox_count = [0]

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

    server_revisions = {}
    dropbox_revisions = {}
    ids_saved_to_dropbox = collections.defaultdict(set)

    def object_matches_dropbox_revision(obj):
        _id = obj['_id']
        _rev = obj['_rev']
        return _rev == dropbox_revisions.get(_id, None)

    def projects_saved():
        local_folder = dropbox_sync.dropbox_folder
        local_folder = os.path.abspath(local_folder)

        for dirname, dirs, files in os.walk(local_folder):
            for file in files:
                if not file.endswith('.txt'):
                    continue

                full_filename = os.path.join(dirname, file)
                relative_path = os.path.relpath(full_filename, local_folder)
                project_name, extension = os.path.splitext(relative_path)
                project_name.replace('\\', '/')
                yield project_name, full_filename

    def project_name_to_local_filename(project_name):
        local_folder = dropbox_sync.dropbox_folder
        local_folder = os.path.abspath(local_folder)
        os_project_name = project_name.replace('/', os.path.sep)
        return os.path.join(local_folder, os_project_name)

    def save_all_to_dropbox():
        objs_by_project = collections.defaultdict(list)

        objs_to_save = []
        for obj in couch_db.all():
            obj = obj['doc']
            if 'project' not in obj:
                continue

            objs_by_project[obj['project']].append(obj)
            if False and obj['_rev'] != dropbox_revisions[obj['_id']]:
                doc_revisions = couch_db.revisions(obj['_id'])

                conflict_obj = obj.copy()
                conflict_id = obj['_id'] + get_uuid() + '-COUCH_CONFLICT'
                conflict_obj['_id'] = conflict_id
                objs_to_save.append(conflict_obj)

        for obj in objs_to_save:
            couch_db.save(obj)

        # if all dropbox revisions and contained ids match, do not write file
        # (that way changes wont be overwritten often)

        # keep track of projects written, if ids_saved_to_dropbox contains a project with things removed, delete the file
        projects_from_db = set(objs_by_project.keys())
        projects_previously_saved = set(ids_saved_to_dropbox.keys())
        project_files_to_remove = projects_previously_saved-projects_from_db
        for project_file_to_remove in project_files_to_remove:
            print 'Removing project from dropbox: ' + str(project_file_to_remove)
            project_filename = project_name_to_local_filename(project_file_to_remove)
            try:
                os.remove(project_filename)
            except OSError:
                pass

        print 'Projects to write from db: ' + str(projects_from_db)


        # Save objects to file, checking if it needs updating first (actual file may still have unprocessed changes)
        for project_name, project_obj_list in objs_by_project.iteritems():
            ids = set([obj['_id'] for obj in project_obj_list])
            if ids == ids_saved_to_dropbox[project_name] and \
                    all([object_matches_dropbox_revision(obj) for obj in project_obj_list]):
                print 'No changes so skipping ' + project_name
                continue

            print 'Saving project: ' + str(project_name)
            content_str = txt_processing.convert_json_to_txt(project_obj_list)
            project_filename = project_name_to_local_filename(project_name)

            dropbox_sync.ensure_file_location(project_filename)
            with open(project_filename+'.txt', 'w') as f:
                f.write(content_str)
            for obj in project_obj_list:
                dropbox_revisions[obj['_id']] = obj['_rev']
            ids_saved_to_dropbox[project_name] = ids


    def changes_from_dropbox(notif):
        obj_list = []
        for project_name, full_filename in projects_saved():
            with open(full_filename) as f:
                root_object = txt_processing.convert_txt_to_json(f.read())

            obj_list.extend([update_object_with_project_info(project_name, obj) for obj in root_object])

        old_obj_ids = set([obj['doc']['_id'] for obj in couch_db.all() if 'project' in obj['doc']])
        new_obj_ids = set([obj['_id'] for obj in obj_list])

        removed_ids = old_obj_ids-new_obj_ids

        for obj_id in removed_ids:
            if obj_id in dropbox_revisions:
                try:
                    previous_obj = couch_db.get(obj_id)
                except pycouchdb.exceptions.NotFound:
                    previous_obj = None

                if previous_obj is not None and previous_obj['_rev'] == dropbox_revisions[obj_id]:
                    couch_db.delete(obj_id)

        for obj in obj_list:
            _id = obj['_id']
            _rev = dropbox_revisions.get(_id, None)

            if _rev is not None:
                obj['_rev'] = _rev

                try:
                    previous_obj = couch_db.get(_id)
                except pycouchdb.exceptions.NotFound:
                    previous_obj = None

                if previous_obj == obj:
                    continue

            # Instead of printing revision into txt files, cache _rev into the processing layer (here)
            # Attempt to save, if it fails, add a uuid to the end of the old id,
            # and mark needs_resolve and conflicting_object
            # Save all needs_resolve into a special document... project.CONFLICTS.txt

            # Ask for forgivneness???
            # Or track changes from that feed update and predict when this is going to happen?
            # And track hashes so we can tell if an object has changed?
            # IS there too much overhead here or is this normal?
            print 'Adding: ' + str(_id)
            try:
                couch_db.save(obj)
            except pycouchdb.exceptions.Conflict as c:
                # obj['needs_resolve'] = True
                # obj['conflicting_object'] = couch_db.get(obj['id'])
                conflict_id = obj['_id'] + get_uuid() + '-DROPBOX_CONFLICT'
                obj['_id'] = conflict_id
                couch_db.save(obj)
                print c

        save_all_to_dropbox()
        updating_dropbox_count[0] -= len(notif)
        if updating_dropbox_count[0] != 0:
            print 'Bad clean up!'

    def increment_updating_dropbox_count(x):
        updating_dropbox_count[0] += 1

    changes_signal.subscribe(increment_updating_dropbox_count)
    changes_signal.accumulated_debounce(30.0).subscribe(changes_from_dropbox)

    db_changes_signal = Subject()

    def changes_from_server(dbs):
        if updating_dropbox_count[0] > 0:
            return
        dbs = set(dbs)
        print 'DBs Changed: ' + str(dbs)

        save_all_to_dropbox()

    db_changes_signal.accumulated_debounce(
        1.0).subscribe(changes_from_server)

    changes_from_server([couch_db])

    server_last_seq = [None]

    def feed_reader(message, db):
        if 'last_seq' in message:
            server_last_seq[0] = str(message['last_seq'])

        if 'id' not in message:
            return

        for change in message.get('changes', []):
            if 'rev' in change:
                server_revisions[message['id']] = change['rev']

        print 'This guy: '+str(message)
        db_changes_signal.on_next(db)

    while True:
        if server_last_seq[0] is None:
            couch_db.changes_feed(feed_reader)
        else:
            couch_db.changes_feed(feed_reader, since=server_last_seq[0])

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
