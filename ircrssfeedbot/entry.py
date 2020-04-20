"""Feed entry."""
import dataclasses
import logging
from typing import Any, Dict, List, Optional, Pattern, Tuple

from . import config
from .util.ircmessage import style
from .util.list import ensure_list
from .util.textwrap import shorten_to_bytes_width

log = logging.getLogger(__name__)


class BaseRawEntry(dict):
    """Base class of raw feed entry.

    This is used for creating a `FeedEntry`.
    """

    @property
    def title(self) -> str:
        """Return the entry title."""
        return self["title"].strip()

    @property
    def link(self) -> str:
        """Return the entry link (URL)."""
        return self["link"].strip()

    @property
    def summary(self) -> str:
        """Return the entry summary (description)."""
        return (self.get("summary") or "").strip()

    @property
    def categories(self) -> List[str]:
        """Return a list of entry categories."""
        return [c.strip() for c in ensure_list(self.get("category"))]


@dataclasses.dataclass(unsafe_hash=True)
class FeedEntry:
    """Feed entry."""

    title: str = dataclasses.field(compare=False)
    long_url: str = dataclasses.field(compare=True)
    summary: str = dataclasses.field(compare=False)
    categories: List[str] = dataclasses.field(compare=False, repr=True)
    data: Dict[str, Any] = dataclasses.field(compare=False, repr=False)
    feed: Any = dataclasses.field(compare=False, repr=False)

    def __post_init__(self):
        self.short_url: Optional[str] = None
        self.matching_title_search_pattern: Optional[Pattern] = None

    def _matching_pattern(self, patterns: Dict[str, List[Pattern]]) -> Optional[Tuple[str, Pattern]]:
        """Return the matching key name and regular expression pattern, if any."""
        # Check title and long URL
        for search_key, val in {"title": self.title, "url": self.long_url}.items():
            for pattern in patterns[search_key]:
                if pattern.search(val):
                    log.log(5, "%s matches %s pattern %s.", self, search_key, repr(pattern.pattern))
                    return search_key, pattern

        # Check categories
        for pattern in patterns["category"]:
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
        return self._matching_pattern(self.feed.blacklist)

    @property
    def whitelisted_pattern(self) -> Optional[Tuple[str, Pattern]]:
        """Return the matching key name and whitelisted regular expression pattern, if any."""
        return self._matching_pattern(self.feed.whitelist)

    @property
    def message(self) -> str:  # pylint: disable=too-many-locals
        """Return the message to post."""
        # Obtain feed config
        feed_config = self.feed.config
        explain = (feed_config.get("whitelist") or {}).get("explain")
        msg_config = feed_config.get("message") or {}
        style_config = feed_config.get("style") or {}
        name_style_config = style_config.get("name", {})

        # Define post params
        format_map = dict(
            identity=config.runtime.identity,
            channel=self.feed.channel,
            feed=style(self.feed.name, **name_style_config),
            url=self.short_url or self.long_url,
        )

        # Define post caption
        format_map["caption"] = ""
        if msg_config.get("title", True) and (title := self.title):
            if explain and (pattern := self.matching_title_search_pattern):
                if match := pattern.search(title):  # Not always guaranteed to be true due to sub, format, etc.
                    span0, span1 = match.span()
                    title_mid = title[span0:span1]
                    title_mid = style(title_mid, italics=True) if style_config else f"*{title_mid}*"
                    title = title[:span0] + title_mid + title[span1:]
            format_map["caption"] += title
        if msg_config.get("summary") and self.summary:
            if format_map["caption"]:
                if style_config:
                    format_map["caption"] = style(format_map["caption"], bold=True)
                format_map["caption"] += ": "
            format_map["caption"] += self.summary

        # Define message format
        msg_format = "[{feed}]"
        if format_map["caption"]:
            msg_format += " {caption} →"
        msg_format += " {url}"
        privmsg_format = f":{{identity}} PRIVMSG {{channel}} :{msg_format}"

        # Shorten caption
        base_bytes_use = len(privmsg_format.format_map({**format_map, "caption": ""}).encode())
        caption_bytes_width = max(0, config.QUOTE_LEN_MAX - base_bytes_use)
        format_map["caption"] = shorten_to_bytes_width(format_map["caption"], caption_bytes_width)

        msg = msg_format.format_map(format_map)
        return msg
