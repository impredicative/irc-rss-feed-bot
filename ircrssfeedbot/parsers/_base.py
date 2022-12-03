"""Base parser class with helper attributes and methods for parsers."""
import abc
import dataclasses
from typing import Dict, List, Optional, Union


@dataclasses.dataclass
class BaseParser(abc.ABC):
    """Base parser class with helper attributes and methods for parsers."""

    selector: Optional[str]  # Is None for feedparser.
    follower: Optional[str]
    content: bytes

    @property
    def _raw_urls(self) -> List[Union[Dict[str, str], str]]:
        """Return a list of parsed raw URLs to scrape.

        Each raw URL in the list is either a string or a dictionary having the key `url` with the URL as its value.
        """
        return []

    @property
    @abc.abstractmethod
    def entries(self) -> List:
        """Return a list of parsed raw entries, each of which is instance of `BaseRawEntry` or of its subclass."""

    @property
    def urls(self) -> List[str]:
        """Return a list of unique URLs to follow."""
        urls = [(d if isinstance(d, str) else d["url"]) for d in self._raw_urls]
        return list(dict.fromkeys(urls))
