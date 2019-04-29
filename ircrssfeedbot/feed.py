import dataclasses
import logging
import re
import sys
import time
from typing import Callable, Dict, List, Optional, Union

import bitlyshortener
import cachetools.func
from descriptors import cachedproperty
import feedparser
import requests

from . import config
from .db import Database
from .util.humanize import humanize_len

log = logging.getLogger(__name__)


@dataclasses.dataclass
class FeedEntry:
    title: str
    long_url: str

    @property
    def post_url(self) -> str:
        return self.long_url

    def is_listed(self, searchlist: Dict[str, List]) -> bool:
        for searchlist_key, val in {'title': self.title, 'url': self.long_url}.items():
            for searchlisted_pattern in searchlist.get(searchlist_key, []):
                if re.search(searchlisted_pattern, val):
                    log.debug('Feed entry %s matches %s pattern %s.', self, searchlist_key, searchlisted_pattern)
                    return True
        return False


@dataclasses.dataclass
class ShortenedFeedEntry(FeedEntry):
    short_url: str

    @property
    def post_url(self) -> str:
        return self.short_url


@dataclasses.dataclass
class Feed:
    channel: str
    name: str
    url: str = dataclasses.field(repr=False)
    db: Database = dataclasses.field(repr=False)
    url_shortener: bitlyshortener.Shortener = dataclasses.field(repr=False)

    def __post_init__(self):
        log.debug('Initializing instance of %s.', self)
        self._feed_config = config.INSTANCE['feeds'][self.channel][self.name]
        self.entries = self._entries()  # Entries are effectively cached at this point in time.
        log.debug('Initialized instance of %s.', self)

    def __str__(self):
        return f'feed {self.name} of {self.channel}'

    def _entries(self) -> List[FeedEntry]:
        # Note: A cache is useful if the same URL is to be read for multiple feeds, perhaps for multiple channels.
        return self._entries_cached(self.url)

    @cachetools.func.ttl_cache(maxsize=sys.maxsize, ttl=config.PERIOD_HOURS_MIN * 3600)
    def _entries_cached(self, url: str) -> List[FeedEntry]:
        feed_config = self._feed_config

        # Read URL
        log.debug('Resiliently retrieving content for %s.', self)
        for num_attempt in range(1, config.READ_ATTEMPTS_MAX + 1):
            try:
                response = requests.get(url, timeout=config.REQUEST_TIMEOUT,
                                        headers={'User-Agent': config.USER_AGENT})
                response.raise_for_status()
            except requests.RequestException as exc:
                log.warning('Error reading feed %s of %s having URL %s in attempt %s of %s: %s',
                            self.name, self.channel, self.url, num_attempt, config.READ_ATTEMPTS_MAX, exc)
                if num_attempt == config.READ_ATTEMPTS_MAX:
                    raise exc from None
                time.sleep(2 ** num_attempt)
            else:
                break
        content = response.content
        log.debug('Retrieved content of size %s for %s.', humanize_len(content), self)

        # Parse entries
        log.debug('Retrieving entries for %s.', self)
        entries = [FeedEntry(title=e['title'], long_url=e['link']) for e in feedparser.parse(content)['entries']]
        logger = log.debug if entries else log.warning
        logger('Retrieved %s entries for %s.', len(entries), self)

        # Keep only whitelisted entries
        whitelist = feed_config.get('whitelist', {})
        if whitelist:
            log.debug('Filtering %s entries using whitelist for %s.', len(entries), self)
            entries = [entry for entry in entries if entry.is_listed(whitelist)]
            log.debug('Filtered to %s entries using whitelist for %s.', len(entries), self)

        # Remove blacklisted entries
        blacklist = feed_config.get('blacklist', {})
        if blacklist:
            log.debug('Filtering %s entries using blacklist for %s.', len(entries), self)
            entries = [entry for entry in entries if not entry.is_listed(blacklist)]
            log.debug('Filtered to %s entries using blacklist for %s.', len(entries), self)

        # Enforce HTTPS URLs
        if feed_config.get('https', False):
            log.debug('Enforcing HTTPS for URLs in %s.', self)
            for entry in entries:
                if entry.long_url.startswith('http://'):
                    entry.long_url = entry.long_url.replace('http://', 'https://', 1)
            log.debug('Enforced HTTPS for URLs in %s.', self)

        # Substitute entries
        sub = feed_config.get('sub')
        if sub:
            log.debug('Substituting entries for %s.', self)
            re_sub: Callable[[str, Optional[Dict[str, str]]], str] = \
                lambda v, r: re.sub(r['pattern'], r['repl'], v) if r else v
            entries = [FeedEntry(title=re_sub(e.title, sub.get('title')), long_url=re_sub(e.long_url, sub.get('url')))
                       for e in entries]
            log.debug('Substituted entries for %s.', self)

        # Format entries
        format_config = feed_config.get('format')
        if format_config:
            log.debug('Formatting entries for %s.', self)
            format_re = format_config.get('re', {})
            format_str = format_config['str']
            for index, entry in enumerate(entries.copy()):  # May not strictly need `copy()`.
                params = {'title': entry.title, 'url': entry.long_url}
                for key, val in params.copy().items():
                    if key in format_re:
                        match = re.search(format_re[key], val)
                        if match:
                            params.update(match.groupdict())
                entries[index] = FeedEntry(title=format_str.get('title', '{title}').format_map(params),
                                           long_url=format_str.get('url', '{url}').format_map(params))
            log.debug('Formatted entries for %s.', self)

        log.debug('Returning %s entries for %s.', len(entries), self)
        return entries

    @cachedproperty
    def postable_entries(self) -> List[Union[FeedEntry, ShortenedFeedEntry]]:
        log.debug('Retrieving postable entries for %s.', self)
        entries = self.unposted_entries

        # Filter entries if new feed
        if self.db.is_new_feed(self.channel, self.name):
            log.debug('Filtering new feed %s having %s postable entries.', self, len(entries))
            max_posts = self._feed_config.get('new', config.NEW_FEED_POSTS_DEFAULT)
            max_posts = config.NEW_FEED_POSTS_MAX[max_posts]
            entries = entries[:max_posts]
            log.debug('Filtered new feed %s to %s postable entries given a max limit of %s entries.',
                      self, len(entries), max_posts)

        # Shorten URLs
        if entries and self._feed_config.get('shorten', True):
            log.debug('Shortening %s postable long URLs for %s.', len(entries), self)
            long_urls = [entry.long_url for entry in entries]
            short_urls = self.url_shortener.shorten_urls(long_urls)
            entries = [ShortenedFeedEntry(e.title, e.long_url, short_urls[i]) for i, e in enumerate(entries)]
            log.debug('Shortened %s postable long URLs for %s.', len(entries), self)

        log.debug('Returning %s postable entries for %s.', len(entries), self)
        return entries

    @cachedproperty
    def unposted_entries(self) -> List[FeedEntry]:
        log.debug('Retrieving unposted entries for %s.', self)
        entries = self.entries
        long_urls = [entry.long_url for entry in entries]
        dedup_strategy = self._feed_config.get('dedup', config.DEDUP_STRATEGY_DEFAULT)
        if dedup_strategy == 'channel':
            long_urls = self.db.select_unposted_for_channel(self.channel, self.name, long_urls)
        else:
            assert dedup_strategy == 'feed'
            long_urls = self.db.select_unposted_for_channel_feed(self.channel, self.name, long_urls)
        long_urls = set(long_urls)
        entries = [entry for entry in entries if entry.long_url in long_urls]
        log.debug('Returning %s unposted entries for %s.', len(entries), self)
        return entries
