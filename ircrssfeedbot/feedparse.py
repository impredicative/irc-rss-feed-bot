from dataclasses import dataclass
from typing import List

import feedparser


@dataclass
class FeedEntry:
    title: str
    long_url: str


@dataclass
class FeedEntryWithShortURL(FeedEntry):
    short_url: str = None


@dataclass
class Feed:
    feed: bytes

    @property
    def entries(self, *, shorten_links: bool = True) -> List[FeedEntry]:
        entries_list = [FeedEntry(entry['title'], entry['link']) for entry in feedparser.parse(self.feed)['entries']]
        if shorten_links:
            pass  # TODO: Shorten links.
        return entries_list


if __name__ == '__main__':
    from urllib.request import urlopen
    content = urlopen('https://feeds.feedburner.com/blogspot/gJZg').read()
    for entry in Feed(content).entries:
        print(entry)
