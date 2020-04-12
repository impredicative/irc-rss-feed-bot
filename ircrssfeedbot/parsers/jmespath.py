"""Parse entries using `jmespath`."""
import json
from typing import List

import jmespath

from ..entry import BaseRawEntry as RawEntry
from .base import BaseParser


class Parser(BaseParser):
    """Parse entries using `jmespath`."""

    @property
    def _raw_entries(self) -> List[RawEntry]:
        """Return a list of raw entries."""
        return [RawEntry(e) for e in (jmespath.search(self.parser_config, json.loads(self.content)) or [])]
