from requests import HTTPError
import config
import logging
from checkpoints import monitor_checkpoint_directories, download_checkpoint
import threading
from api import get_api_session
from download import concurrently_download
from upload import upload_file
from webhooks import send_heartbeat, send_complete_webhook
from train import train
import time
import signal
import os
import shutil


log_format = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
logging.basicConfig(level=config.log_level, format=log_format,
                    datefmt="%m/%d/%Y %H:%M:%S")


def get_work():
    api = get_api_session()
    url = config.api_base_url + "/work"
    response = api.get(url)
    response.raise_for_status()
    body = response.json()
    if len(body) == 0:
        return None
    return body[0]


keep_alive = True
heartbeat_active = False


def heartbeat(job_id, failed_event):
    global heartbeat_active
    global keep_alive
    while heartbeat_active:
        try:
            send_heartbeat(job_id)
            time.sleep(config.heartbeat_interval)
        except HTTPError as e:
            if e.response.status_code == 400:
                logging.info(
                    f"Stopping heartbeat for job {job_id}. Job has been canceled.")
                heartbeat_active = False
                failed_event.set()
                break
        except Exception as e:
            logging.error(f"Error: {e}")
            keep_alive = False
            heartbeat_active = False
            failed_event.set()
            break


def reset_for_next_job():
    shutil.rmtree(config.instance_dir)
    os.makedirs(config.instance_dir, exist_ok=True)
    shutil.rmtree(config.class_dir)
    os.makedirs(config.class_dir, exist_ok=True)
    shutil.rmtree(config.output_dir)
    os.makedirs(config.output_dir, exist_ok=True)


def main():
    global keep_alive
    global heartbeat_active

    while keep_alive:
        job_should_stop = threading.Event()
        job = get_work()
        if job is None:
            logging.info("No work available. Sleeping for 5 seconds...")
            time.sleep(5)
            continue
        logging.info(f"Got work: {job['id']}")
        heartbeat_active = True
        heartbeat_thread = threading.Thread(
            target=heartbeat, args=(job["id"], job_should_stop))
        heartbeat_thread.start()
        reset_for_next_job()
        if job["resume_from"] is not None:
            logging.info(f"Resuming from {job['resume_from']}")
            download_checkpoint(job["checkpoint_bucket"], job["resume_from"])

        images = [{"bucket": job["data_bucket"], "key": image,
                   "filename": f"{config.instance_dir}/{image.split('/')[-1]}"} for image in job["instance_data_keys"]]
        concurrently_download(images)

        if "class_data_keys" in job and job["class_data_keys"] is not None and len(job["class_data_keys"]) > 0:
            class_images = [{"bucket": job["data_bucket"], "key": image,
                             "filename": f"{config.class_dir}/{image.split('/')[-1]}"} for image in job["class_data_keys"]]
            concurrently_download(class_images)

        training_thread = threading.Thread(
            target=train, args=(job, job_should_stop,))
        monitoring_thread = threading.Thread(
            target=monitor_checkpoint_directories, args=(config.output_dir, job["checkpoint_bucket"], job["checkpoint_prefix"], job["id"], job_should_stop,))

        training_thread.start()
        monitoring_thread.start()
        logging.info(f"Training and monitoring threads started: {job['id']}")

        training_thread.join()
        logging.info(f"Training process exited: {job['id']}")
        monitoring_thread.join()
        logging.info(f"Monitoring process exited: {job['id']}")

        if "pytorch_lora_weights.safetensors" in os.listdir(config.output_dir):
            upload_file(f"{config.output_dir}/pytorch_lora_weights.safetensors",
                        job["checkpoint_bucket"], f"{job['checkpoint_prefix']}pytorch_lora_weights.safetensors")
            send_complete_webhook(
                job["checkpoint_bucket"], f"{job['checkpoint_prefix']}pytorch_lora_weights.safetensors", job["id"])

        heartbeat_active = False
        heartbeat_thread.join()
        reset_for_next_job()
        if job_should_stop.is_set():
            logging.info(
                f"Job {job['id']} failed or was canceled. Moving on to next job.")
            continue
        logging.info(f"Work complete: {job['id']}")


def signal_handler(sig, frame):
    global keep_alive
    global heartbeat_active
    keep_alive = False
    heartbeat_active = False
    logging.info("Exiting...")
    exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    main()
