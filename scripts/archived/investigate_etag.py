import argparse
import logging
import json
from pathlib import Path
import time

import requests
from ruamel.yaml import YAML

from ircrssfeedbot import config

log = logging.getLogger(__name__)


def main() -> None:
    # Read args
    parser = argparse.ArgumentParser(prog=config.PACKAGE_NAME, description="ETag investigation")
    parser.add_argument('--config-path', required=True, help='Configuration file path, e.g. /some/dir/config.yaml')
    instance_config_path = Path(parser.parse_args().config_path)

    # Read user config
    log.debug('Reading instance configuration file %s', instance_config_path)
    instance_config = YAML().load(instance_config_path)
    instance_config = json.loads(json.dumps(instance_config))  # Recursively use a dict as the data structure.

    # Log user config
    logged_instance_config = instance_config.copy()
    del logged_instance_config['feeds']
    log.info('Read user configuration file %s having excerpted configuration %s for %s channels %s with %s feeds.',
             instance_config_path, logged_instance_config,
             len(instance_config['feeds']), list(instance_config['feeds']),
             len([feed for channel in instance_config['feeds'].values() for feed in channel]))

    config.INSTANCE = instance_config
    investigate_etags()


def investigate_etags() -> None:
    instance = config.INSTANCE
    urls = sorted({feed_config['url'] for channel_config in instance['feeds'].values() for feed_config in channel_config.values()})
    for url in urls[55:]:
        time.sleep(.5)
        log.debug('Reading %s', url)
        response1 = requests.get(url, timeout=config.REQUEST_TIMEOUT, headers={'User-Agent': config.USER_AGENT, 'If-None-Match': 'jhok23*%^&%^&D*$*7632984'})
        response1.raise_for_status()
        assert response1.status_code == 200
        etag1 = response1.headers.get('ETag')
        if etag1:
            log.info('Response 1 for %s has status %s, content length %s, and etag %s.', url, response1.status_code, len(response1.content), etag1)
            # if etag1.startswith('"') and etag1.endswith('"'): etag1 = etag1[1:-1]
            time.sleep(.5)
            response2 = requests.get(url, timeout=config.REQUEST_TIMEOUT, headers={'User-Agent': config.USER_AGENT, 'If-None-Match': etag1})
            response2.raise_for_status()
            assert response2.status_code in (200, 304)
            etag2 = response2.headers.get('ETag')
            log.info('Response 2 for %s has status %s, content length %s, and etag %s.', url, response2.status_code, len(response2.content), etag2)
        else:
            log.debug('Response 1 for %s has status %s and no etag.', url, response1.status_code)


if __name__ == '__main__':
    main()
