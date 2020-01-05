"""Package entrypoint."""
import argparse
import collections
import json
import logging
from pathlib import Path

from ruamel.yaml import YAML

from ircrssfeedbot import Bot, config

log = logging.getLogger(__name__)


def main() -> None:
    """Start the bot."""
    # Read args
    parser = argparse.ArgumentParser(prog=config.PACKAGE_NAME, description="IRC RSS feed posting bot")
    parser.add_argument("--config-path", required=True, help="Configuration file path, e.g. /some/dir/config.yaml")
    instance_config_path = Path(parser.parse_args().config_path)

    # Read instance config
    log.debug("Reading instance configuration file %s", instance_config_path)
    instance_config = YAML().load(instance_config_path)
    instance_config = json.loads(json.dumps(instance_config))  # Recursively use a dict as the data structure.

    # Log instance config
    logged_instance_config = instance_config.copy()
    del logged_instance_config["feeds"]
    log.info(
        "Read user configuration file %s having excerpted configuration %s for %s channels %s with %s feeds.",
        instance_config_path,
        logged_instance_config,
        len(instance_config["feeds"]),
        list(instance_config["feeds"]),
        len([feed for channel in instance_config["feeds"].values() for feed in channel]),
    )

    for channel, channel_config in instance_config["feeds"].items():
        for feed, feed_config in channel_config.items():
            log.info("%s has feed %s having config: %s", channel, feed, feed_config)

    # Set alerts channel
    alerts_channel_format = instance_config.get("alerts_channel") or config.ALERTS_CHANNEL_FORMAT_DEFAULT
    instance_config["alerts_channel"] = alerts_channel_format.format(nick=instance_config["nick"])
    if instance_config["alerts_channel"] not in instance_config["feeds"]:
        instance_config["feeds"][instance_config["alerts_channel"]] = {}  # Set as a feeds channel.

    # Process instance config
    instance_config["dir"] = instance_config_path.parent
    instance_config["nick:casefold"] = instance_config["nick"].casefold()
    instance_config["channels:casefold"] = [channel.casefold() for channel in instance_config["feeds"]]
    instance_config["repeated_urls"] = {
        url
        for url, count in collections.Counter(
            feed_cfg["url"] for channel_cfg in instance_config["feeds"].values() for feed_cfg in channel_cfg.values()
        ).items()
        if count > 1
    }
    instance_config["defaults"] = {
        k: instance_config.get("defaults", {}).get(k, v) for k, v in config.FEED_DEFAULTS.items()
    }
    config.INSTANCE = instance_config

    # Start bot
    Bot()


if __name__ == "__main__":
    main()
