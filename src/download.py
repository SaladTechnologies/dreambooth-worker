from api import get_api_session
import config
import concurrent.futures
import logging


def download_file(bucket, key, filename):
    api = get_api_session()
    token_url = f"{config.api_base_url}/download/token"
    download_resp = api.get(
        token_url, params={"bucket": bucket, "key": key})

    try:
        download_resp.raise_for_status()
    except Exception as e:
        logging.error(f"Error: {e.response.text}")
        raise e

    download_token = download_resp.json()["token"]

    url = f"{config.api_base_url}/download/{bucket}/{key}"
    try:
        response = api.get(url, stream=True, headers={
            'x-download-token': download_token})
    except Exception as e:
        logging.error(f"Error: Failed to download {key} from {bucket}: {e}")
        raise e
    else:
        try:
            response.raise_for_status()
        except Exception as e:
            logging.error(e.response.text)
            raise e
        else:
            with open(filename, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
            logging.info(f"Downloaded {key} from {bucket} to {filename}")


def concurrently_download(files):
    with concurrent.futures.ThreadPoolExecutor(10) as executor:
        futures = [executor.submit(
            download_file, file["bucket"], file["key"], file["filename"]) for file in files]
        concurrent.futures.wait(futures)
        for future in futures:
            future.result()
