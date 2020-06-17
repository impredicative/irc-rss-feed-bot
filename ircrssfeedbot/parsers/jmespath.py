"""Parse entries using `jmespath`."""
import dataclasses
import json
from typing import Dict, List, cast

import jmespath

from ..entry import RawFeedEntry
from ._base import BaseParser


@dataclasses.dataclass
class Parser(BaseParser):
    """Parse entries using `jmespath`."""

    def __post_init__(self):
        self.data = json.loads(self.content)

    def _parse(self, selector: str) -> List[Dict[str, str]]:
        return jmespath.search(selector, self.data) or []

    @property
    def _raw_urls(self) -> List[Dict[str, str]]:  # type: ignore
        """Return a list of parsed raw URLs to scrape."""
        return self._parse(self.follower) if self.follower else []

    @property
    def entries(self) -> List[RawFeedEntry]:
        """Return a list of parsed raw entries."""
        return [RawFeedEntry(e) for e in self._parse(cast(str, self.selector))]
