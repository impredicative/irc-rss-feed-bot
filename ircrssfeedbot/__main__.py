import argparse
import logging
import json
from pathlib import Path

from ruamel.yaml import YAML

from ircrssfeedbot import config

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
    logged_instance_config = instance_config.copy()
    del logged_instance_config['nick_password']
    log.info('Read user configuration file "%s" having configuration: %s',
             instance_config_path, json.dumps(logged_instance_config))

    # Process user config
    instance_config['dir'] = instance_config_path.parent
    instance_config['alerts_channel'] = f'##{instance_config["nick"]}-alerts'
    if instance_config['alerts_channel'] not in instance_config['feeds']:
        instance_config['feeds'][instance_config['alerts_channel']] = {}
    config.INSTANCE = instance_config

    # Start bot
    #Bot().serve()


if __name__ == '__main__':
    main()
