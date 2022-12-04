"""requests utilities."""
import functools

import requests

from ..config import CACHE_MAXSIZE__URL_REDIRECT, REQUEST_TIMEOUT, SECONDS_PER_HEAD_REQUEST
from .time import Throttle


@functools.lru_cache(CACHE_MAXSIZE__URL_REDIRECT)
def find_redirect(url: str) -> str:
    """Return the location that the given URL redirects to.

    If there is no redirect, the given URL is returned instead.
    """
    # Ref: https://stackoverflow.com/a/68433381/
    with Throttle(SECONDS_PER_HEAD_REQUEST):
        response = requests.head(url, allow_redirects=False, timeout=REQUEST_TIMEOUT)
    return response.headers["Location"] if response.is_redirect else url
