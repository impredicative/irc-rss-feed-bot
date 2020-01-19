"""Feed entry."""
import dataclasses
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger(__name__)


@dataclasses.dataclass(unsafe_hash=True)
class FeedEntry:
    """Feed entry."""

    title: str = dataclasses.field(compare=False)
    long_url: str = dataclasses.field(compare=True)
    categories: List[str] = dataclasses.field(compare=False, repr=False)
    data: Dict[str, Any] = dataclasses.field(compare=False, repr=False)

    @property
    def post_url(self) -> str:
        """Return the URL to post."""
        return self.long_url

    def listing(self, searchlist: Dict[str, List[str]]) -> Optional[Tuple[str, re.Match]]:
        """Return the matching key name and regular expression match against the given match lists mapping."""
        # Check title and long URL
        for searchlist_key, val in {"title": self.title, "url": self.long_url}.items():
            for pattern in searchlist.get(searchlist_key, []):
                match = re.search(pattern, val)
                if match:
                    log.debug("%s matches %s pattern %s.", self, searchlist_key, repr(pattern))
                    return searchlist_key, match
        # Check categories
        for pattern in searchlist.get("category", []):
            for category in self.categories:
                match = re.search(pattern, category)
                if match:
                    log.debug("%s having category %s matches category pattern %s.", self, repr(category), repr(pattern))
                    return "category", match
        return None


@dataclasses.dataclass
class ShortenedFeedEntry(FeedEntry):
    """Shortened feed entry."""

    short_url: str = dataclasses.field(compare=False)

    @property
    def post_url(self) -> str:
        """Return the URL to post."""
        return self.short_url
