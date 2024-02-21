import math
import os
import requests
from requests.adapters import HTTPAdapter, Retry
import concurrent.futures
import config

# Configure the part size to be 10MB. 5MB is the minimum part size, except for the last part
partsize = 10 * 1024 * 1024


def upload_file(filename, bucket, key):
    global partsize

    token_url = f"{config.api_base_url}/upload/token"
    upload_token = requests.get(
        token_url, params={"bucket": bucket, "key": key}, headers={"x-api-key": config.api_key}).json()["token"]

    url = f"{config.api_base_url}/upload/{bucket}/{key}"

    # Create the multipart upload
    uploadId = requests.post(
        url, params={"action": "mpu-create"}, headers={'x-upload-token': upload_token, "x-api-key": config.api_key}).json()["uploadId"]

    part_count = math.ceil(os.stat(filename).st_size / partsize)
    # Create an executor for up to 25 concurrent uploads.
    executor = concurrent.futures.ThreadPoolExecutor(25)
    # Submit a task to the executor to upload each part
    futures = [
        executor.submit(upload_part, filename, partsize,
                        url, uploadId, index, upload_token)
        for index in range(part_count)
    ]
    concurrent.futures.wait(futures)
    # get the parts from the futures
    uploaded_parts = [future.result() for future in futures]

    # complete the multipart upload
    response = requests.post(
        url,
        params={"action": "mpu-complete", "uploadId": uploadId},
        headers={'x-upload-token': upload_token, "x-api-key": config.api_key},
        json={"parts": uploaded_parts},
    )
    if response.status_code == 200:
        print("completed multipart upload")
    else:
        print(response.text)


def upload_part(filename, partsize, url, uploadId, index, token):
    # Open the file in rb mode, which treats it as raw bytes rather than attempting to parse utf-8
    with open(filename, "rb") as file:
        file.seek(partsize * index)
        part = file.read(partsize)

    # Retry policy for when uploading a part fails
    api = requests.Session()
    api.headers.update({"x-api-key": config.api_key, "x-upload-token": token})
    retries = Retry(total=3, status_forcelist=[400, 500, 502, 503, 504])
    api.mount("https://", HTTPAdapter(max_retries=retries))

    return api.put(
        url,
        params={
            "action": "mpu-uploadpart",
            "uploadId": uploadId,
            "partNumber": str(index + 1),
        },
        data=part,
    ).json()
