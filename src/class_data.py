import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
import os
from upload import upload_file


class ClassDataMonitor(FileSystemEventHandler):
    def __init__(self, class_data_dir, bucket, prefix):
        super().__init__()
        self.class_data_dir = class_data_dir
        self.bucket = bucket
        self.prefix = prefix

    def on_created(self, event):
        if not event.is_directory and event.src_path.startswith(self.class_data_dir):
            print(f"File {event.src_path} has been created!")
            self.wait_for_write_completion(event.src_path)
            upload_file(event.src_path, self.bucket,
                        f"{self.prefix}{event.src_path.split('/')[-1]}")

    def wait_for_write_completion(self, file_path):
        while True:
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                return
            time.sleep(.1)


def monitor_class_data(directory, bucket, prefix, stop_signal):
    event_handler = ClassDataMonitor(directory, bucket, prefix)
    observer = Observer()
    observer.schedule(event_handler, directory, recursive=True)
    observer.start()
    logging.info(
        f"Monitoring directory: {directory} for new class samples...")
    try:
        while not stop_signal.is_set():
            time.sleep(1)
        observer.stop()
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
