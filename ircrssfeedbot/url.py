"""URL reader and content."""
import logging
import random
import time
import zlib
from typing import Optional, cast

import cachetools.func
import diskcache
import requests

from . import config
from .util.datetime import timedelta_desc
from .util.hashlib import hash4
from .util.humanize import humanize_size
from .util.timeit import Timer
from .util.urllib import url_to_netloc

log = logging.getLogger(__name__)

_COMPRESSION_CACHE_MAXSIZE = 8  # Meant for short term reuse.
_COMPRESSION_CACHE_TTL = 60


@cachetools.func.ttl_cache(maxsize=_COMPRESSION_CACHE_MAXSIZE, ttl=_COMPRESSION_CACHE_TTL)
def _compress(content: bytes) -> bytes:
    return zlib.compress(content)


@cachetools.func.ttl_cache(maxsize=_COMPRESSION_CACHE_MAXSIZE, ttl=_COMPRESSION_CACHE_TTL)
def _decompress(content: bytes) -> bytes:
    return zlib.decompress(content)


class URLContent:
    """URL content."""

    CURRENT_VERSION = 1

    class Approach:
        """Approaches for providing the content of a URL."""

        CACHE_HIT = "read from unexpired cache"
        CACHE_ETAG_HIT = "read from cache having matching etag"
        READ = "read bypassing cache"

    def __init__(self, content: bytes, etag: Optional[str], approach: str):
        self.time = time.time()
        self.version = self.CURRENT_VERSION
        self._content = _compress(content)
        self.etag = etag
        self.approach = approach

    @property
    def age(self) -> float:
        """Return the age of the content."""
        return time.time() - self.time

    @property  # Effectively read-only. For memory and diskcache efficiency, don't use cachedproperty here.
    def content(self) -> bytes:
        """Return URL content."""
        return _decompress(self._content)

    @property
    def etag_type(self) -> str:
        """Return whether the ETag is "strong" or "weak"."""
        assert self.etag
        if self.is_etag_strong:
            return "strong"
        assert self.is_etag_weak
        return "weak"

    @property
    def is_etag_strong(self) -> bool:
        """Return whether the ETag is a strong ETag.

        This requires an ETag to be available.
        """
        return not cast(str, self.etag).startswith(("W/", "w/"))  # Only uppercase "W/" has been observed.

    @property
    def is_etag_weak(self) -> bool:
        """Return whether the ETag is a weak ETag.

        This requires an ETag to be available.
        """
        return cast(str, self.etag).startswith(("W/", "w/"))  # Only uppercase "W/" has been observed.

    @property
    def is_version_current(self) -> bool:
        """Return whether the instance version is the current version.

        This check can be relevant after restoring a pickled instance.
        """
        return self.version == self.CURRENT_VERSION


class URLReader:
    """URL reader."""

    def __init__(self, max_cache_age: float):
        diskcache_path = config.DISKCACHE_PATH / self.__class__.__name__
        self._cache = diskcache.Cache(directory=diskcache_path, timeout=2, size_limit=config.DISKCACHE_SIZE_LIMIT)
        self._max_cache_age = max_cache_age
        log.debug(f"Initialized disk cache having max age {timedelta_desc(max_cache_age)} in {diskcache_path}.")

    def __delitem__(self, url: str) -> None:
        try:
            del self._cache[url]
        except KeyError:
            log.debug(f"Unable to delete nonexistent URL content from cache for {url}.")
        else:
            log.info(f"Deleted cached URL content for {url}.")

    def __getitem__(  # pylint: disable=too-many-branches,too-many-locals,too-many-statements
        self, url: str
    ) -> URLContent:

        # Reuse cache if possible
        if cached_url_content := self._cache.get(url):
            if cached_url_content.is_version_current:
                # Check age
                cache_age_desc = f"{timedelta_desc(cached_url_content.age)}/{timedelta_desc(self._max_cache_age)}"
                desc = f"URL content having age {cache_age_desc} from cache for {url}"
                if cached_url_content.age <= self._max_cache_age:
                    log.debug(f"Reusing and returning {desc}.")
                    cached_url_content.approach = URLContent.Approach.CACHE_HIT
                    return cached_url_content
                log.debug(f"Found expired {desc}.")  # Will still be checked for ETag.
            else:
                log.info(
                    f"Cached URL content having version {cached_url_content.version} for {url} will be deleted "
                    f"from the cache because is not the current version {cached_url_content.CURRENT_VERSION}."
                )
                del self._cache[url]
                cached_url_content = None
        else:
            log.debug(f"Unable to retrieve nonexistent URL content from cache for {url}.")

        # Define request headers
        netloc = url_to_netloc(url)
        request_headers = {"User-Agent": config.USER_AGENT_OVERRIDES.get(netloc, config.USER_AGENT_DEFAULT)}
        has_cached_etag = bool(cached_url_content and cached_url_content.etag)
        is_etag_cache_allowed = netloc not in config.ETAG_CACHE_PROHIBITED_NETLOCS
        test_cached_etag = bool(
            has_cached_etag
            and cached_url_content.is_etag_strong
            and is_etag_cache_allowed
            and (random.random() <= config.ETAG_TEST_PROBABILITY)
        )
        if has_cached_etag:
            log.debug(
                f"Expired URL content from cache for {url} has {cached_url_content.etag_type} ETag "
                f"{cached_url_content.etag}."
            )
            if test_cached_etag:
                log.debug(
                    f"The cached {cached_url_content.etag_type} ETag {cached_url_content.etag} for {url} will "
                    f"be tested for a mismatch."
                )
            elif is_etag_cache_allowed:
                request_headers["If-None-Match"] = cached_url_content.etag
                log.debug(f"Added request header If-None-Match={request_headers['If-None-Match']} for {url}.")

        # Request URL
        log.debug(f"Resiliently retrieving content for {url}.")
        assert not url.startswith("file://")
        timer = Timer()
        for num_attempt in range(1, config.READ_ATTEMPTS_MAX + 1):
            try:
                response = requests.Session().get(url, timeout=config.REQUEST_TIMEOUT, headers=request_headers)
                # Note: requests.Session may be relevant for reading a page which requires cookies to be accepted.
                response.raise_for_status()
            except requests.RequestException as exc:
                log.info(f"Error reading {url} in attempt {num_attempt} of {config.READ_ATTEMPTS_MAX}: {exc}")
                if num_attempt == config.READ_ATTEMPTS_MAX:
                    raise exc from None
                time.sleep(2 ** num_attempt)
            else:
                log.debug(
                    f"Received response having status code {response.status_code} in attempt {num_attempt} for "
                    f"{url} in {timer}."
                )
                break

        # Reuse ETag cache if possible
        if response.status_code == 304:  # pylint: disable=too-many-nested-blocks
            # Note: 304 = Not Modified.
            assert all((cached_url_content, has_cached_etag, not test_cached_etag, request_headers["If-None-Match"]))
            url_content = URLContent(
                content=cached_url_content.content,  # Sets updated time attribute too.
                etag=cached_url_content.etag,
                approach=URLContent.Approach.CACHE_ETAG_HIT,
            )
            log.debug(
                f"Reusing, recaching, and returning unchanged ETag matched URL content of size "
                f"{humanize_size(url_content.content)} from cache for {url}."
            )
            self._cache[url] = url_content
            return url_content

        # Cache content
        url_content = URLContent(
            content=response.content, etag=response.headers.get("ETag"), approach=URLContent.Approach.READ
        )
        self._cache[url] = url_content
        log.debug(f"Cached URL content of size {humanize_size(url_content.content)} for {url}.")

        # Test ETag
        if test_cached_etag and (url_content.etag == cached_url_content.etag):
            if url_content.content == cached_url_content.content:
                log.debug(f"ETag test passed with {url_content.etag_type} ETag {url_content.etag} for {url}.")
            else:
                config.runtime.alert(
                    f"Etag test failed for {url} with unchanged {url_content.etag_type} etag {url_content.etag!r}. "
                    "The content was unexpectedly found to be changed whereas the etag stayed unchanged. "
                    f"The previously cached content has length {len(cached_url_content.content):,} with "
                    f"hash {hash4(cached_url_content.content)} and the dissimilar current content has "
                    f"length {len(url_content.content):,} with hash {hash4(url_content.content)}. ",
                    log.warning,
                )
                config.runtime.alert(
                    f"The etag cache will be disabled for the duration of the bot process for all {netloc} feed URLs. "
                    "The content mismatch should be reported to the site administrator and also to the bot's "
                    "maintainer.",
                    log.warning,
                )
                # Disable and delete cache for netloc
                config.ETAG_CACHE_PROHIBITED_NETLOCS.add(netloc)
                for cached_url in self._cache:
                    if url_to_netloc(cached_url) == netloc:
                        del self._cache[cached_url]

        return url_content
