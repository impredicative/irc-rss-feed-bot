"""Base class with helper attributes and methods for parsers."""
import abc
import dataclasses
from typing import Any, Dict, List

from .. import feed  # pylint: disable=unused-import
from ..entry import FeedEntry


@dataclasses.dataclass  # type: ignore
class BaseParser(abc.ABC):
    """Base class with helper attributes and methods for parsers."""

    parser_config: Dict[str, Any]
    content: bytes
    feed: "feed.Feed"

    @property
    @abc.abstractmethod
    def _raw_entries(self) -> List:
        """Return a list of raw entries."""

    @property
    def entries(self) -> List[FeedEntry]:
        """Return a list of feed entries."""
        return [
            FeedEntry(
                title=e.title,
                long_url=e.link,
                summary=e.summary,
                categories=e.categories,
                data=dict(e),
                feed=self.feed,
            )
            for e in self._raw_entries
        ]
