from dataclasses import dataclass
from typing import List

import feedparser


@dataclass
class FeedEntry:
    title: str
    long_url: str


@dataclass
class Feed:
    feed: bytes

    @property
    def entries(self) -> List[FeedEntry]:
        return [FeedEntry(title=e['title'], long_url=e['link']) for e in feedparser.parse(self.feed)['entries']]


if __name__ == '__main__':
    from urllib.request import urlopen
    content = urlopen('https://feeds.feedburner.com/blogspot/gJZg').read()
    for entry in Feed(content).entries:
        print(entry)
