"""Feed entry."""
import dataclasses
import functools
import logging
import re
from typing import Any, Dict, List, Match, Optional, Pattern, Tuple, cast

from . import config
from .util.ircmessage import style
from .util.set import leaves
from .util.textwrap import shorten_to_bytes_width

log = logging.getLogger(__name__)


@functools.lru_cache(maxsize=None)  # maxsize is bounded by a multiple of the number of feeds.
def _patterns(channel: str, feed: str, list_type: str, key: str) -> List[Pattern]:
    """Return a list of unique compiled regular expression patterns for the given args."""
    feed_config = config.INSTANCE["feeds"][channel][feed]
    list_config = feed_config.get(list_type) or {}
    key_config = list_config.get(key, [])
    patterns = leaves(key_config)
    patterns = [re.compile(pattern) for pattern in patterns]
    log.debug(
        "Caching %s unique regex patterns for %s %s of feed %s of %s", len(patterns), key, list_type, feed, channel,
    )
    return patterns


@dataclasses.dataclass(unsafe_hash=True)
class FeedEntry:
    """Feed entry."""

    title: str = dataclasses.field(compare=False)
    long_url: str = dataclasses.field(compare=True)
    categories: List[str] = dataclasses.field(compare=False, repr=True)
    data: Dict[str, Any] = dataclasses.field(compare=False, repr=False)
    feed: Any = dataclasses.field(compare=False, repr=False)

    def __post_init__(self):
        self.short_url: Optional[str] = None
        self.matching_title_search_pattern: Optional[Pattern] = None

    def _matching_pattern(self, list_type: str) -> Optional[Tuple[str, Pattern]]:
        """Return the matching key name and regular expression pattern, if any."""
        channel = self.feed.channel
        feed = self.feed.name

        # Check title and long URL
        for search_key, val in {"title": self.title, "url": self.long_url}.items():
            for pattern in _patterns(channel, feed, list_type, search_key):
                if pattern.search(val):
                    log.log(5, "%s matches %s pattern %s.", self, search_key, repr(pattern.pattern))
                    return search_key, pattern

        # Check categories
        for pattern in _patterns(channel, feed, list_type, "category"):
            for category in self.categories:  # This loop is only for categories.
                if pattern.search(category):
                    log.log(
                        5,
                        "%s having category %s matches category pattern %s.",
                        self,
                        repr(category),
                        repr(pattern.pattern),
                    )
                    return "category", pattern

        return None

    @property
    def blacklisted_pattern(self) -> Optional[Tuple[str, Pattern]]:
        """Return the matching key name and blacklisted regular expression pattern, if any."""
        return self._matching_pattern("blacklist")

    @property
    def whitelisted_pattern(self) -> Optional[Tuple[str, Pattern]]:
        """Return the matching key name and whitelisted regular expression pattern, if any."""
        return self._matching_pattern("whitelist")

    @property
    def message(self) -> str:  # pylint: disable=too-many-locals
        """Return the message to post."""
        # Define feed config
        feed_name = self.feed.name
        feed_config = self.feed.config
        explain = (feed_config.get("whitelist") or {}).get("explain")  # Note: get("whitelist") can be None.
        feed_style = feed_config.get("style") or {}
        feed_name_style = feed_style.get("name", {})

        # Define post title
        title = self.title
        if explain and (pattern := self.matching_title_search_pattern):
            pattern = cast(Pattern, pattern)
            if match := pattern.search(self.title):  # Not always guaranteed to be true due to sub, format, etc.
                match = cast(Match, match)
                span0, span1 = match.span()
                title_mid = title[span0:span1]
                title_mid = style(title_mid, italics=True) if feed_style else f"*{title_mid}*"
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
