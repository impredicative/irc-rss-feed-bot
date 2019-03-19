import dataclasses
import logging
from typing import List, Union

import bitlyshortener
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
    def url(self) -> str:
        return self.long_url


@dataclasses.dataclass
class ShortenedFeedEntry(FeedEntry):
    short_url: str

    @property
    def url(self) -> str:
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
        self._feed_config = config.INSTANCE[self.channel][self.name]
        self._is_new_feed = self.db.is_new_feed(self.channel, self.name)
        log.debug('Initialized instance of %s.', self)

    @property
    def _feed(self) -> bytes:
        log.debug('Retrieving content for %s.', self)
        response = requests.get(self.url, timeout=config.REQUEST_TIMEOUT, headers={'User-Agent': config.USER_AGENT})
        response.raise_for_status()
        content = response.content
        log.debug('Returning content of size %s for %s.', humanize_len(content), self)
        return content

    @cachedproperty
    def entries(self) -> List[FeedEntry]:
        log.debug('Retrieving entries for %s.', self)
        entries = [FeedEntry(title=e['title'], long_url=e['link']) for e in feedparser.parse(self._feed)['entries']]
        log.debug('Returning %s entries for %s.', len(entries), self)
        return entries

    @cachedproperty
    def postable_entries(self) -> List[Union[FeedEntry, ShortenedFeedEntry]]:
        log.debug('Retrieving postable entries for %s.', self)
        entries = self.unposted_entries[:config.MAX_POSTS_OF_NEW_FEED] if self._is_new_feed else self.unposted_entries

        # Shorten URLs
        if self._feed_config.get('shorten', True):
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
        dedup_strategy = self._feed_config.get('dedup', 'feed')
        if dedup_strategy == 'feed':
            long_urls = self.db.select_unposted_for_channel_feed(self.channel, self.name, long_urls)
        else:
            assert dedup_strategy == 'channel'
            long_urls = self.db.select_unposted_for_channel(self.channel, long_urls)
        long_urls = set(long_urls)
        entries = [entry for entry in entries if entry.long_url in long_urls]
        log.debug('Returning %s unposted entries for %s.', len(entries), self)
        return entries
