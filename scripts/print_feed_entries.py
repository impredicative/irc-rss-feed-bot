"""Print entries from a specific configured feed.

The feed settings are parsed from the user configuration file.

Usage:
Customize CHANNEL and FEED below.

CLI example: python -m scripts.print_feed_entries --config-path /workspaces/irc-bots/libera/feed-bot/config.yaml

"""

# pylint: disable=import-error,invalid-name

import logging

from ircrssfeedbot import config
from ircrssfeedbot.feed import FeedReader
from ircrssfeedbot.main import load_instance_config
from ircrssfeedbot.url import URLReader

# Customize this section:
FEED = "COVID-19:stats:USA:NY"
CHANNEL, FEED = "#trading", "MarketWatch"
# CHANNEL, FEED = "##CoV", "stats:🇺🇸"
# CHANNEL, FEED = "#workerbot", "ArXiv:fin"
CHANNEL, FEED = "##machinelearning", "Nvidia:Research"

config.LOGGING["loggers"][config.PACKAGE_NAME]["level"] = "DEBUG"  # type: ignore
config.configure_logging()

log = logging.getLogger(__name__)

config.runtime.alert = lambda *args: log.exception(args[0])
config.runtime.identity = ""
load_instance_config(log_details=False)
config.INSTANCE["feeds"][CHANNEL][FEED]["style"] = None

# URL_SHORTENER__USER_AGENT_SUFFIX = f"{config.REPO_NAME}/" + "/".join(Path(__file__).parts[-2:])
# print(f"User agent suffix for URL shortener is: {URL_SHORTENER__USER_AGENT_SUFFIX}")
# url_shortener = dagdshort.Shortener(user_agent_suffix=URL_SHORTENER__USER_AGENT_SUFFIX, max_cache_size=config.CACHE_MAXSIZE__URL_SHORTENER)
# Note: url_shortener cannot be used in this script because URL shortening is done at a later stage.

url_reader = URLReader(max_cache_age=3600)
feed = FeedReader(channel=CHANNEL, name=FEED, irc=None, db=None, url_reader=url_reader, url_shortener=None, publishers=None).read()  # type: ignore
for index, entry in enumerate(feed.entries):
    post = f"\n#{index + 1:,}: {entry.message()}"
    if entry.categories:
        post += "\nCategories: " + "; ".join(entry.categories)
    print(post)
