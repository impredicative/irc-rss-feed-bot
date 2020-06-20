"""Base publisher class with helper attributes and methods for publishers."""
import abc
import itertools
import logging
import threading
import time
from typing import Any, Dict, List, Union

import pandas as pd

from .. import config
from ..feed import FeedEntry
from ..util.dict import dict_str

log = logging.getLogger(__name__)


class BasePublisher(abc.ABC):
    """Base publisher class with helper attributes and methods for publishers."""

    def __init__(self, name: str):
        self.name = name
        self.config = config.INSTANCE["publish"][self.name]
        self._publish_lock = threading.Lock()  # May not be necessary, but used anyway for safety.
        self._publish_queue: Dict[str, pd.DataFrame] = {}  # Only for retries of failed publishes.
        log.info(f"Initalizing {self.name} publisher.")

    def __str__(self) -> str:
        return f"{self.name} publisher"

    def drain(self, blocking: bool = True) -> bool:
        """Return a success indicator after draining the queue.

        This method is expected to be called only after external calls to `publish` have ended and stopped.
        """
        if not blocking:
            return not self._publish_queue
        while self._publish_queue:
            channel = next(iter(self._publish_queue))
            log.info(f"Draining channel {channel} of {self}.")
            result = self.publish(channel, entries=[], max_attempts=float("inf"))
            log.info(f"Drained channel {channel} of {self} with result: {dict_str(result)}")
        return True

    @staticmethod
    def entries_df(entries: List[FeedEntry]) -> pd.DataFrame:
        """Return a dataframe corresponding to the given entries."""
        if entries:
            entries_gen = ({"channel": e.feed_reader.channel, "feed": e.feed_reader.name, "title": e.title, "long_url": e.long_url, "short_url": e.short_url} for e in entries)
            return pd.DataFrame(entries_gen, dtype="string")
        return pd.DataFrame([{}], columns=["channel", "feed", "title", "long_url", "short_url"], dtype="string").drop(labels=0)  # Workaround for https://git.io/Jfbjd

    @abc.abstractmethod
    def _publish(self, channel: str, df_entries: pd.DataFrame) -> Dict[str, Any]:
        """Return the result after publishing the given entries for the given channel."""

    def publish(self, channel: str, entries: List[FeedEntry], max_attempts: Union[int, float] = config.PUBLISH_ATTEMPTS_MAX) -> Dict[str, Any]:  # type: ignore
        """Return the result after publishing the given entries along with any previously queued entries for the given channel."""
        df_entries = self.entries_df(entries)
        with self._publish_lock:
            df_entries = pd.concat((self._publish_queue.pop(channel, None), df_entries))  # Requires channel-level or broader lock.
            assert not df_entries.empty
            num_entries = len(entries)
            for num_attempt in itertools.count(start=1):
                desc_minimal = f"{num_entries:,} entries of {channel} to {self.name}"
                desc = f"{desc_minimal} in attempt {num_attempt} of {max_attempts}"
                try:
                    return {**self._publish(channel, df_entries), **{"num_entries": num_entries}}
                except Exception as exc:  # pylint: disable=broad-except
                    if num_attempt == max_attempts:
                        self._publish_queue[channel] = df_entries
                        config.runtime.alert(f"Failed to publish {desc_minimal}. The entries are queued. The error was: {exc}")
                        raise exc from None
                    assert num_attempt < max_attempts
                    sleep_time = min(config.PUBLISH_RETRY_SLEEP_MAX, 2 ** num_attempt)
                    log.warning(f"Failed to publish {desc}. A reattempt will be made in {sleep_time}s. The error was: {exc}")
                    time.sleep(sleep_time)
