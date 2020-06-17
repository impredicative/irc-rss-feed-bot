"""Parse entries using `pandas`."""
import dataclasses
import io
import json
from typing import Dict, List, cast

import numpy as np
import pandas as pd

from .. import util
from ..entry import RawFeedEntry
from ._base import BaseParser


@dataclasses.dataclass
class Parser(BaseParser):
    """Parse entries using `pandas`."""

    def _parse(self, selector: str) -> List[Dict[str, str]]:
        eval_globals = {"json": json, "np": np, "pd": pd, "util": util}
        eval_locals = {"file": io.BytesIO(self.content)}
        df = eval(f"pd.{selector}", eval_globals, eval_locals)  # pylint: disable=eval-used
        return [dict(e) for _, e in df.iterrows()]

    @property
    def _raw_urls(self) -> List[Dict[str, str]]:  # type: ignore
        """Return a list of parsed raw URLs to scrape."""
        return self._parse(self.follower) if self.follower else []

    @property
    def entries(self) -> List[RawFeedEntry]:
        """Return a list of raw entries."""
        return [RawFeedEntry(e) for e in self._parse(cast(str, self.selector))]
