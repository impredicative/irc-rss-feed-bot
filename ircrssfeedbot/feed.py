from dataclasses import dataclass
from typing import List

import feedparser
import requests

from ircrssfeedbot import config


@dataclass
class FeedEntry:
    title: str
    long_url: str


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
        return [FeedEntry(title=e['title'], long_url=e['link']) for e in feedparser.parse(self._feed)['entries']]


if __name__ == '__main__':
    for entry in Feed('https://feeds.feedburner.com/blogspot/gJZg').entries:
        print(entry)
