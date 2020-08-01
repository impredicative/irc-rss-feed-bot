"""Config loader and bot runner."""
import argparse
import collections
import json
import logging
from pathlib import Path

from ruamel.yaml import YAML

from ircrssfeedbot import config
from ircrssfeedbot.bot import Bot
from ircrssfeedbot.util.list import ensure_list
from ircrssfeedbot.util.tracemalloc import TraceMalloc

log = logging.getLogger(__name__)


def load_instance_config(log_details: bool = True) -> None:  # pylint: disable=too-many-locals
    """Read and load the instance configuration."""
    # Read args
    parser = argparse.ArgumentParser(prog=config.PACKAGE_NAME, description="IRC RSS feed posting bot")
    parser.add_argument("--config-path", required=True, help="Configuration file path, e.g. /some/dir/config.yaml")
    instance_config_path = Path(parser.parse_args().config_path)

    # Read instance config
    log.debug("Reading instance configuration file %s", instance_config_path)
    instance_config = YAML().load(instance_config_path)
    instance_config = json.loads(json.dumps(instance_config))  # Recursively use a dict as the data structure.
    log.info("Read user configuration file %s", instance_config_path)
    if "taxonomies" in instance_config:
        del instance_config["taxonomies"]

    if instance_config.get("tracemalloc"):
        TraceMalloc().start()

    if not instance_config["feeds"]:
        instance_config["feeds"] = {}

    url_counter = collections.Counter(
        feed_url for channel_cfg in instance_config["feeds"].values() for feed_cfg in channel_cfg.values() for feed_url in ensure_list(feed_cfg["url"])
    )

    if log_details:

        # Log instance config
        logged_instance_config = instance_config.copy()
        del logged_instance_config["feeds"]
        log.info(
            "The excerpted configuration for %s channels with %s feeds having %s unique URLs is:\n%s",
            len(instance_config["feeds"]),
            len([feed for channel in instance_config["feeds"].values() for feed in channel]),
            len(url_counter),
            logged_instance_config,
        )

        # Log channel config
        for channel, channel_config in instance_config["feeds"].items():
            feed_names = sorted(channel_config)
            log.info("%s has %s feeds: %s", channel, len(feed_names), ", ".join(feed_names))
            for feed, feed_config in channel_config.items():
                log.debug("%s has feed %s having config: %s", channel, feed, feed_config)

        # Log unused channel colors
        unclear_colors = {"white", "black", "grey", "silver"}
        clear_colors = config.IRC_COLORS - unclear_colors
        for channel, channel_config in instance_config["feeds"].items():
            if not (used_colors := {fg_color for feed_config in channel_config.values() if (fg_color := feed_config.get("style", {}).get("name", {}).get("fg")) is not None}):
                log.info("%s has no foreground colors in use.", channel)
                continue
            if not (unused_colors := clear_colors - used_colors):  # pylint: disable=superfluous-parens
                log.info("%s has all foreground colors in use.", channel)
                continue
            log.info("%s has %s unused foreground colors: %s", channel, len(unused_colors), ", ".join(sorted(unused_colors)))

    # Set alerts channel
    alerts_channel_format = instance_config.get("alerts_channel") or config.ALERTS_CHANNEL_FORMAT_DEFAULT
    instance_config["alerts_channel"] = alerts_channel_format.format(nick=instance_config["nick"])
    if instance_config["alerts_channel"] not in instance_config["feeds"]:
        instance_config["feeds"][instance_config["alerts_channel"]] = {}  # Set as a feeds channel.

    # Process instance config
    instance_config["dir"] = instance_config_path.parent
    instance_config["nick:casefold"] = instance_config["nick"].casefold()
    instance_config["channels:casefold"] = [channel.casefold() for channel in instance_config["feeds"]]
    # instance_config["repeated_urls"] = {url for url, count in url_counter.items() if count > 1}

    instance_config["defaults"] = {k: instance_config.get("defaults", {}).get(k, v) for k, v in config.FEED_DEFAULTS.items()}

    config.INSTANCE = instance_config


def main() -> None:
    """Start the bot."""
    load_instance_config()
    Bot()
