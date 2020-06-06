"""Feed reader and feed."""
import collections
import dataclasses
import logging
import multiprocessing
import re
import time
from functools import cached_property, lru_cache
from typing import Callable, Dict, List, Optional, Pattern, Tuple

import bitlyshortener
import miniirc
from orderedset import OrderedSet

from . import config
from .db import Database
from .entry import FeedEntry, RawFeedEntry
from .url import URLReader
from .util.bs4 import html_to_text
from .util.list import ensure_list
from .util.set import leaves
from .util.str import readable_list
from .util.textwrap import shorten_to_bytes_width
from .util.time import Throttle
from .util.timeit import Timer

log = logging.getLogger(__name__)


def _parse_entries(parser_name: str, selector: Optional[str], follower: Optional[str], url_content: bytes) -> Tuple[List[RawFeedEntry], List[str]]:
    from . import parsers  # pylint: disable=import-outside-toplevel

    Parser = getattr(parsers, parser_name).Parser  # pylint: disable=invalid-name
    parser = Parser(selector=selector, follower=follower, content=url_content)
    return parser.entries, parser.urls  # pylint: disable=no-member


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
class FeedReader:
    """Initialize a feed reader of a given channel and feed."""

    channel: str
    name: str
    irc: miniirc.IRC = dataclasses.field(repr=False)
    db: Database = dataclasses.field(repr=False)
    url_reader: URLReader = dataclasses.field(repr=False)
    url_shortener: bitlyshortener.Shortener = dataclasses.field(repr=False)

    def __post_init__(self):
        log.debug(f"Initializing {self}.")
        self.config: Dict = {**config.INSTANCE["defaults"], **config.INSTANCE["feeds"][self.channel][self.name]}
        self.urls = OrderedSet(ensure_list(self.config["url"]))
        self.min_channel_idle_time = config.MIN_CHANNEL_IDLE_TIME_DEFAULT if (self.config.get("period", config.PERIOD_HOURS_DEFAULT) > config.PERIOD_HOURS_MIN) else 0
        self.blacklist = _patterns(self.channel, self.name, "blacklist")
        self.whitelist = _patterns(self.channel, self.name, "whitelist")
        self.max_posts_if_new = config.NEW_FEED_POSTS_MAX[self.config["new"]]

        # Configure parser
        for parser_name in ("hext", "jmes", "jmespath", "pandas"):  # Searched in alphabetical order.
            if parser_config := self.config.get(parser_name):
                if parser_name == "jmes":  # Deprecated name.
                    parser_name = "jmespath"

                if isinstance(parser_config, str):
                    parser_config = {"select": parser_config, "follow": None}
                parser_selector, parser_follower = parser_config["select"], parser_config.get("follow")

                break
        else:
            parser_name = "feedparser"
            parser_selector, parser_follower = None, None
        self.parser_name, self.parser_selector, self.parser_follower = parser_name, parser_selector, parser_follower

        log.debug(f"Initialized {self} having {len(self.urls)} configured URLs.")

    def __str__(self):
        return f"feed {self.name} reader of {self.channel}"

    def _dedupe_entries(self, entries: List[FeedEntry], *, after_what: Optional[str] = None) -> List[FeedEntry]:
        """Remove duplicate entries while preserving order."""
        # e.g. for https://projecteuclid.org/feeds/euclid.ba_rss.xml
        action = f"After {after_what}, removing" if after_what else "Removing"
        log.debug("%s duplicate entry URLs for %s.", action, self)
        entries_deduped = list(dict.fromkeys(entries))
        num_removed = len(entries) - len(entries_deduped)
        action = f"After {after_what}, removed" if after_what else "Removed"
        log.debug(
            "%s %s duplicate entry URLs out of %s, leaving %s, for %s.", action, num_removed, len(entries), len(entries_deduped), self,
        )
        return entries_deduped

    def _process_entries(self, entries: List[FeedEntry]) -> List[FeedEntry]:  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
        feed_config = self.config

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

        # Enforce HTTPS for URLs
        if feed_config.get("https"):
            log.debug("Enforcing HTTPS for URLs in %s.", self)
            for entry in entries:
                if entry.long_url.startswith("http://"):
                    entry.long_url = entry.long_url.replace("http://", "https://", 1)
            log.debug("Enforced HTTPS for URLs in %s.", self)

        # Remove WWW from URLs
        if feed_config.get("www") is False:
            log.debug("Removing WWW from URLs in %s.", self)
            for entry in entries:
                for protocol in ("https", "http"):
                    prefix = f"{protocol}://www."
                    if entry.long_url.startswith(prefix):
                        entry.long_url = entry.long_url.replace(prefix, prefix[:-4], 1)
            log.debug("Removed WWW from URLs in %s.", self)

        # Substitute entries
        if sub_config := feed_config.get("sub"):
            log.debug("Substituting entries for %s.", self)
            re_sub: Callable[[Dict[str, str], str], str] = lambda r, v: re.sub(r["pattern"], r["repl"], v)
            for sub_attr, entry_attr in {"title": "title", "url": "long_url", "summary": "summary"}.items():
                if sub_attr_config := sub_config.get(sub_attr):
                    for entry in entries:
                        if entry_attr_val_old := getattr(entry, entry_attr):
                            entry_attr_val_new = re_sub(sub_attr_config, entry_attr_val_old)
                            setattr(entry, entry_attr, entry_attr_val_new)
            log.debug("Substituted entries for %s.", self)

        # Format entries
        if format_config := feed_config.get("format"):
            log.debug("Formatting entries for %s.", self)
            format_re = format_config.get("re") or {}
            format_str = format_config.get("str") or {}
            for entry in entries:
                # Collect:
                params = {
                    **entry.data,
                    "title": entry.title,
                    "url": entry.long_url,
                    "summary": entry.summary,
                    "categories": entry.categories,
                }
                for re_key, re_val in format_re.items():
                    if match := re.search(re_val, params[re_key]):
                        params.update(match.groupdict())
                # Format title:
                title_format_str = format_str.get("title", "{title}")
                try:
                    entry.title = title_format_str.format_map(params)
                except Exception as exc:  # pylint: disable=broad-except
                    log.warning(f"Unable to format entry title for {entry} by {self} due to exception {exc!r} using format string {title_format_str!r}.")
                # Format URL:
                url_format_str = format_str.get("url", "{url}")
                try:
                    entry.long_url = url_format_str.format_map(params)
                except Exception as exc:  # pylint: disable=broad-except
                    log.warning(f"Unable to format entry URL for {entry} by {self} due to exception {exc!r} using format string {url_format_str!r}.")
            log.debug("Formatted entries for %s.", self)

        # Escape spaces in URLs
        log.debug("Escaping spaces in URLs for %s.", self)
        for entry in entries:
            # e.g. for https://covid-api.com/api/reports?iso=USA&region_province=New York&date=2020-03-15
            entry.long_url = entry.long_url.strip().replace(" ", "%20")
        log.debug("Escaped spaces in URLs for %s.", self)

        # Strip HTML tags from titles and summaries
        log.debug("Stripping HTML tags from titles and summaries for %s.", self)
        for entry in entries:
            # e.g. for http://rss.sciencedirect.com/publication/science/08999007  (Elsevier Nutrition journal)
            entry.title = html_to_text(entry.title)
            entry.summary = html_to_text(entry.summary)
        log.debug("Stripped HTML tags from titles and summaries for %s.", self)

        # Strip unicode quotes around titles
        quote_begin, quote_end = tuple("“”")
        # e.g. for https://www.sciencedirect.com/science/article/abs/pii/S0899900718307883
        log.debug("Stripping unicode quotes around titles for %s.", self)
        for entry in entries:
            title = entry.title
            if (len(title) > 2) and (title[0] == quote_begin) and (title[-1] == quote_end):
                title = title[1:-1]
                if (quote_begin not in title) and (quote_end not in title):
                    entry.title = title
        log.debug("Stripped unicode quotes around titles for %s.", self)

        # Remove trailing periods from title
        log.debug("Removing trailing periods from single-sentence titles for %s.", self)
        for entry in entries:
            if len(entry.title.rstrip().split(". ", maxsplit=1)) < 2:  # Crude check.
                entry.title = entry.title.rstrip().rstrip(".")  # e.g. for PubMed RSS feeds
        log.debug("Removed trailing periods from single-sentence titles for %s.", self)

        # Replace all-caps titles
        log.debug("Capitalizing all-caps multi-word titles for %s.", self)
        for entry in entries:
            entry_has_multiple_words = len(entry.title.split(maxsplit=1)) > 1
            if entry_has_multiple_words and entry.title.isupper():  # e.g. for https://redd.it/fm8z83
                entry.title = entry.title.capitalize()
        log.debug("Capitalized all-caps multi-word titles for %s.", self)

        # Shorten titles
        title_max_bytes = config.TITLE_MAX_BYTES
        log.debug("Shortening titles to %s bytes for %s.", title_max_bytes, self)
        for entry in entries:
            entry.title = shorten_to_bytes_width(entry.title, title_max_bytes)
        log.debug("Shortened titles to %s bytes for %s.", title_max_bytes, self)

        # Deduplicate entries
        entries = self._dedupe_entries(entries)

        return entries

    def _parse_entries(self, url_content: bytes) -> Tuple[List[FeedEntry], List[str]]:
        with multiprocessing.Pool(1) as pool:
            log.info(f"Created process worker to parse entries for {self} using {self.parser_name}.")  # DEBUG
            # Note: Using a separate temporary process is a workaround for memory leaks of hext, feedparser, etc.
            raw_entries, urls = pool.apply(_parse_entries, (self.parser_name, self.parser_selector, self.parser_follower, url_content))
            log.info(f"Used process worker to parse {len(raw_entries):,} raw entries and {len(urls):,} URLs for {self} using {self.parser_name}.")  # DEBUG
        log.debug(f"Ended process worker to parse entries for {self} using {self.parser_name}.")
        entries = [FeedEntry(title=e.title, long_url=e.link, summary=e.summary, categories=e.categories, data=dict(e), feed_reader=self,) for e in raw_entries]
        log.debug(f"Converted {len(raw_entries):,} raw entries to actual entries for {self}.")
        return entries, urls

    def read(self) -> "Feed":  # pylint: disable=too-many-locals
        """Read feed with entries."""
        timer = Timer()
        feed_config = self.config

        # Retrieve URL content and parse entries
        urls_pending, urls_read = self.urls.copy(), OrderedSet()
        url_read_approach_counts: collections.Counter = collections.Counter()
        entries = []
        while urls_pending:
            # Read URL
            url = urls_pending.pop(last=False)
            url_content = self.url_reader[url]
            url_read_finish_time = time.monotonic()
            urls_read.add(url)
            url_read_approach_counts.update([url_content.approach])
            # Parse content
            log.debug(f"Parsing entries for {url} for {self} using {self.parser_name}.")
            selected_entries, follow_urls = self._parse_entries(url_content.content)
            log_msg = f"Parsed {len(selected_entries):,} entries and {len(follow_urls):,} followable URLs for {url} for {self} using {self.parser_name}."
            entries.extend(selected_entries)
            urls_pending.update(follow_urls - urls_read)

            # Raise alert if no entries for URL
            if selected_entries:
                log.debug(log_msg)
            else:
                if feed_config.get("alerts", {}).get("empty", True):
                    log_msg += " Either check the feed configuration, or wait for its next read, or set `alerts/empty` to `false` for it."
                    config.runtime.alert(log_msg)
                else:
                    log.warning(log_msg)

            # Sleep between URLs
            if urls_pending:
                time_elapsed_since_url_read = time.monotonic() - url_read_finish_time
                sleep_time = max(0, config.SECONDS_BETWEEN_FEED_URLS - time_elapsed_since_url_read)
                if sleep_time > 0:
                    log.debug(f"Sleeping for {sleep_time:.1f}s before next URL.")
                    time.sleep(sleep_time)

        url_read_approach_desc = readable_list([f"{count} URLs {approach}" for approach, count in url_read_approach_counts.items()])
        log.debug(f"Read {len(entries)} entries via {url_read_approach_desc} for {self} using {self.parser_name} parser in {timer}.")
        entries = self._process_entries(entries)
        log.debug(f"Returning {len(entries)} processed entries via {url_read_approach_desc} for {self} having used {self.parser_name} parser in {timer}.")
        return Feed(entries=entries, reader=self, read_approach=url_read_approach_desc, read_time_used=timer())


@dataclasses.dataclass
class Feed:
    """Initialize a feed with unposted entries."""

    entries: List[FeedEntry]
    reader: FeedReader
    read_approach: str
    read_time_used: float

    def __str__(self):
        return f"feed {self.name} of {self.channel}"

    @cached_property
    def _postable_entries(self) -> List[FeedEntry]:
        """Return the subset of postable entries."""
        log.debug(f"Retrieving postable entries for {self}.")
        unposted_entries = self._unposted_entries

        # Filter entries if new feed
        if self.reader.db.is_new_feed(self.channel, self.name):
            log.debug(f"Filtering new {self} having {len(unposted_entries)} unposted entries for postable entries.")
            max_posts = self.reader.max_posts_if_new
            postable_entries = unposted_entries[:max_posts]
            log.debug(f"Filtered new {self} from {len(unposted_entries)} unposted entries to {len(postable_entries)} postable entries given a limit of {max_posts} entries.")
        else:
            postable_entries = unposted_entries

        # Shorten URLs
        if postable_entries and self.reader.config["shorten"]:
            log.debug(f"Shortening {len(postable_entries)} postable long URLs for {self}.")
            long_urls = [entry.long_url for entry in postable_entries]
            short_urls = self.reader.url_shortener.shorten_urls(long_urls)
            for entry, short_url in zip(postable_entries, short_urls):
                entry.short_url = short_url
            log.debug(f"Shortened {len(postable_entries)} postable long URLs for {self}.")

        log.debug(f"Returning {len(postable_entries)} postable entries for {self}.")
        return postable_entries

    @cached_property
    def _unposted_entries(self) -> List[FeedEntry]:
        """Return the subset of unposted entries."""
        log.debug(f"Retrieving unposted entries for {self}.")
        entries = self.entries

        long_urls = [entry.long_url for entry in entries]
        db_dedup_strategy = self.reader.config.get("dedup") or config.DEDUP_STRATEGY_DEFAULT
        if db_dedup_strategy == "channel":
            unposted_long_urls = self.reader.db.select_unposted_for_channel(self.channel, self.name, long_urls)
        else:
            assert db_dedup_strategy == "feed"
            unposted_long_urls = self.reader.db.select_unposted_for_channel_feed(self.channel, self.name, long_urls)
        unique_unposted_long_urls = set(unposted_long_urls)
        unposted_entries = [entry for entry in entries if entry.long_url in unique_unposted_long_urls]
        log.debug(f"Returning {len(unposted_entries)} unposted entries out of {len(entries)} for {self}.")
        return unposted_entries

    @cached_property
    def channel(self) -> str:
        """Return the feed channel."""
        return self.reader.channel

    @cached_property
    def name(self) -> str:
        """Return the feed name."""
        return self.reader.name

    @cached_property
    def is_postable(self) -> bool:
        """Return whether the feed is postable."""
        return len(self._postable_entries) > 0

    def mark_posted(self) -> None:
        """Mark unposted entries as posted.

        This applies to both unpostable and postable entries.
        """
        if unposted_entries := self._unposted_entries:  # Note: self.postable_entries is intentionally not used here.
            self.reader.db.insert_posted(self.channel, self.name, [entry.long_url for entry in unposted_entries])

    def post(self) -> None:
        """Post the postable entries and also update the channel topic as relevant."""
        irc = self.reader.irc
        channel = self.channel
        seconds_per_msg = config.SECONDS_PER_MESSAGE
        channel_topics = config.runtime.channel_topics
        postable_entries = self._postable_entries
        log.info(f"Posting {len(postable_entries)} entries for {self}.")

        # Post postable entries
        for entry in postable_entries:
            # Send message
            with Throttle(seconds_per_msg):
                msg = entry.message
                irc.msg(channel, msg)
                log.debug("Sent message to %s: %s", channel, msg)

            # Update topic if changed
            with Throttle(seconds_per_msg) as throttle:
                old_topic = channel_topics.get(channel, "")
                new_topic = entry.topic(old_topic)
                if old_topic == new_topic:
                    raise throttle.Break()
                channel_topics[channel] = new_topic
                irc.quote("TOPIC", channel, f":{new_topic}")
                log.info(f"Updated {channel} topic: {new_topic}")

        log.info(f"Posted {len(postable_entries)} entries for {self}.")
