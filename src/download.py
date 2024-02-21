import requests
import config
import concurrent.futures


def download_file(bucket, key, filename):
    token_url = f"{config.api_base_url}/download/token"
    download_token = requests.get(
        token_url, params={"bucket": bucket, "key": key}, headers={"x-api-key": config.api_key}).json()["token"]

    url = f"{config.api_base_url}/download/{bucket}/{key}"
    response = requests.get(url, stream=True, headers={
        'x-download-token': download_token, "x-api-key": config.api_key})
    response.raise_for_status()
    with open(filename, "wb") as file:
        for chunk in response.iter_content(chunk_size=8192):
            file.write(chunk)
    print(f"downloaded {key} from {bucket} to {filename}")


def concurrently_download(files):
    with concurrent.futures.ThreadPoolExecutor(10) as executor:
        futures = [executor.submit(
            download_file, file["bucket"], file["key"], file["filename"]) for file in files]
        concurrent.futures.wait(futures)
        for future in futures:
            future.result()
