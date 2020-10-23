"""Parse entries using `feedparser`."""
import dataclasses
from typing import List

import feedparser

from ..entry import RawFeedEntry as BaseRawFeedEntry
from ..gnews import decode_google_news_url
from ..util.lxml import sanitize_xml
from ._base import BaseParser


class RawFeedEntry(BaseRawFeedEntry):
    """Raw feed entry."""

    @property
    def link(self) -> str:
        link = self.get("link") or self["links"][0]["href"]
        link = link.strip()  # e.g. for https://feeds.buzzsprout.com/188368.rss
        link = decode_google_news_url(link).strip()
        if link.startswith("http://feedproxy.google.com/") and (origlink := self.get("feedburner_origlink")):
            link = origlink.strip()
        return link

    @property
    def categories(self) -> List[str]:
        return [term for tag in self.get("tags", []) if (term := (tag["term"] or "").strip())]  # tag["term"] is None in https://www.sciencemag.org/rss/news_current.xml


@dataclasses.dataclass
class Parser(BaseParser):
    """Parse entries using `feedparser`."""

    @property
    def entries(self) -> List[RawFeedEntry]:
        """Return a list of parsed raw entries."""
        content = sanitize_xml(self.content)  # e.g. for unescaped "&" char in https://deepmind.com/blog/feed/basic/
        return [RawFeedEntry(e) for e in feedparser.parse(content.lstrip())["entries"]]
