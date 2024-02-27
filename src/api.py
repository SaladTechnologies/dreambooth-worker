import requests
import config
from requests.adapters import HTTPAdapter, Retry


def get_api_session():
    api = requests.Session()
    api.headers.update({"x-api-key": config.api_key})
    retries = Retry(
        total=3,
        status_forcelist=[400, 500, 502, 503, 504],
        status=3,
        backoff_factor=1,
        raise_on_status=False)
    api.mount("https://", HTTPAdapter(max_retries=retries))
    return api
