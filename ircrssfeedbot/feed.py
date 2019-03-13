from dataclasses import dataclass
import types
from typing import List

import bitlyshortener
import feedparser
import requests

from ircrssfeedbot import config

_bitly_shortener = bitlyshortener.Shortener(tokens=config.INSTANCE['tokens']['bitly'],
                                            max_cache_size=config.BITLY_SHORTENER_MAX_CACHE_SIZE)


@dataclass
class FeedEntry:
    title: str
    long_url: str
    short_url: str


@dataclass
class Feed:
    url: str

    @property
    def _feed(self) -> bytes:
        response = requests.get(self.url, timeout=config.REQUEST_TIMEOUT, headers={'User-Agent': config.USER_AGENT})
        response.raise_for_status()
        return response.content

    @property
    def entries(self) -> List[FeedEntry]:
        entries = feedparser.parse(self._feed)['entries']
        entries = [types.SimpleNamespace(title=entry['title'], long_url=entry['link']) for entry in entries]
        long_urls = [entry.long_url for entry in entries]
        short_urls = _bitly_shortener.shorten_urls(long_urls)
        entries = [FeedEntry(title=entry.title, long_url=entry.long_url, short_url=short_urls[i])
                   for i, entry in enumerate(entries)]
        return entries


if __name__ == '__main__':
    for entry in Feed('https://feeds.feedburner.com/blogspot/gJZg').entries:
        print(entry)
