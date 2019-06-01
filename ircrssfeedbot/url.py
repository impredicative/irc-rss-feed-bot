import logging
import random
import sys
import time
from typing import ClassVar, Dict, Set
import urllib.parse
import zlib

import cachetools.func
from descriptors import cachedproperty
import feedparser
import requests

from . import config
from .util.humanize import humanize_len

log = logging.getLogger(__name__)


class URLContent:

    def __init__(self, etag: str, content: bytes):
        self._etag = etag
        self._content = zlib.compress(content)

    @property  # Effectively read-only. Don't use cachedproperty here.
    def content(self) -> bytes:
        return zlib.decompress(self._content)

    @property  # Effectively read-only.
    def etag(self) -> str:
        return self._etag

    @cachedproperty
    def links(self) -> Set[str]:
        # Note: This is useful for approximately comparing semantic equivalence of two instances.
        return {e['link'] for e in feedparser.parse(self.content)['entries']}


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

    @staticmethod
    def _netloc(url: str) -> str:
        netloc = urllib.parse.urlparse(url).netloc.casefold()
        if netloc.startswith('www.'):
            netloc = netloc[4:]
        return netloc

    @classmethod
    @cachetools.func.ttl_cache(maxsize=sys.maxsize, ttl=config.URL_CACHE_TTL)
    def _ttl_cached_compressed_url_content(cls, url: str) -> bytes:
        log.debug('Compressed content of %s will be stored in the TTL cache.', url)
        return zlib.compress(cls._url_content(url))

    @classmethod
    def _url_content(cls, url: str) -> bytes:
        # Note: This method is feed agnostic. To prevent bugs, the return value of this method must be immutable.
        # Note: TTL cache is useful if the same URL is to be read for multiple feeds, sometimes for multiple channels.
        netloc = cls._netloc(url)

        # Define headers
        headers = {'User-Agent': config.USER_AGENT}
        test_etag = False
        if netloc not in config.ETAG_CACHE_PROHIBITED_NETLOCS:
            try:
                etag_cache = cls._etag_cache[url]
            except KeyError:
                pass
            else:
                test_etag = random.random() <= config.ETAG_TEST_PROBABILITY
                if not test_etag:
                    headers['If-None-Match'] = etag_cache.etag

        # Read URL
        log.debug('Resiliently retrieving content for %s.', url)
        for num_attempt in range(1, config.READ_ATTEMPTS_MAX + 1):
            try:
                response = requests.get(url, timeout=config.REQUEST_TIMEOUT, headers=headers)
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
                    if etag_cache.links == url_content.links:
                        log.debug('Etag test passed for %s with etag %s.', url, etag)
                    else:
                        # Disable and delete cache
                        config.ETAG_CACHE_PROHIBITED_NETLOCS.add(netloc)
                        for cached_url in list(cls._etag_cache):  # Thread-safety is not important in this block.
                            if cls._netloc(cached_url) == netloc:
                                cls._del_etag_cache(url)
                        config.runtime.alert(
                            f'Etag test failed for {url} with etag {repr(etag)}. '
                            f'The semantic content was unexpectedly found to be changed whereas the etag stayed '
                            f'unchanged. '
                            f'The previously cached content has {len(etag_cache.links)} unique links and the '
                            f'dissimilar current content has {len(url_content.links)}. ', log.warning)
                        config.runtime.alert(
                            f'The etag cache has been disabled for the duration of the bot process for all {netloc} '
                            f'feed URLs. '
                            'The semantic content mismatch should be reported to the site administrator.', log.warning)
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
