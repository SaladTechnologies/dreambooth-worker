from api import get_api_session
import config
import logging


def send_webhook(url, bucket_name, key, job_id):
    api = get_api_session()
    try:
        if url is None:
            return

        payload = {
            "bucket_name": bucket_name,
            "key": key,
            "machine_id": config.salad_machine_id,
            "container_group_id": config.salad_container_group_id,
            "organization_name": config.salad_organization_name,
            "project_name": config.salad_project_name,
            "container_group_name": config.salad_container_group_name,
            "job_id": job_id,
        }
        payload = {k: v for k, v in payload.items() if v is not None}

        response = api.post(url, json=payload)
        response.raise_for_status()
        logging.info("Webhook sent successfully.")
    except Exception as e:
        logging.error(e.response.json() if hasattr(e, "response") else e)


def send_progress_webhook(bucket_name, key, job_id):
    url = config.api_base_url + "/progress"
    logging.info(f"Reporting Job Progress: {key} uploaded for job {job_id}")
    send_webhook(url, bucket_name, key, job_id)


def send_complete_webhook(bucket_name, key, job_id):
    url = config.api_base_url + "/complete"
    logging.info(f"Reporting Job Complete: {key} uploaded for job {job_id}")
    send_webhook(url, bucket_name, key, job_id)


def send_failed_webhook(bucket_name, key, job_id):
    url = config.api_base_url + "/fail"
    logging.info(f"Reporting Job Failed: {key} uploaded for job {job_id}")
    send_webhook(url, bucket_name, key, job_id)


def send_heartbeat(job_id):
    api = get_api_session()
    url = config.api_base_url + f"/heartbeat/{job_id}"
    payload = {
        "machine_id": config.salad_machine_id,
        "container_group_id": config.salad_container_group_id,
        "organization_name": config.salad_organization_name,
        "project_name": config.salad_project_name,
        "container_group_name": config.salad_container_group_name,
    }
    payload = {k: v for k, v in payload.items() if v is not None}
    response = api.post(url, json=payload)
    response.raise_for_status()
