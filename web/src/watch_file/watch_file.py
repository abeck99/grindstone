import time
from watchdog.observers import Observer as Watchdog_Observer
from watchdog.events import FileSystemEventHandler
from rx.subjects import Subject
from rx import Observable, Observer
import reactive


class ObserveFileChange(Observer):
    def __init__(self, action):
        self.action = action
        super(ObserveFileChange, self).__init__()

    def on_next(self, x):
        self.action(list(set(x)))

    def on_error(self, e):
        pass

    def on_completed(self):
        pass


class FileUpdatedSignal(FileSystemEventHandler):
    def __init__(self):
        self.on_modified = self.send_event_if_needed
        self.on_moved = self.send_event_if_needed
        self.on_created = self.send_event_if_needed
        self.on_deleted = self.send_event_if_needed
        self.signal = Subject()

    def send_event_if_needed(self, event):
        if '.git' not in event.src_path:
            self.signal.on_next(event.src_path)


def new_observer(action, path='.', recursive=True):
    event_handler = FileUpdatedSignal()

    event_handler.signal.accumulated_debounce(
        10.0).subscribe(
        ObserveFileChange(action))

    file_observer = Watchdog_Observer()
    file_observer.schedule(event_handler, path, recursive)
    return file_observer


if __name__ == "__main__":
    def print_result(x):
        print x
    observer = new_observer(print_result)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
