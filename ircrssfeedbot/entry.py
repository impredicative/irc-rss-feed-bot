"""Feed entry."""
import dataclasses
import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Union

from more_itertools import collapse

log = logging.getLogger(__name__)
SearchPatterns = Dict[str, Union[List[str], Dict[str, List[str]]]]


@dataclasses.dataclass(unsafe_hash=True)
class FeedEntry:
    """Feed entry."""

    title: str = dataclasses.field(compare=False)
    long_url: str = dataclasses.field(compare=True)
    categories: List[str] = dataclasses.field(compare=False, repr=False)
    data: Dict[str, Any] = dataclasses.field(compare=False, repr=False)

    @staticmethod
    def _applicable_patterns(patterns: SearchPatterns, key: str) -> List[str]:
        patterns = patterns.get(key, [])
        if isinstance(patterns, dict):
            patterns = patterns.values()  # type: ignore
        patterns = list(filter(None.__ne__, collapse(patterns)))
        # Note: `None.__ne__` helps remove None values. Refer to https://stackoverflow.com/a/16097112/
        return patterns

    def listing(self, search_patterns: SearchPatterns) -> Optional[Tuple[str, re.Match]]:
        """Return the matching key name and regular expression match against the given search patterns."""
        # Check title and long URL
        for search_key, val in {"title": self.title, "url": self.long_url}.items():
            for pattern in self._applicable_patterns(search_patterns, search_key):
                if match := re.search(pattern, val):
                    log.debug("%s matches %s pattern %s.", self, search_key, repr(pattern))
                    return search_key, match  # type: ignore

        # Check categories
        for pattern in self._applicable_patterns(search_patterns, "category"):
            for category in self.categories:  # This loop is only for categories.
                if match := re.search(pattern, category):
                    log.debug("%s having category %s matches category pattern %s.", self, repr(category), repr(pattern))
                    return "category", match  # type: ignore

        return None

    @property
    def post_url(self) -> str:
        """Return the URL to post."""
        return self.long_url


@dataclasses.dataclass
class ShortenedFeedEntry(FeedEntry):
    """Shortened feed entry."""

    short_url: str = dataclasses.field(compare=False)

    @property
    def post_url(self) -> str:
        """Return the URL to post."""
        return self.short_url
