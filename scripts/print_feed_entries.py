"""Print entries from a specific configured feed.

The feed settings are parsed from the user configuration file.

Usage:
CLI arg example: --config-path ~/irc-rss-feed-bot/config.yaml
Customize CHANNEL and FEED.
"""

# pylint: disable=import-error,invalid-name

import logging
from pathlib import Path

import dagdshort

from ircrssfeedbot import config
from ircrssfeedbot.feed import FeedReader
from ircrssfeedbot.main import load_instance_config
from ircrssfeedbot.url import URLReader

# Customize this section:
FEED = "COVID-19:stats:USA:NY"
CHANNEL, FEED = "#trading", "Medium"
# CHANNEL, FEED = "##CoV", "stats:🇺🇸"

config.LOGGING["loggers"][config.PACKAGE_NAME]["level"] = "DEBUG"  # type: ignore
config.configure_logging()

log = logging.getLogger(__name__)

config.runtime.alert = lambda *args: log.exception(args[0])
config.runtime.identity = ""
load_instance_config(log_details=False)
config.INSTANCE["feeds"][CHANNEL][FEED]["style"] = None

url_reader = URLReader(max_cache_age=3600)
url_shortener = dagdshort.Shortener(user_agent_suffix=f"{config.REPO_NAME}/" + "/".join(Path(__file__).parts[-2:]), max_cache_size=config.CACHE_MAXSIZE__URL_SHORTENER)
feed = FeedReader(channel=CHANNEL, name=FEED, irc=None, db=None, url_reader=url_reader, url_shortener=url_shortener, publishers=None).read()  # type: ignore
for index, entry in enumerate(feed.entries):
    post = f"\n#{index + 1:,}: {entry.message()}"
    if entry.categories:
        post += "\nCategories: " + "; ".join(entry.categories)
    print(post)
