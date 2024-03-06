import sys
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
import os
import re
import config
import subprocess
from upload import upload_file
from download import download_file
from webhooks import send_progress_webhook


def zip_checkpoint(checkpoint_dir):
    # Get the name of the rightmost directory
    base_dir = os.path.basename(checkpoint_dir)

    # Construct the zip file name
    zip_file_name = f"{base_dir}.zip"

    logging.info(
        f"Zipping and uploading checkpoint directory: {checkpoint_dir} as {zip_file_name}")

    # Zip the contents of the rightmost directory
    zip_command = ['zip', '-rj',
                   f"{config.output_dir}/{zip_file_name}", f"{checkpoint_dir}"]
    logging.info(f"Running command: {' '.join(zip_command)}")
    subprocess.run(zip_command, check=True)

    return zip_file_name


def unzip_to_sibling_folder(zip_file):
    # Get the name of the zip file without extension
    zip_file_name = os.path.splitext(zip_file)[0]

    # Create a folder with the same name as the zip file
    output_folder = os.path.join(os.path.dirname(zip_file), zip_file_name)
    os.makedirs(output_folder, exist_ok=True)

    # Construct the unzip command
    unzip_command = ['unzip', '-o', zip_file, '-d', output_folder]

    # Execute the unzip command
    try:
        subprocess.run(unzip_command, check=True)
        logging.info(
            f"Zip file '{zip_file}' successfully extracted to '{output_folder}'.")
    except subprocess.CalledProcessError as e:
        logging.info(f"Error: Failed to extract zip file '{zip_file}': {e}")


def download_checkpoint(bucket, key):
    output_file = f"{config.output_dir}/{key.split('/')[-1]}"
    download_file(bucket, key, output_file)
    unzip_to_sibling_folder(output_file)
    os.remove(output_file)


class CheckPointMonitor(FileSystemEventHandler):
    def __init__(self, checkpoint_dir, bucket, prefix, job_id):
        super().__init__()
        self.checkpoint_dir = checkpoint_dir
        self.bucket = bucket
        self.prefix = prefix
        self.job_id = job_id

    def on_created(self, event):
        if event.is_directory and event.src_path.startswith(self.checkpoint_dir) and re.search(r"checkpoint-\d+/?$", event.src_path):
            logging.info(
                f"New checkpoint directory created: {event.src_path}")
            self.wait_for_write_completion(event.src_path)
            zip_file_name = zip_checkpoint(event.src_path)
            upload_file(f"{config.output_dir}/{zip_file_name}", self.bucket,
                        f"{self.prefix}{zip_file_name}")
            send_progress_webhook(
                self.bucket, f"{self.prefix}{zip_file_name}", self.job_id)
            os.remove(f"{config.output_dir}/{zip_file_name}")

    def wait_for_write_completion(self, directory):
        logging.info(f"Waiting for write operations to stop in {directory}...")
        expected_files = {"pytorch_lora_weights.safetensors", "optimizer.bin",
                          "scheduler.bin", "scaler.pt", "random_states_0.pkl"}
        found_files = set()
        while not found_files == expected_files:
            time.sleep(1)
            try:
                if os.path.exists(os.path.join(directory, "sampler.bin")):
                    expected_files.add("sampler.bin")
                # Check if all expected files are present and have non-zero size,
                # and have no write operations in progress
                for file in expected_files:
                    file_path = os.path.join(directory, file)
                    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                        mod_time = os.path.getmtime(file_path)
                        if (time.time() - mod_time) > .5 and file not in found_files:
                            logging.info(
                                f"File {file_path} has stopped writing.")
                            found_files.add(file)
                        elif (time.time() - mod_time) <= .5 and file not in found_files:
                            logging.info(
                                f"File {file_path} is still being written.")

            except Exception as e:
                logging.error(f"Error: {e}")
                sys.exit(1)


def monitor_checkpoint_directories(directory, bucket, prefix, job_id, stop_signal):
    event_handler = CheckPointMonitor(directory, bucket, prefix, job_id)
    observer = Observer()
    observer.schedule(event_handler, directory, recursive=True)
    observer.start()
    logging.info(
        f"Monitoring directory: {directory} for new 'checkpoint-*' subdirectories...")
    try:
        while not stop_signal.is_set():
            time.sleep(1)
        observer.stop()
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
