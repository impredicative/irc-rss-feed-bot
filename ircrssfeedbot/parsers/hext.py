"""Parse entries using `hext`."""
import dataclasses
import html
from typing import Dict, List, cast

import hext

from ..entry import BaseRawEntry
from .base import BaseParser


class RawEntry(BaseRawEntry):
    """Raw feed entry."""

    @property
    def categories(self) -> List[str]:
        return [html.unescape(c) for c in super().categories]


@dataclasses.dataclass
class Parser(BaseParser):
    """Parse entries using `hext`."""

    def __post_init__(self):
        self.html = hext.Html(self.content.decode())

    def _parse(self, selector: str) -> List[Dict[str, str]]:
        return hext.Rule(selector).extract(self.html)

    @property
    def _raw_entries(self) -> List[RawEntry]:
        """Return a list of parsed raw entries."""
        return [RawEntry(e) for e in self._parse(cast(str, self.selector))]

    @property
    def _raw_urls(self) -> List[Dict[str, str]]:  # type: ignore
        """Return a list of parsed raw URLs to scrape."""
        return self._parse(self.follower) if self.follower else []
