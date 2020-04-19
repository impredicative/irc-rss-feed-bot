"""Parse entries using `jmespath`."""
import dataclasses
import json
from typing import Dict, List, cast

import jmespath

from ..entry import BaseRawEntry as RawEntry
from .base import BaseParser


@dataclasses.dataclass
class Parser(BaseParser):
    """Parse entries using `jmespath`."""

    def __post_init__(self):
        self.data = json.loads(self.content)

    def _parse(self, selector: str) -> List[Dict[str, str]]:
        return jmespath.search(selector, self.data) or []

    @property
    def _raw_entries(self) -> List[RawEntry]:
        """Return a list of parsed raw entries."""
        return [RawEntry(e) for e in self._parse(cast(str, self.selector))]

    @property
    def _raw_urls(self) -> List[Dict[str, str]]:  # type: ignore
        """Return a list of parsed raw URLs to scrape."""
        return self._parse(self.follower) if self.follower else []
