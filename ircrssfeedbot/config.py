import logging.config
from pathlib import Path
import tempfile
from typing import Dict


def configure_logging() -> None:
    logging.config.dictConfig(LOGGING)
    log = logging.getLogger(__name__)
    log.debug('Logging is configured.')


INSTANCE: Dict = {}  # Set from YAML config file.
PACKAGE_NAME = Path(__file__).parent.stem

ALERTS_CHANNEL_FORMAT_DEFAULT = '##{nick}-alerts'
BITLY_SHORTENER_MAX_CACHE_SIZE = 4096
DB_FILENAME = 'posts.v1.db'
DEDUP_STRATEGY_DEFAULT = 'channel'
MESSAGE_FORMAT = '[{feed}] {title} → {url}'
MIN_CHANNEL_IDLE_TIME = 15 * 60
NEW_FEED_POSTS_DEFAULT = 'some'
NEW_FEED_POSTS_MAX = {'none': 0, 'some': 3, 'all': None}
PERIOD_HOURS_DEFAULT = 1
PERIOD_HOURS_MIN = .25
PERIOD_RANDOM_PERCENT = 5
REQUEST_TIMEOUT = 90
SECONDS_PER_MESSAGE = 2
TEMPDIR = Path(tempfile.gettempdir())
USER_AGENT = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:65.0) Gecko/20100101 Firefox/65.0'

LOGGING = {  # Ref: https://docs.python.org/3/howto/logging.html#configuring-logging
    'version': 1,
    'formatters': {
        'detailed': {
            'format': '%(asctime)s %(levelname)s %(threadName)s:%(name)s:%(lineno)d:%(funcName)s: %(message)s',
        },  # Note: Use %(thread)x- if needed for thread ID.
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'detailed',
            'stream': 'ext://sys.stdout',
        },
    },
    'loggers': {
        PACKAGE_NAME: {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': False,
        },
        'bitlyshortener': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': False,
        },
        'peewee': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': False,
        },
        '': {
            'level': 'DEBUG',
            'handlers': ['console'],
        },
    },
}

configure_logging()
