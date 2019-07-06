import logging
import random
import sys
import time
from typing import ClassVar, Dict
import zlib

import cachetools.func
import requests

from . import config
from .util.hashlib import hash4
from .util.humanize import humanize_len
from .util.urllib import url_to_netloc

log = logging.getLogger(__name__)


class URLContent:

    def __init__(self, etag: str, content: bytes):
        self._etag = etag
        self._content = zlib.compress(content)

    @property  # Effectively read-only. For memory efficiency, don't use cachedproperty here.
    def content(self) -> bytes:
        return zlib.decompress(self._content)

    @property  # Effectively read-only.
    def etag(self) -> str:
        return self._etag

    @property
    def is_etag_strong(self) -> bool:
        return not self.is_etag_weak

    @property
    def is_etag_weak(self) -> bool:
        return self._etag.startswith(('W/', 'w/'))  # Only uppercase "W/" has been observed.


class URLReader:
    _etag_cache: ClassVar[Dict[str, URLContent]] = {}

    @classmethod
    def _del_etag_cache(cls, url: str) -> None:
        try:
            del cls._etag_cache[url]
        except KeyError:
            pass
        else:
            log.info('Deleted cached content for %s from etag cache.', url)

    @classmethod
    @cachetools.func.ttl_cache(maxsize=sys.maxsize, ttl=config.URL_CACHE_TTL)
    def _ttl_cached_compressed_url_content(cls, url: str) -> bytes:
        log.debug('Compressed content of %s will be stored in the TTL cache.', url)
        return zlib.compress(cls._url_content(url))

    @classmethod
    def _url_content(cls, url: str) -> bytes:
        # Note: This method is feed agnostic. To prevent bugs, the return value of this method must be immutable.
        # Note: TTL cache is useful if the same URL is to be read for multiple feeds, sometimes for multiple channels.
        netloc = url_to_netloc(url)

        # Define headers
        headers = {'User-Agent': config.USER_AGENT_OVERRIDES.get(netloc, config.USER_AGENT_DEFAULT)}
        test_etag = False
        if netloc not in config.ETAG_CACHE_PROHIBITED_NETLOCS:
            try:
                etag_cache = cls._etag_cache[url]
            except KeyError:
                pass
            else:
                test_etag = etag_cache.is_etag_strong and (random.random() <= config.ETAG_TEST_PROBABILITY)
                # Note: A weak etag can also be tested but not as easily. It may be unlikely to have a mismatch anyway.
                if not test_etag:
                    headers['If-None-Match'] = etag_cache.etag

        # Read URL
        log.debug('Resiliently retrieving content for %s.', url)
        for num_attempt in range(1, config.READ_ATTEMPTS_MAX + 1):
            try:
                response = requests.Session().get(url, timeout=config.REQUEST_TIMEOUT, headers=headers)
                # Note: requests.Session may be relevant for scraping a page which requires cookies to be accepted.
                response.raise_for_status()
            except requests.RequestException as exc:
                log.warning('Error reading %s in attempt %s of %s: %s', url, num_attempt, config.READ_ATTEMPTS_MAX, exc)
                if num_attempt == config.READ_ATTEMPTS_MAX:
                    raise exc from None
                time.sleep(2 ** num_attempt)
            else:
                break

        # Get and cache content
        if response.status_code == 304:
            content = etag_cache.content
            log.debug('Reused cached content for %s from etag cache.', url)
        else:  # 200
            content = response.content
            etag = response.headers.get('ETag')

            if etag:
                url_content = URLContent(etag, content)

                # Conditionally test, disable, delete, and update cache
                if test_etag and (etag_cache.etag == etag):
                    if etag_cache.content == content:
                        log.debug('Etag test passed for %s with etag %s.', url, etag)
                    else:
                        # Disable and delete cache
                        config.ETAG_CACHE_PROHIBITED_NETLOCS.add(netloc)
                        for cached_url in list(cls._etag_cache):  # Thread-safety is not important in this block.
                            if url_to_netloc(cached_url) == netloc:
                                cls._del_etag_cache(url)
                        config.runtime.alert(
                            f'Etag test failed for {url} with strong etag {repr(etag)}. '
                            f'The content was unexpectedly found to be changed whereas the etag stayed unchanged. '
                            f'The previously cached content has length {len(etag_cache.content)} with '
                            f'hash {hash4(etag_cache.content)} and the dissimilar current content has '
                            f'length {len(content)} with hash {hash4(content)}. ', log.warning)
                        config.runtime.alert(
                            f'The etag cache has been disabled for the duration of the bot process for all {netloc} '
                            f'feed URLs. '
                            "The content mismatch should be reported to the site administrator and also to the bot's "
                            "maintainer.", log.warning)
                else:
                    # Update cache
                    action = 'Updated cached content' if (url in cls._etag_cache) else 'Cached content'
                    cls._etag_cache[url] = url_content
                    log.debug('%s for %s having etag %s.', action, url, etag)
            else:
                # Delete cache
                cls._del_etag_cache(url)
        log.debug('Resiliently retrieved content of size %s for %s.', humanize_len(content), url)

        # Note: Entry parsing is not done in this method in order to permit mutability of individual entries.
        return content

    @classmethod
    def url_content(cls, url: str) -> bytes:
        return zlib.decompress(cls._ttl_cached_compressed_url_content(url)) \
            if (url in config.INSTANCE['repeated_urls']) else cls._url_content(url)
