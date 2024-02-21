import config
import logging
from checkpoints import monitor_checkpoint_directories, download_checkpoint, stop_monitoring
import threading
import requests
from download import concurrently_download
from upload import upload_file
from webhooks import send_heartbeat, send_complete_webhook
from train import train
import time
import signal
import os


log_format = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
logging.basicConfig(level=config.log_level, format=log_format,
                    datefmt="%m/%d/%Y %H:%M:%S")

api = requests.Session()
api.headers.update({"x-api-key": config.api_key})


def get_work():
    url = config.api_base_url + "/work"
    response = api.get(url)
    response.raise_for_status()
    body = response.json()
    if len(body) == 0:
        return None
    return body[0]


keep_alive = True

heartbeat_active = False


def heartbeat(job_id):
    global heartbeat_active
    global keep_alive
    while heartbeat_active:
        try:
            send_heartbeat(job_id)
            time.sleep(config.heartbeat_interval)
        except Exception as e:
            logging.error(f"Error: {e}")
            keep_alive = False
            heartbeat_active = False
            break


def main():
    global keep_alive
    global heartbeat_active
    while keep_alive:
        job = get_work()
        if job is None:
            logging.info("No work available. Sleeping for 5 seconds...")
            time.sleep(5)
            continue
        logging.info(f"Got work: {job['id']}")
        heartbeat_active = True
        heartbeat_thread = threading.Thread(
            target=heartbeat, args=(job["id"],))
        heartbeat_thread.start()
        if job["resume_from"] is not None:
            logging.info(f"Resuming from {job['resume_from']}")
            download_checkpoint(job["checkpoint_bucket"], job["resume_from"])

        images = [{"bucket": job["data_bucket"], "key": image,
                   "filename": f"{config.input_dir}/{image.split('/')[-1]}"} for image in job["data_keys"]]
        concurrently_download(images)

        training_thread = threading.Thread(target=train, args=(job,))
        monitoring_thread = threading.Thread(
            target=monitor_checkpoint_directories, args=(config.output_dir, job["checkpoint_bucket"], job["checkpoint_prefix"], job["id"]))

        training_thread.start()
        monitoring_thread.start()
        logging.info(f"Training and monitoring threads started: {job['id']}")

        training_thread.join()
        logging.info(f"Training process exited: {job['id']}")
        stop_monitoring()
        monitoring_thread.join()
        logging.info(f"Monitoring process exited: {job['id']}")

        if "pytorch_lora_weights.safetensors" in os.listdir(config.output_dir):
            upload_file(f"{config.output_dir}/pytorch_lora_weights.safetensors",
                        job["checkpoint_bucket"], f"{job['checkpoint_prefix']}/pytorch_lora_weights.safetensors")
            send_complete_webhook(
                job["checkpoint_bucket"], f"{job['checkpoint_prefix']}/pytorch_lora_weights.safetensors", job["id"])

        heartbeat_active = False
        heartbeat_thread.join()
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
