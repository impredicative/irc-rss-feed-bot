import abc
import datetime
from typing import List, Union

import feedparser
from descriptors import cachedproperty

import feedgen.feed
from ircrssfeedbot import config
from ircrssfeedbot.entry import FeedEntry, ShortenedFeedEntry


class BaseChannelPublisher(abc.ABC):
    CHANNEL_PATH_FORMAT = "feeds/{channel}.rss"

    def __init__(self, channel: str):
        self.channel = channel
        self.channel_path = self.CHANNEL_PATH_FORMAT.format(channel=channel)
        config_ = config.INSTANCE["publish"]["rss"]
        self.repo = config_["repo"]
        self.history = config_.get("history", config.PUBLISH_RSS_HISTORY_HOURS_DEFAULT)

    @cachedproperty
    @abc.abstractmethod
    def channel_url(self) -> str:
        ...

    @property
    @abc.abstractmethod
    def content(self) -> bytes:
        ...

    @content.setter
    @abc.abstractmethod
    def content(self, xml: bytes) -> None:
        ...

    @property
    def default_content(self) -> bytes:
        return self.default_feed().rss_str(pretty=True)

    def default_feed(self) -> feedgen.feed.FeedGenerator:
        feed = feedgen.feed.FeedGenerator()
        feed.title(self.channel)
        feed.link(href=self.repo_url, rel="self")
        feed.description(f'{self.channel} on {config.INSTANCE["host"]}')
        return feed

    @property
    def add_entries(self, entries: List[Union[FeedEntry, ShortenedFeedEntry]]) -> None:
        old_entries = feedparser.parse(self.content.lstrip())["entries"]
        feed = self.default_feed()
        for old_entry in old_entries:
            entry = feed.add_entry(order="append")
            entry.title(old_entry.title)
            entry.link(href=old_entry.link)
            entry.guid(old_entry.link, permalink=True)
            entry.published(old_entry.published)
            for tag in getattr(old_entry, "tags", []):
                entry.category(term=tag["term"])
        new_entries_dt = datetime.datetime.now(tz=datetime.timezone.utc)
        for new_entry in reversed(entries):
            entry = feed.add_entry(order="prepend")
            entry.title(new_entry.title)
            entry.link(new_entry.long_url)
            entry.guid(new_entry.long_url, permalink=True)
            entry.published(new_entries_dt)

        text = feed.rss_str(pretty=True)

    @cachedproperty
    @abc.abstractmethod
    def repo_url(self) -> str:
        ...
