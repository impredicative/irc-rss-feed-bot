import argparse
import logging
import json
from pathlib import Path

from ruamel.yaml import YAML

from ircrssfeedbot import Bot, config

log = logging.getLogger(__name__)


def main() -> None:
    # Read args
    parser = argparse.ArgumentParser(prog=config.PACKAGE_NAME, description="IRC RSS feed posting bot")
    parser.add_argument('--config-path', required=True, help='Configuration file path, e.g. /some/dir/config.yaml')
    instance_config_path = Path(parser.parse_args().config_path)

    # Read user config
    log.debug('Reading instance configuration file %s', instance_config_path)
    instance_config = YAML().load(instance_config_path)
    instance_config = json.loads(json.dumps(instance_config))  # Recursively use a dict as the data structure.

    # Log user config
    logged_instance_config = instance_config.copy()
    for key in ('nick_password', 'tokens', 'feeds'):
        del logged_instance_config[key]
    log.info('Read user configuration file "%s" having excerpted configuration %s for %s channels %s with %s feeds.',
             instance_config_path, logged_instance_config,
             len(instance_config['feeds']), list(instance_config['feeds']),
             len([feed for channel in instance_config['feeds'].values() for feed in channel]))

    for channel, channeL_config in instance_config['feeds'].items():
        for feed, feed_config in channeL_config.items():
            log.info('User configuration for channel %s has feed %s with configuration: %s',
                     channel, feed, feed_config)

    # Setup alerts channel
    if 'alerts_channel' not in instance_config:
        instance_config['alerts_channel'] = config.ALERTS_CHANNEL_FORMAT_DEFAULT
    instance_config['alerts_channel'] = instance_config['alerts_channel'].format(nick=instance_config['nick'])
    if instance_config['alerts_channel'] not in instance_config['feeds']:
        instance_config['feeds'][instance_config['alerts_channel']] = {}

    # Process user config
    instance_config['dir'] = instance_config_path.parent
    instance_config['nick:casefold'] = instance_config['nick'].casefold()
    instance_config['channels:casefold'] = [channel.casefold() for channel in instance_config['feeds']]
    config.INSTANCE = instance_config

    # Start bot
    Bot()


if __name__ == '__main__':
    main()
