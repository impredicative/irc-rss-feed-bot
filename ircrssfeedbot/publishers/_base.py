"""Base publisher class with helper attributes and methods for publishers."""
import abc
import logging
import threading
import time
from typing import Any, Dict, List

import pandas as pd

from .. import config
from ..feed import FeedEntry

log = logging.getLogger(__name__)


class BasePublisher(abc.ABC):
    """Base publisher class with helper attributes and methods for publishers."""

    def __init__(self, name: str):
        self.name = name
        self.config = config.INSTANCE["publish"][self.name]
        self._publish_lock = threading.Lock()  # May not be necessary, but used anyway for safety.
        log.info(f"Initalizing {self.name} publisher.")

    @staticmethod
    def entries_df(entries: List[FeedEntry]) -> pd.DataFrame:
        """Return a dataframe corresponding to the given entries."""
        entries = ({"channel": e.feed_reader.channel, "feed": e.feed_reader.name, "title": e.title, "long_url": e.long_url, "short_url": e.short_url} for e in entries)
        return pd.DataFrame(entries, dtype="string")

    @abc.abstractmethod
    def _publish(self, channel: str, df_entries: pd.DataFrame) -> Dict[str, Any]:
        """Return the result after publishing the given entries for the given channel."""

    def publish(self, channel: str, entries: List[FeedEntry]) -> Dict[str, Any]:  # type: ignore
        """Return the result after resiliently publishing the given entries for the given channel."""
        assert entries
        num_entries = len(entries)
        df_entries = self.entries_df(entries)
        max_attempts = config.PUBLISH_ATTEMPTS_MAX
        with self._publish_lock:
            for num_attempt in range(1, max_attempts + 1):
                desc = f"{num_entries} entries of {channel} to {self.name} in attempt {num_attempt} of {max_attempts}"
                try:
                    return self._publish(channel, df_entries)
                except Exception as exc:  # pylint: disable=broad-except
                    log.info(f"Error publishing {desc}: {exc}")
                    if num_attempt == max_attempts:
                        # TODO: Consider saving unpublished entries in memory until a future retry is successful.
                        raise exc from None
                    time.sleep(2 ** num_attempt)
