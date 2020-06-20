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
        self._publish_queue: Dict[str, pd.DataFrame] = {}  # Only for retries of failed publishes.
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
        df_entries = self.entries_df(entries)
        max_attempts = config.PUBLISH_ATTEMPTS_MAX
        with self._publish_lock:
            df_entries = pd.concat((self._publish_queue.pop(channel, None), df_entries))  # Requires channel-level or broader lock.
            num_entries = len(entries)
            for num_attempt in range(1, max_attempts + 1):
                desc_minimal = f"{num_entries:,} entries of {channel} to {self.name}"
                desc = f"{desc_minimal} in attempt {num_attempt} of {max_attempts}"
                try:
                    return {**self._publish(channel, df_entries), **{"num_entries": num_entries}}
                except Exception as exc:  # pylint: disable=broad-except
                    if num_attempt < max_attempts:
                        log.info(f"Error publishing {desc}: {exc}")
                    else:
                        assert num_attempt == max_attempts
                        self._publish_queue[channel] = df_entries
                        config.runtime.alert(f"Failed to publish {desc_minimal}. The entries are queued. The error was: {exc}")
                        raise exc from None
                    time.sleep(2 ** num_attempt)
