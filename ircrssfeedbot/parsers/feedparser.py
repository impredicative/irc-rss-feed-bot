"""Parse entries using `feedparser`."""
from typing import List

import feedparser

from ..entry import BaseRawEntry
from ..util.lxml import sanitize_xml
from .base import BaseParser


class RawEntry(BaseRawEntry):
    """Raw feed entry."""

    @property
    def link(self) -> str:
        link = self.get("link") or self["links"][0]["href"]
        return link.strip()  # e.g. for https://feeds.buzzsprout.com/188368.rss

    @property
    def categories(self) -> List[str]:
        return [tag["term"].strip() for tag in self.get("tags", [])]


class Parser(BaseParser):
    """Parse entries using `feedparser`."""

    @property
    def _raw_entries(self) -> List[RawEntry]:
        """Return a list of raw entries."""
        content = sanitize_xml(self.content)  # e.g. for unescaped "&" char in https://deepmind.com/blog/feed/basic/
        return [RawEntry(e) for e in feedparser.parse(content.lstrip())["entries"]]
