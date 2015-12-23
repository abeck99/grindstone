if __name__ == "__main__":
    import sys
    import git
    import datetime
    import txt_processing
    import watch_file
    import time
    import dropbox_sync
    import os

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

    dropbox_disposable, changes_signal = dropbox_sync.sync_dropbox_task()

    def update_object_with_project_info(project_name, obj):
        obj['project'] = project_name
        if obj['_id'] is None:
            obj['_id'] = get_uuid()
        return obj

    def changes_from_dropbox(notif):
        local_folder = notif.root_folder
        local_folder = os.path.abspath(local_folder)

        for dirname, dirs, files in os.walk(local_folder):
            for file in files:
                if not file.endswith('.txt'):
                    continue

                full_filename = os.path.join(dirname, file)
                relative_path = os.path.relpath(full_filename, local_folder)
                project_name, extension = os.path.splitext(relative_path)

                with open(full_filename) as f:
                    root_object = txt_processing.convert_txt_to_json(f.read())

                obj_list = [update_object_with_project_info(project_name, obj) for obj in root_object]

                print obj_list

                # save to db

        # print "Added: " + str(notif.added)
        # print "Removed: " + str(notif.removed)
    changes_signal.subscribe(changes_from_dropbox)


    def changes_from_server(notif):
        pass


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
