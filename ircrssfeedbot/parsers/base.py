"""Base class with helper attributes and methods for parsers."""
import abc
import dataclasses
from typing import TYPE_CHECKING, Dict, List, Optional, Union

from ..entry import FeedEntry

if TYPE_CHECKING:
    from ..feed import FeedReader  # pylint: disable=unused-import


@dataclasses.dataclass  # type: ignore
class BaseParser(abc.ABC):
    """Base class with helper attributes and methods for parsers."""

    selector: Optional[str]  # Is None for feedparser.
    follower: Optional[str]
    content: bytes
    feed_reader: "FeedReader"

    @property
    @abc.abstractmethod
    def _raw_entries(self) -> List:
        """Return a list of parsed raw entries, each of which is instance of `BaseRawEntry` or of its subclass."""

    @property
    def _raw_urls(self) -> List[Union[Dict[str, str], str]]:
        """Return a list of parsed raw URLs to scrape.

        Each raw URL in the list is either a string or a dictionary having the key `url` with the URL as its value.
        """
        return []

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
                feed_reader=self.feed_reader,
            )
            for e in self._raw_entries
        ]

    @property
    def urls(self) -> List[str]:
        """Return a list of unique URLs to follow."""
        urls = [(d if isinstance(d, str) else d["url"]) for d in self._raw_urls]
        return list(dict.fromkeys(urls))
