"""Feed."""
import dataclasses
import html
import json
import logging
import re
from functools import lru_cache
from typing import Callable, Dict, List, Optional, Pattern

import bitlyshortener
import feedparser
import hext
import jmespath
from descriptors import cachedproperty

from . import config
from .db import Database
from .entry import FeedEntry
from .gnews import decode_google_news_url
from .url import URLReader
from .util.hext import html_to_text
from .util.list import ensure_list
from .util.lxml import sanitize_xml
from .util.set import leaves
from .util.textwrap import shorten_to_bytes_width

log = logging.getLogger(__name__)


@lru_cache(maxsize=None)  # maxsize is bounded by a multiple of the number of feeds.
def _patterns(channel: str, feed: str, list_type: str) -> Dict[str, List[Pattern]]:  # Cache-lookup friendly signature.
    """Return a mapping of keys to a list of unique compiled regular expression patterns for the given args.

    The mapping keys are `title`, `url`, and `category`.
    """
    list_config = config.INSTANCE["feeds"][channel][feed].get(list_type) or {}
    patterns = {key: [re.compile(pat) for pat in leaves(list_config.get(key))] for key in ("title", "url", "category")}
    log.debug("Caching regex patterns for %s of feed %s of %s.", list_type, feed, channel)
    return patterns


@dataclasses.dataclass
class Feed:
    """Feed with entries."""

    channel: str
    name: str
    db: Database = dataclasses.field(repr=False)
    url_shortener: bitlyshortener.Shortener = dataclasses.field(repr=False)

    def __post_init__(self):
        log.debug("Initializing instance of %s.", self)
        self.config: Dict = {**config.INSTANCE["defaults"], **config.INSTANCE["feeds"][self.channel][self.name]}
        self.url = self.config["url"]
        self.min_channel_idle_time = (
            config.MIN_CHANNEL_IDLE_TIME_DEFAULT
            if (self.config.get("period", config.PERIOD_HOURS_DEFAULT) > config.PERIOD_HOURS_MIN)
            else 0
        )
        self.blacklist = _patterns(self.channel, self.name, "blacklist")
        self.whitelist = _patterns(self.channel, self.name, "whitelist")
        self.entries = self._entries()  # Entries are effectively cached here at this point in time.
        log.debug("Initialized instance of %s with %s entries.", self, len(self.entries))

    def __str__(self):
        return f"feed {self.name} of {self.channel}"

    def _dedupe_entries(self, entries: List[FeedEntry], *, after_what: Optional[str] = None) -> List[FeedEntry]:
        """# Remove duplicate entries while preserving order."""
        # e.g. for https://projecteuclid.org/feeds/euclid.ba_rss.xml
        action = f"After {after_what}, removing" if after_what else "Removing"
        log.debug("%s duplicate entry URLs for %s.", action, self)
        entries_deduped = list(dict.fromkeys(entries))
        num_removed = len(entries) - len(entries_deduped)
        logger = log.info if num_removed > 0 else log.debug
        action = f"After {after_what}, removed" if after_what else "Removed"
        logger(
            "%s %s duplicate entry URLs out of %s, leaving %s, for %s.",
            action,
            num_removed,
            len(entries),
            len(entries_deduped),
            self,
        )
        return entries_deduped

    def _entries(self) -> List[FeedEntry]:  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
        feed_config = self.config

        # Retrieve URL content
        content = URLReader.url_content(self.url)

        # Parse entries
        log.debug("Parsing entries for %s.", self)
        if extract_config := feed_config.get("jmes"):
            parser = "jmes"
            raw_entries = jmespath.search(extract_config, json.loads(content)) or []  # search can return None
            entries = [
                FeedEntry(
                    title=e["title"].strip(),
                    long_url=e["link"].strip(),
                    categories=[c.strip() for c in ensure_list(e.get("category", []))],
                    data=e,
                    feed=self,
                )
                for e in raw_entries
            ]
        elif extract_config := feed_config.get("hext"):
            parser = "hext"
            raw_entries = hext.Rule(extract_config).extract(hext.Html(content.decode()))
            entries = [
                FeedEntry(
                    title=html.unescape(e["title"].strip()),
                    long_url=e["link"].strip(),
                    categories=[html.unescape(c.strip()) for c in ensure_list(e.get("category", []))],
                    data=e,
                    feed=self,
                )
                for e in raw_entries
            ]
        else:
            parser = "default"
            content = sanitize_xml(content)  # e.g. for unescaped "&" char in https://deepmind.com/blog/feed/basic/
            raw_entries = feedparser.parse(content.lstrip())["entries"]
            entries = [
                FeedEntry(
                    title=e["title"],
                    long_url=e.get("link") or e["links"][0]["href"],  # e.g. for https://feeds.buzzsprout.com/188368.rss
                    categories=[t["term"] for t in getattr(e, "tags", [])],
                    data=dict(e),
                    feed=self,
                )
                for e in raw_entries
            ]
        log_msg = f"Parsed {len(entries)} entries for {self} using the {parser} parser."

        # Raise alert if no entries
        if entries:
            log.debug(log_msg)
        else:
            if feed_config.get("alerts", {}).get("empty", True):
                log_msg += (
                    " Either check the feed configuration, or wait for its next read, "
                    "or set `alerts/empty` to `false` for it."
                )
                config.runtime.alert(log_msg)
            else:
                log.warning(log_msg)
            return entries

        # Decode Google News URLs
        if self.url.startswith("https://news.google.com/rss/") and (parser == "default"):
            log.debug("Conditionally decoding Google News URLs for %s.", self)
            for entry in entries:
                entry.long_url = decode_google_news_url(entry.long_url)
            log.debug("Conditionally decoded Google News URLs for %s.", self)

        # Remove blacklisted entries
        if feed_config.get("blacklist", {}):
            log.debug("Filtering %s entries using blacklist for %s.", len(entries), self)
            entries = [entry for entry in entries if not entry.blacklisted_pattern]
            log.debug("Filtered to %s entries using blacklist for %s.", len(entries), self)
            if not entries:
                return entries

        # Keep only whitelisted entries
        if feed_config.get("whitelist", {}):
            log.debug("Filtering %s entries using whitelist for %s.", len(entries), self)
            whitelisted_entries: List[FeedEntry] = []
            for entry in entries:
                if key_pattern_tuple := entry.whitelisted_pattern:
                    key, pattern = key_pattern_tuple
                    if key == "title":
                        entry.matching_title_search_pattern = pattern
                    whitelisted_entries.append(entry)
            entries = whitelisted_entries
            log.debug("Filtered to %s entries using whitelist for %s.", len(entries), self)
            if not entries:
                return entries

        # Enforce HTTPS URLs
        if feed_config.get("https"):
            log.debug("Enforcing HTTPS for URLs in %s.", self)
            for entry in entries:
                if entry.long_url.startswith("http://"):
                    entry.long_url = entry.long_url.replace("http://", "https://", 1)
            log.debug("Enforced HTTPS for URLs in %s.", self)

        # Substitute entries
        if sub := feed_config.get("sub"):
            log.debug("Substituting entries for %s.", self)
            re_sub: Callable[[Dict[str, str], str], str] = lambda r, v: re.sub(r["pattern"], r["repl"], v)
            if title_sub := sub.get("title"):
                for entry in entries:
                    entry.title = re_sub(title_sub, entry.title)
            if url_sub := sub.get("url"):
                for entry in entries:
                    entry.long_url = re_sub(url_sub, entry.long_url)
            log.debug("Substituted entries for %s.", self)

        # Format entries
        if format_config := feed_config.get("format"):
            log.debug("Formatting entries for %s.", self)
            format_re = format_config.get("re", {})
            format_str = format_config["str"]
            for entry in entries:
                # Collect:
                re_params = {"title": entry.title, "url": entry.long_url, "categories": entry.categories}
                params = {**entry.data, **re_params}
                for re_key, re_val in format_re.items():
                    if match := re.search(re_val, params[re_key]):
                        params.update(match.groupdict())
                # Format:
                entry.title = format_str.get("title", "{title}").format_map(params)
                entry.long_url = format_str.get("url", "{url}").format_map(params)
            log.debug("Formatted entries for %s.", self)

        # Escape spaces in URLs
        log.debug("Escaping spaces in URLs for %s.", self)
        for entry in entries:
            # e.g. for https://covid-api.com/api/reports?iso=USA&region_province=New York&date=2020-03-15
            entry.long_url = entry.long_url.strip().replace(" ", "%20")
        log.debug("Escaped spaces in URLs for %s.", self)

        # Strip HTML tags from titles
        log.debug("Stripping HTML tags from titles for %s.", self)
        for entry in entries:
            # e.g. for http://rss.sciencedirect.com/publication/science/08999007  (Elsevier Nutrition journal)
            entry.title = html_to_text(entry.title)
        log.debug("Stripped HTML tags from titles for %s.", self)

        # Strip unicode quotes around titles
        quote_begin, quote_end = "“”"
        # e.g. for https://www.sciencedirect.com/science/article/abs/pii/S0899900718307883
        log.debug("Stripping unicode quotes around titles for %s.", self)
        for entry in entries:
            title = entry.title
            if (len(title) > 2) and (title[0] == quote_begin) and (title[-1] == quote_end):
                title = title[1:-1]
                if (quote_begin not in title) and (quote_end not in title):
                    entry.title = title
        log.debug("Stripped unicode quotes around titles for %s.", self)

        # Replace all-caps titles
        log.debug("Capitalizing all-caps titles for %s.", self)
        for entry in entries:
            if entry.title.isupper():  # e.g. for https://www.biorxiv.org/content/10.1101/667436v1
                entry.title = entry.title.capitalize()
        log.debug("Capitalized all-caps titles for %s.", self)

        # Shorten titles
        title_max_bytes = config.TITLE_MAX_BYTES
        log.debug("Shortening titles to %s bytes for %s.", title_max_bytes, self)
        for entry in entries:
            entry.title = shorten_to_bytes_width(entry.title, title_max_bytes)
        log.debug("Shortened titles to %s bytes for %s.", title_max_bytes, self)

        # Deduplicate entries
        entries = self._dedupe_entries(entries)

        return entries

    @cachedproperty
    def postable_entries(self) -> List[FeedEntry]:
        """Return the subset of postable entries as a list."""
        log.debug("Retrieving postable entries for %s.", self)
        entries = self.unposted_entries

        # Filter entries if new feed
        if self.db.is_new_feed(self.channel, self.name):
            log.debug("Filtering new feed %s having %s postable entries.", self, len(entries))
            max_posts = config.NEW_FEED_POSTS_MAX[self.config["new"]]
            entries = entries[:max_posts]
            log.debug(
                "Filtered new feed %s to %s postable entries given a max limit of %s entries.",
                self,
                len(entries),
                max_posts,
            )

        # Shorten URLs
        if entries and self.config["shorten"]:
            log.debug("Shortening %s postable long URLs for %s.", len(entries), self)
            long_urls = [entry.long_url for entry in entries]
            short_urls = self.url_shortener.shorten_urls(long_urls)
            for index, entry in enumerate(entries):
                entry.short_url = short_urls[index]
            log.debug("Shortened %s postable long URLs for %s.", len(entries), self)

        log.debug("Returning %s postable entries for %s.", len(entries), self)

        return entries

    @cachedproperty
    def unposted_entries(self) -> List[FeedEntry]:
        """Return the subset of unposted entries as a list."""
        log.debug("Retrieving unposted entries for %s.", self)
        entries = self.entries
        long_urls = [entry.long_url for entry in entries]
        dedup_strategy = self.config.get("dedup") or config.DEDUP_STRATEGY_DEFAULT
        if dedup_strategy == "channel":
            long_urls = self.db.select_unposted_for_channel(self.channel, self.name, long_urls)
        else:
            assert dedup_strategy == "feed"
            long_urls = self.db.select_unposted_for_channel_feed(self.channel, self.name, long_urls)
        long_urls = set(long_urls)
        entries = [entry for entry in entries if entry.long_url in long_urls]
        log.debug("Returning %s unposted entries for %s.", len(entries), self)
        return entries
