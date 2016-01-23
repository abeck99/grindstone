if __name__ == "__main__":
    import txt_processing
    import dropbox_sync
    import os
    import pycouchdb
    import pycouchdb.exceptions
    from settings import settings, logging_settings
    import collections
    from rx.subjects import Subject
    import reactive
    import logging
    import logging.config
    import numconv

    log_file = logging_settings.get('handlers', {}).get('file', {}).get('filename', None)
    if log_file is not None:
        dropbox_sync.ensure_file_location(log_file)
    logging.config.dictConfig(logging_settings)
    log = logging.getLogger("Main")

    couch_server = pycouchdb.Server(settings['couchdb-server'])
    try:
        couch_db = couch_server.database(settings['couchdb-tasks-database'])
    except pycouchdb.exceptions.NotFound:
        couch_db = couch_server.create(settings['couchdb-tasks-database'])

    uuid_obj_id = 'uuid-count'

    def get_uuid_obj():
        try:
            return couch_db.get(uuid_obj_id)
        except pycouchdb.exceptions.NotFound:
            # TODO: Initial value should come from config, and we can probably set ranges in some config file
            return {
                '_id': uuid_obj_id,
                'current': 1000,
            }
        raise RuntimeError('Something bad happened!')

    def num_to_uuid(i):
        return numconv.NumConv(85, '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz!.$%&()*:-;<=>?@^_`{|}~').int2str(i)

    # TODO: this is fine for single threaded but we'll need to be more original
    # or just bite the bullet and do normal uuids
    def reserve_uuids(count):
        uuid_obj = get_uuid_obj()
        cur = uuid_obj['current']
        uuid_obj['current'] += count
        couch_db.save(uuid_obj)

        for i in xrange(cur, cur+count):
            yield num_to_uuid(i)

    def get_uuid():
        return reserve_uuids(1).next()

    updating_dropbox_count = [0]
    dropbox_disposable, changes_signal = dropbox_sync.sync_dropbox_task(True)

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
        return os.path.join(local_folder, os_project_name) + '.txt'


    def deflatten_children(dest_obj_list, source_obj_list, parent_id=None):
        obj_list = [obj for obj in source_obj_list if obj.get('parent', None) == parent_id]

        for obj in obj_list:
            dest_obj_list.append(obj)
            source_obj_list.remove(obj)
            children_list = []
            obj['children'] = children_list
            deflatten_children(children_list, source_obj_list, obj['_id'])


    def save_all_to_dropbox():
        objs_by_project = collections.defaultdict(list)

        all_objs = [obj['doc'] for obj in couch_db.all() if 'project' in obj['doc']]
        objs_by_id = {obj['_id']: obj for obj in all_objs}

        for obj in all_objs:
            objs_by_project[obj['project']].append(obj)

            for blocked_id in obj.get('blocks', []):
                blocked_obj = objs_by_id[blocked_id]
                if blocked_obj is not None:
                    blocked_obj['blocked_by'] = blocked_obj.get('blocked_by', [])
                    blocked_obj['blocked_by'].append(obj['_id'])

            obj_parents = obj.get('parents', [])
            if len(obj_parents) > 0:
                obj['parent'] = obj_parents[-1]

        # TODO if response from 'all' doesn't match the current dropbox_revisions, what should we do?
        projects_from_db = set(objs_by_project.keys())
        projects_previously_saved = set(ids_saved_to_dropbox.keys())
        project_files_to_remove = projects_previously_saved-projects_from_db
        for project_file_to_remove in project_files_to_remove:
            log.info('Removing project from dropbox: ' + str(project_file_to_remove))
            project_filename = project_name_to_local_filename(project_file_to_remove)
            try:
                os.remove(project_filename)
            except OSError:
                pass
            del ids_saved_to_dropbox[project_file_to_remove]

        log.info('Projects to write from db: ' + str(projects_from_db))


        # Save objects to file, checking if it needs updating first (actual file may still have unprocessed changes)
        for project_name, project_obj_list in objs_by_project.iteritems():
            ids = set([obj['_id'] for obj in project_obj_list])
            if ids == ids_saved_to_dropbox[project_name] and \
                    all([object_matches_dropbox_revision(obj) for obj in project_obj_list]):
                log.info('No changes so skipping ' + project_name)
                continue

            obj_list = []
            project_list_copy = list(project_obj_list)
            deflatten_children(obj_list, project_list_copy)

            if len(project_list_copy) > 0:
                log.critical('Not all items were found! This is an issue')
                log.critical(str(project_list_copy))

            log.info('Saving project: ' + str(project_name))
            content_str = txt_processing.convert_json_to_txt(obj_list)

            project_filename = project_name_to_local_filename(project_name)
            dropbox_sync.ensure_file_location(project_filename)
            with open(project_filename, 'w') as f:
                try:
                   f.write(content_str.encode('utf-8'))
                except Exception as e:
                   log.critical("Error Saving: " + str(e))
            for obj in project_obj_list:
                dropbox_revisions[obj['_id']] = obj['_rev']
            ids_saved_to_dropbox[project_name] = ids

    def flatten_children(dest_obj_list, project_name, obj_list, parents):
        for obj in obj_list:
            obj['project'] = project_name
            obj['parents'] = parents
            obj['blocks'] = []

            new_parents = parents + [obj]

            dest_obj_list.append(obj)

            obj['children'] = obj.get('children', [])
            children_objects = obj['children']
            flatten_children(dest_obj_list, project_name, children_objects, new_parents)

    def inner_sync():
        obj_list = []

        # TODO: This cleanup process could probably be improved...
        for project_name, full_filename in projects_saved():
            with open(full_filename) as f:
                root_object = txt_processing.convert_txt_to_json(f.read())

            flatten_children(obj_list, project_name, root_object, [])

        objs_without_id = [obj for obj in obj_list if obj['_id'] is None]
        uuid_iter = reserve_uuids(len(objs_without_id))
        for obj in objs_without_id:
            obj['_id'] = uuid_iter.next()

        objs_by_id = {obj['_id']: obj for obj in obj_list}
        for obj in obj_list:
            obj['parents'] = [sub_obj['_id'] for sub_obj in obj['parents']]
            obj['children'] = [sub_obj['_id'] for sub_obj in obj['children']]
            if 'blocked_by' in obj:
                for blocking_obj in [objs_by_id.get(sub_obj_id, None) for sub_obj_id in obj['blocked_by']]:
                    if blocking_obj is not None:
                        blocking_obj['blocks'].append(obj['_id'])
                del obj['blocked_by']

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
                    # TODO: Do we need to test _rev here, or just ask for forgiveness?
                    previous_obj = couch_db.get(_id)
                    temp_obj = dict(previous_obj)
                    temp_obj.update(obj)
                    obj = temp_obj
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

            # TODO Should this be bulk save with transactional guarentee?
            # Perhaps we should just attempt to do a bulk update and if any fails, make a backup copy???
            log.info('Adding: ' + str(_id))
            try:
                couch_db.save(obj)
            except pycouchdb.exceptions.Conflict as c:
                # obj['needs_resolve'] = True
                # obj['conflicting_object'] = couch_db.get(obj['id'])

                # TODO: This will temporarily screw up children count, but will be fixed soon after by next
                # dropbox sync...
                conflict_id = obj['_id'] + get_uuid() + '-DROPBOX_CONFLICT'
                obj['_id'] = conflict_id
                couch_db.save(obj)
                log.exception(c)

        save_all_to_dropbox()

    def changes_from_dropbox(notifs):
        try:
            inner_sync()
        except Exception as e:
            log.critical('Something big happened!')
            log.exception(e)
        updating_dropbox_count[0] -= len(notifs)
        if updating_dropbox_count[0] != 0:
            log.critical('Bad clean up!')

    def increment_updating_dropbox_count(notif):
        updating_dropbox_count[0] += 1

        should_reload = False
        for fn in notif.added:
            try:
                with open(fn) as f:
                    s = f.read()
                if '::RELOAD::' in s:
                    should_reload = True
                    with open(fn, 'w') as f:
                        f.write(s.replace('::RELOAD::', ''))
            except OSError:
                pass

        if should_reload:
            inner_sync()

    changes_signal.subscribe(increment_updating_dropbox_count)
    changes_signal.accumulated_debounce(30.0).subscribe(changes_from_dropbox)

    db_changes_signal = Subject()

    def changes_from_server(dbs):
        if updating_dropbox_count[0] > 0:
            return
        dbs = set(dbs)
        log.debug('DBs Changed: ' + str(dbs))

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

        log.debug('Message from couchdb: '+str(message))
        db_changes_signal.on_next(db)

    while True:
        if server_last_seq[0] is None:
            couch_db.changes_feed(feed_reader)
        else:
            couch_db.changes_feed(feed_reader, since=server_last_seq[0])

