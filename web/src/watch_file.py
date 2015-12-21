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
        print("Got: %s" % x)
        
    def on_error(self, e):
        print("Got error: %s" % e)
        
    def on_completed(self):
        print("Sequence completed")


class FileUpdatedSignal(FileSystemEventHandler):
    def __init__(self):
        self.signal = Subject()

    def on_modified(self, event):
        self.signal.on_next(event.src_path)


def new_observer(action, path='.', recursive=True):
    event_handler = FileUpdatedSignal()

    event_handler.signal.accumulated_debounce(
        15.0).subscribe(
        ObserveFileChange(action))

    observer = Watchdog_Observer()
    observer.schedule(event_handler, path='.', recursive=True)
    return observer


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