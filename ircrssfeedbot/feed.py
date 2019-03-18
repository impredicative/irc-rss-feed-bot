import dataclasses
from typing import List, Union

import bitlyshortener
from descriptors import cachedproperty
import feedparser
import requests

from . import config
from .db import Database


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
        self._feed_config = config.INSTANCE[self.channel][self.name]
        self._is_new_feed = self.db.is_new_feed(self.channel, self.name)

    @property
    def _feed(self) -> bytes:
        response = requests.get(self.url, timeout=config.REQUEST_TIMEOUT, headers={'User-Agent': config.USER_AGENT})
        response.raise_for_status()
        return response.content

    @cachedproperty
    def entries(self) -> List[FeedEntry]:
        return [FeedEntry(title=e['title'], long_url=e['link']) for e in feedparser.parse(self._feed)['entries']]

    @cachedproperty
    def postable_entries(self) -> List[Union[FeedEntry, ShortenedFeedEntry]]:
        entries = self.unposted_entries[:config.MAX_POSTS_OF_NEW_FEED] if self._is_new_feed else self.unposted_entries

        # Shorten URLs
        if self._feed_config.get('shorten', True):
            long_urls = [entry.long_url for entry in entries]
            short_urls = self.url_shortener.shorten_urls(long_urls)
            entries = [ShortenedFeedEntry(e.title, e.long_url, short_urls[i]) for i, e in enumerate(entries)]

        return entries

    @cachedproperty
    def unposted_entries(self) -> List[FeedEntry]:
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
        return entries
