from dataclasses import dataclass
from typing import List

from descriptors import cachedproperty
import feedparser
import requests

from ircrssfeedbot import config


@dataclass
class FeedEntry:
    title: str
    long_url: str


@dataclass
class ShortenedFeedEntry(FeedEntry):
    short_url: str


@dataclass
class Feed:
    name: str
    url: str

    @property
    def _feed(self) -> bytes:
        response = requests.get(self.url, timeout=config.REQUEST_TIMEOUT, headers={'User-Agent': config.USER_AGENT})
        response.raise_for_status()
        return response.content

    @cachedproperty
    def entries(self) -> List[FeedEntry]:
        entries = feedparser.parse(self._feed)['entries']
        entries = [FeedEntry(title=entry['title'], long_url=entry['link']) for entry in entries]
        return entries
