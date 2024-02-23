import math
import os
from api import get_api_session
import concurrent.futures
import config

# Configure the part size to be 10MB. 5MB is the minimum part size, except for the last part
partsize = 10 * 1024 * 1024


def upload_file(filename, bucket, key):
    global partsize

    api = get_api_session()
    token_url = f"{config.api_base_url}/upload/token"
    upload_token = api.get(
        token_url, params={"bucket": bucket, "key": key}).json()["token"]

    url = f"{config.api_base_url}/upload/{bucket}/{key}"

    # Create the multipart upload
    uploadId = api.post(
        url, params={"action": "mpu-create"}, headers={'x-upload-token': upload_token}).json()["uploadId"]

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
    response = api.post(
        url,
        params={"action": "mpu-complete", "uploadId": uploadId},
        headers={'x-upload-token': upload_token},
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
    api = get_api_session()
    api.headers.update({"x-upload-token": token})

    return api.put(
        url,
        params={
            "action": "mpu-uploadpart",
            "uploadId": uploadId,
            "partNumber": str(index + 1),
        },
        data=part,
    ).json()
