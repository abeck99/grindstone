if __name__ == "__main__":
    import sys
    import git
    import datetime
    import txt_processing
    import watch_file
    import time
    import dropbox_sync

    dropbox_sync.sync_dropbox_task()

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
