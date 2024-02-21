import requests
import config
import logging

api = requests.Session()
api.headers.update({"x-api-key": config.api_key})


def send_webhook(url, bucket_name, key, job_id):
    try:
        if url is None:
            return

        response = api.post(url, json={
            "bucket_name": bucket_name,
            "key": key,
            "machine_id": config.salad_machine_id,
            "container_group_id": config.salad_container_group_id,
            "organization_name": config.salad_organization_name,
            "project_name": config.salad_project_name,
            "container_group_name": config.salad_container_group_name,
            "job_id": job_id,
        })
        response.raise_for_status()
        logging.info("Progress webhook sent successfully.")
    except Exception as e:
        logging.error(f"Error: {e}")


def send_progress_webhook(bucket_name, key, job_id):
    url = config.api_base_url + "/progress"
    logging.info(f"Reporting Progress: {key} uploaded for job {job_id}")
    send_webhook(url, bucket_name, key, job_id)


def send_complete_webhook(bucket_name, key, job_id):
    url = config.api_base_url + "/complete"
    logging.info(f"Reporting Complete: {key} uploaded for job {job_id}")
    send_webhook(url, bucket_name, key, job_id)


def send_failed_webhook(bucket_name, key, job_id):
    url = config.api_base_url + "/fail"
    logging.info(f"Reporting Failed: {key} uploaded for job {job_id}")
    send_webhook(url, bucket_name, key, job_id)


def send_heartbeat(job_id):
    url = config.api_base_url + f"/heartbeat/{job_id}"
    response = api.post(url)
    response.raise_for_status()
