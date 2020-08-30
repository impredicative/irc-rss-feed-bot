"""Print entries from a specific configured feed.

The feed settings are parsed from the user configuration file.

Usage:
CLI arg example: --config-path ~/irc-rss-feed-bot/config.yaml
Customize CHANNEL and FEED.
"""

# pylint: disable=import-error,invalid-name

import logging

from ircrssfeedbot import config
from ircrssfeedbot.feed import FeedReader
from ircrssfeedbot.main import load_instance_config
from ircrssfeedbot.url import URLReader

# import os
#
# import bitlyshortener

CHANNEL = "##servicebot"  # CUSTOMIZE
# FEED = "stats:🌎"  # World
# FEED = "stats:🇺🇸"  # USA
# FEED = "stats:🇮🇹"  # Italy
# FEED = "stats:🇷🇺"  # Russia
# FEED = "stats:🇨🇳"  # China
FEED = "COVID-19:stats:USA:NY"
CHANNEL, FEED = "##RL", "r/ML:50+"
# CHANNEL, FEED = "##us-market-news", "SeekingAlpha"
# CHANNEL, FEED = "##usm-earnings", "SA:beats"

config.LOGGING["loggers"][config.PACKAGE_NAME]["level"] = "DEBUG"  # type: ignore
config.configure_logging()

log = logging.getLogger(__name__)

config.runtime.alert = lambda *args: log.exception(args[0])
config.runtime.identity = ""
load_instance_config(log_details=False)
config.INSTANCE["feeds"][CHANNEL][FEED]["style"] = None

# _url_shortener = bitlyshortener.Shortener(
#     tokens=[token.strip() for token in os.environ["BITLY_TOKENS"].strip().split(",")],
#     max_cache_size=config.BITLY_SHORTENER_MAX_CACHE_SIZE,
# )

url_reader = URLReader(max_cache_age=3600)
feed = FeedReader(channel=CHANNEL, name=FEED, irc=None, db=None, url_reader=url_reader, url_shortener=None, publishers=None).read()  # type: ignore
for index, entry in enumerate(feed.entries):
    post = f"\n#{index + 1:,}: {entry.message}"
    if entry.categories:
        post += "\nCategories: " + "; ".join(entry.categories)
    print(post)
