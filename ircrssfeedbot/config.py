import logging.config
import os
from pathlib import Path
import tempfile
import types
from typing import Dict


def configure_logging() -> None:
    logging.config.dictConfig(LOGGING)
    log = logging.getLogger(__name__)
    log.debug('Logging is configured.')


# Meta
INSTANCE: Dict = {}  # Gets set from YAML config file.
runtime = types.SimpleNamespace()  # Set at runtime.
PACKAGE_NAME = Path(__file__).parent.stem
ENV = os.getenv(f'{PACKAGE_NAME.upper()}_ENV', 'prod')  # Externally set as needed: IRCRSSFEEDBOT_ENV='dev'

# Main
ALERTS_CHANNEL_FORMAT_DEFAULT = '##{nick}-alerts'
BITLY_SHORTENER_MAX_CACHE_SIZE = 2048
DB_FILENAME = 'posts.v2.db'
DEDUP_STRATEGY_DEFAULT = 'channel'
ETAG_CACHE_PROHIBITED_NETLOCS = {'blogs.cornell.edu',
                                 'bodyrecomposition.com',
                                 'deeplearning.ai',
                                 'export.arxiv.org',
                                 'rise.cs.berkeley.edu',
                                 'siliconangle.com',
                                 }
ETAG_TEST_PROBABILITY = .1
FEED_DEFAULTS = {'new': 'some', 'shorten': True}
MESSAGE_FORMAT = '[{feed}] {title} → {url}'
MIN_CHANNEL_IDLE_TIME = {'dev': 1}.get(ENV, 15 * 60)
NEW_FEED_POSTS_MAX = {'none': 0, 'some': 3, 'all': None}
PERIOD_HOURS_DEFAULT = 1
PERIOD_HOURS_MIN = {'dev': .0001}.get(ENV, .5)
PERIOD_RANDOM_PERCENT = {'dev': 20}.get(ENV, 5)
QUOTE_LEN_MAX = 510  # Leaving 2 for "\r\n".
READ_ATTEMPTS_MAX = 3
REQUEST_TIMEOUT = 90
SECONDS_PER_MESSAGE = 2
TEMPDIR = Path(tempfile.gettempdir())
USER_AGENT_DEFAULT = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:67.0) Gecko/20100101 Firefox/67.0'
USER_AGENT_OVERRIDES = {  # Site-specific overrides (without www prefix). Sites must be in lowercase.
    'medscape.com': 'Googlebot-News',
    'm.youtube.com': 'Mozilla/5.0',
    'swansonvitamins.com': 'FeedFetcher-Google; (+http://www.google.com/feedfetcher.html)',
    'youtu.be': 'Mozilla/5.0',
    'youtube.com': 'Mozilla/5.0',
}

# Calculated
PRIVMSG_FORMAT = f':{{identity}} PRIVMSG {{channel}} :{MESSAGE_FORMAT}'  # Assumed.
URL_CACHE_TTL = PERIOD_HOURS_MIN * 3600 * ((100 - PERIOD_RANDOM_PERCENT) / 100) * .99

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
            'level': 'INFO',
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
            'level': 'INFO',
            'handlers': ['console'],
        },
    },
}

configure_logging()
