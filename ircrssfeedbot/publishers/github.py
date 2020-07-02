"""Publish entries to GitHub."""
import datetime
import io
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

import diskcache
import github
import pandas as pd

from .. import config
from ._base import BasePublisher

log = logging.getLogger(__name__)


class Publication:

    CURRENT_VERSION = 1

    def __init__(self, channel: str, df_entries: pd.DataFrame, sha: Optional[str]):
        self.dt_utc = datetime.datetime.utcnow()
        self.version = self.CURRENT_VERSION

        self.channel = channel
        self.df_entries = df_entries
        self.sha = sha

    @property
    def summary(self) -> str:
        feed_counts = ", ".join(f"{value}={count}" for value, count in self.df_entries["feed"].value_counts().iteritems())
        return f"{self.channel}={len(self.df_entries)}: {feed_counts}"

    @property
    def entries_csv(self) -> str:
        assert not self.df_entries.empty
        entries_csv = self.df_entries.to_csv(index=False)
        assert self.df_entries.equals(self.from_entries_csv(channel=self.channel, entries_csv=entries_csv))
        return entries_csv

    @classmethod
    def from_entries_csv(cls, channel: str, entries_csv: str) -> 'Publication':
        return cls(channel=channel, df_entries=pd.read_csv(io.StringIO(entries_csv), parse_dates=["dt_utc"]))

    @property
    def is_version_current(self) -> bool:
        """Return whether the instance version is the current version.

        This check can be relevant after restoring a pickled instance.
        """
        return self.version == self.CURRENT_VERSION

    @property
    def path(self) -> str:
        return f"{self.channel}/{self.dt_utc.strftime('%Y/%m%d/%H')}.csv"  # Ref: https://strftime.org/


class Publisher(BasePublisher):
    """Publish a list of previously unpublished entries as a new file to GitHub."""

    def __init__(self):
        super().__init__(name=Path(__file__).stem)
        self._github = github.Github(os.environ["GITHUB_TOKEN"].strip())
        self._repo = self._github.get_repo(self.config)
        self._cache = diskcache.Cache(directory=config.DISKCACHE_PATH / f"{self.name.title()}{self.__class__.__name__}", timeout=2, size_limit=config.DISKCACHE_SIZE_LIMIT)

    def _publish(self, channel: str, df_entries: pd.DataFrame) -> Dict[str, Any]:
        assert not df_entries.empty
        pub = Publication(channel=channel, df_entries=df_entries)
        response = None

        # Try updating file, appending to previously disk-cached content
        if (cached_pub := self._cache.get(channel)) and cached_pub.is_version_current and pub.path == cached_pub.path:
            cached_pub.df_entries = pd.concat((cached_pub.df_entries, pub.df_entries))  # pub is intentionally not updated here instead.
            assert not cached_pub.df_entries.duplicated().any()
            try:
                response = self._repo.update_file(path=cached_pub.path, message=cached_pub.summary, content=cached_pub.entries_csv, sha=cached_pub.sha)
            except github.GithubException:
                log.warning("")
            else:
                pub = cached_pub

        # Try creating file
        if not response:
            try:
                response = self._repo.create_file(path=pub.path, message=pub.summary, content=pub.entries_csv)
            except github.GithubException:
                log.debug("")

        # Try updating file, appending to previously published content
        if not response:
            response = self._repo.get_contents(path=pub.path)
            stored_pub = Publication.from_entries_csv(channel=channel, entries_csv=response.decoded_content.decode())
            pub.df_entries = pd.concat((stored_pub, pub.df_entries))
            assert not pub.df_entries.duplicated().any()
            response = self._repo.update_file(path=pub.path, message=pub.summary, content=pub.entries_csv, sha=response.sha)

        # Update disk-cache
        pub.sha = response["content"].sha
        self._cache[channel] = pub

        return {
            "path": pub.path,
            # "content_len": len(content),
            "rate_remaining": self._github.rate_limiting[0],
            # "rate_limit": self._github.rate_limiting[1],  # Always 5000.
            "rate_reset": datetime.timedelta(seconds=round(self._github.rate_limiting_resettime - time.time())),
        }
