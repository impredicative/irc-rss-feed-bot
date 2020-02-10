"""Feed entry."""
import dataclasses
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union, cast

from . import config
from .util.ircmessage import style
from .util.set import leaves
from .util.textwrap import shorten_to_bytes_width

log = logging.getLogger(__name__)
SearchPatterns = Dict[str, Union[List[str], Dict[str, List[str]]]]


@dataclasses.dataclass(unsafe_hash=True)
class FeedEntry:
    """Feed entry."""

    title: str = dataclasses.field(compare=False)
    long_url: str = dataclasses.field(compare=True)
    categories: List[str] = dataclasses.field(compare=False, repr=False)
    data: Dict[str, Any] = dataclasses.field(compare=False, repr=False)
    feed: Any = dataclasses.field(compare=False, repr=False)
    short_url: Optional[str] = dataclasses.field(default=None, compare=False, repr=False)
    matching_title_search_pattern: Optional[str] = dataclasses.field(default=None, compare=False, repr=False)

    @staticmethod
    def _applicable_patterns(patterns: SearchPatterns, key: str) -> Set[str]:
        patterns = patterns.get(key, [])
        # if isinstance(patterns, dict): patterns = patterns.values()  # type: ignore
        # patterns = list(filter(None.__ne__, collapse(patterns)))
        return leaves(patterns)

    def listing(self, search_patterns: SearchPatterns) -> Optional[Tuple[str, str]]:
        """Return the matching key name and regular expression pattern against the given search patterns."""
        # Check title and long URL
        for search_key, val in {"title": self.title, "url": self.long_url}.items():
            for pattern in self._applicable_patterns(search_patterns, search_key):
                if re.search(pattern, val):
                    log.debug("%s matches %s pattern %s.", self, search_key, repr(pattern))
                    return search_key, pattern

        # Check categories
        for pattern in self._applicable_patterns(search_patterns, "category"):
            for category in self.categories:  # This loop is only for categories.
                if re.search(pattern, category):
                    log.debug("%s having category %s matches category pattern %s.", self, repr(category), repr(pattern))
                    return "category", pattern

        return None

    @property
    def message(self) -> str:  # pylint: disable=too-many-locals
        """Return the message to post."""
        # Define feed config
        feed_name = self.feed.name
        feed_config = self.feed.config
        explain = feed_config.get("whitelist", {}).get("explain")
        feed_name_style = feed_config.get("style", {}).get("name")

        # Define post title
        title = self.title
        if explain and (pattern := self.matching_title_search_pattern):
            pattern = cast(str, pattern)
            if match := re.search(pattern, self.title):  # Not always guaranteed to be true due to sub, format, etc.
                match = cast(re.Match, match)
                span0, span1 = match.span()
                title_mid = title[span0:span1]
                title_mid = style(title_mid, italics=True) if feed_name_style else f"*{title_mid}*"
                title = title[:span0] + title_mid + title[span1:]

        # Define other post params
        feed = style(feed_name, **feed_name_style)
        url = self.short_url or self.long_url

        # Shorten title
        base_bytes_use = len(
            config.PRIVMSG_FORMAT.format(
                identity=config.runtime.identity, channel=self.feed.channel, feed=feed, title="", url=url,
            ).encode()
        )
        title_bytes_width = max(0, config.QUOTE_LEN_MAX - base_bytes_use)
        title = shorten_to_bytes_width(title, title_bytes_width)

        msg = config.MESSAGE_FORMAT.format(feed=feed, title=title, url=url)
        return msg
