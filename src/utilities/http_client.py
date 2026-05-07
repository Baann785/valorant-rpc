import requests

from .logging import Logger


class HTTPClient:
    DEFAULT_TIMEOUT = 5

    @staticmethod
    def get_json(url, timeout=DEFAULT_TIMEOUT, headers=None, params=None):
        try:
            response = requests.get(url, timeout=timeout, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            Logger.exception(f"HTTP request failed: {url}")
            raise
        except ValueError:
            Logger.exception(f"Invalid JSON response: {url}")
            raise
