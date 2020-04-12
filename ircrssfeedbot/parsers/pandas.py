"""Parse entries using `pandas`."""
import io
import json
from typing import List

import numpy as np
import pandas as pd

from .. import util
from ..entry import BaseRawEntry as RawEntry
from .base import BaseParser


class Parser(BaseParser):
    """Parse entries using `pandas`."""

    @property
    def _raw_entries(self) -> List[RawEntry]:
        """Return a list of raw entries."""
        eval_globals = {"json": json, "np": np, "pd": pd, "util": util}
        eval_locals = {"file": io.BytesIO(self.content)}
        df = eval(f"pd.{self.parser_config}", eval_globals, eval_locals)  # pylint: disable=eval-used
        return [RawEntry(e) for _, e in df.iterrows()]
