"""Feed entry."""
import dataclasses
import logging
import re
from typing import Any, Dict, List, Optional, Pattern, Tuple

from . import config
from .style import style
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
    feed_reader: Any = dataclasses.field(compare=False, repr=False)

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
        return self._matching_pattern(self.feed_reader.blacklist)

    @property
    def whitelisted_pattern(self) -> Optional[Tuple[str, Pattern]]:
        """Return the matching key name and whitelisted regular expression pattern, if any."""
        return self._matching_pattern(self.feed_reader.whitelist)

    @property
    def message(self) -> str:  # pylint: disable=too-many-locals
        """Return the message to post."""
        # Obtain feed config
        feed_config = self.feed_reader.config
        explain = (feed_config.get("whitelist") or {}).get("explain")
        msg_config = feed_config.get("message") or {}
        include_summary = msg_config.get("summary") and self.summary
        style_config = feed_config.get("style") or {}

        def _style_name(text: str) -> str:
            return style(text, styler="irc", **style_config.get("name", {}))

        def _style_title(text: str, **kwargs: Any) -> str:
            return style(text, styler="irc" if style_config else "unicode", **kwargs)

        # Define post params
        format_map = dict(
            identity=config.runtime.identity,
            channel=self.feed_reader.channel,
            feed=_style_name(self.feed_reader.name),
            url=self.short_url or self.long_url,
        )

        # Define post caption
        format_map["caption"] = ""
        if msg_config.get("title", True) and (title := self.title):
            if (
                explain
                and (pattern := self.matching_title_search_pattern)
                and (match := pattern.search(title))  # pylint: disable=used-before-assignment
            ):
                # Note: A match is not always guaranteed to exist due to sub, format, etc.
                span0, span1 = match.span()
                title_pre, title_mid, title_post = title[:span0], title[span0:span1], title[span1:]
                if include_summary:
                    title_pre = _style_title(title_pre, bold=True)
                    title_mid = _style_title(title_mid, bold=True, italics=True)
                    title_post = _style_title(title_post, bold=True)
                    title = title_pre + title_mid + title_post
                else:
                    title = title_pre + _style_title(title_mid, italics=True) + title_post
            elif include_summary:
                title = _style_title(title, bold=True)
            format_map["caption"] += title
        if include_summary:
            if format_map["caption"]:
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

    def topic(self, topic: str) -> str:
        """Return the updated or unchanged channel topic as updated by the entry."""
        if not (topic_config := self.feed_reader.config.get("topic")):  # pylint: disable=superfluous-parens
            return topic
        topic_parts = {k: v for k, _, v in (p.partition(": ") for p in topic.split(" | "))}
        for key, pattern in topic_config.items():
            if re.search(pattern, self.title):
                topic_parts[key] = self.short_url or self.feed_reader.url_shortener.shorten_urls([self.long_url])[0]
        topic = " | ".join((f"{k}: {v}" if v else k) for k, v in topic_parts.items())
        return topic
