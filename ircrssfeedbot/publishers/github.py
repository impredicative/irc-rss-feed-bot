"""Publish entries to GitHub."""
import datetime
import os
import time
from pathlib import Path
from typing import Any, Dict

import github
import pandas as pd

from ..util.str import readable_list
from ._base import BasePublisher


class Publisher(BasePublisher):
    """Publish a list of previously unpublished entries as a new file to GitHub."""

    def __init__(self):
        super().__init__(name=Path(__file__).stem)
        self._github = github.Github(os.environ["GITHUB_TOKEN"].strip())
        self._repo = self._github.get_repo(self.config)

    def _publish(self, channel: str, df_entries: pd.DataFrame) -> Dict[str, Any]:
        assert not df_entries.empty
        path = f"{channel}/{datetime.datetime.utcnow().strftime('%Y/%m%d/%H%M%S')}.csv"  # Ref: https://strftime.org/
        feed_counts = readable_list([f"{count} {value}" for value, count in df_entries["feed"].value_counts().iteritems()])
        content = df_entries.drop(columns="channel").to_csv(index=False)
        self._repo.create_file(path=path, message=f"Add {feed_counts} entries of {channel}", content=content)
        return {
            "path": path,
            # "content_len": len(content),
            "rate_remaining": self._github.rate_limiting[0],
            # "rate_limit": self._github.rate_limiting[1],  # Always 5000.
            "rate_reset": datetime.timedelta(seconds=round(self._github.rate_limiting_resettime - time.time())),
        }
