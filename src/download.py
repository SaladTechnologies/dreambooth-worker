from api import get_api_session
import config
import concurrent.futures


def download_file(bucket, key, filename):
    api = get_api_session()
    token_url = f"{config.api_base_url}/download/token"
    download_token = api.get(
        token_url, params={"bucket": bucket, "key": key}).json()["token"]

    url = f"{config.api_base_url}/download/{bucket}/{key}"
    response = api.get(url, stream=True, headers={
        'x-download-token': download_token})
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
