import argparse
import json
import logging
from pathlib import Path

from ruamel.yaml import YAML

from ircrssfeedbot import config
from ircrssfeedbot.util.urllib import url_to_netloc

log = logging.getLogger(__name__)


def main() -> None:
    # Read args
    parser = argparse.ArgumentParser(prog=config.PACKAGE_NAME, description="Netloc investigation")
    parser.add_argument("--config-path", required=True, help="Configuration file path, e.g. /some/dir/config.yaml")
    instance_config_path = Path(parser.parse_args().config_path)

    # Read user config
    log.debug("Reading instance configuration file %s", instance_config_path)
    instance_config = YAML().load(instance_config_path)
    instance_config = json.loads(json.dumps(instance_config))  # Recursively use a dict as the data structure.

    # Log user config
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

    config.INSTANCE = instance_config
    investigate_etags()


def investigate_etags() -> None:
    instance = config.INSTANCE
    netlocs = sorted({url_to_netloc(feed_config["url"]) for channel_config in instance["feeds"].values() for feed_config in channel_config.values()})
    log.info("The unique netlocs are: %s", ", ".join(netlocs))
    log.info("Number of unique netlocs is %s.", len(netlocs))


if __name__ == "__main__":
    main()
