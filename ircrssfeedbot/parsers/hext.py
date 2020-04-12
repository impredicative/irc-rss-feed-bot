"""Parse entries using `hext`."""
import html
from typing import List

import hext

from ..entry import BaseRawEntry
from .base import BaseParser


class RawEntry(BaseRawEntry):
    """Raw feed entry."""

    @property
    def categories(self) -> List[str]:
        return [html.unescape(c) for c in super().categories]


class Parser(BaseParser):
    """Parse entries using `hext`."""

    @property
    def _raw_entries(self) -> List[RawEntry]:
        """Return a list of raw entries."""
        return [RawEntry(e) for e in hext.Rule(self.parser_config).extract(hext.Html(self.content.decode()))]
