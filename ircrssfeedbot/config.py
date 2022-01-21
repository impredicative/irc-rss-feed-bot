"""Package configuration."""
import logging.config
import os
import tempfile
import types
from pathlib import Path
from typing import Dict, Final, Pattern

import emoji
import ircstyle


def configure_logging() -> None:
    """Configure logging."""
    logging.config.dictConfig(LOGGING)
    log = logging.getLogger(__name__)
    log.debug("Logging is configured.")


# Meta
CACHE_MAXSIZE_DEFAULT: Final = 1024
INSTANCE: Dict = {}  # Gets set from YAML config file.
runtime = types.SimpleNamespace()  # Set at runtime.  # pylint: disable=invalid-name
PACKAGE_PATH: Final = Path(__file__).parent
PACKAGE_NAME: Final = PACKAGE_PATH.stem
ENV: Final = os.getenv(f"{PACKAGE_NAME.upper()}_ENV", "prod")  # Externally set as needed: IRCRSSFEEDBOT_ENV='dev'
GiB = 1024 ** 3  # pylint: disable=invalid-name

# Main
ALERTS_CHANNEL_FORMAT_DEFAULT: Final = "##{nick}-alerts"
CACHE_MAXSIZE__BITLY_SHORTENER: Final = CACHE_MAXSIZE_DEFAULT
CACHE_MAXSIZE__INT8HASH: Final = CACHE_MAXSIZE_DEFAULT
CACHE_MAXSIZE__URL_COMPRESSION: Final = 4
CACHE_MAXSIZE__URL_GOOGLE_NEWS: Final = CACHE_MAXSIZE_DEFAULT
CACHE_MAXSIZE__URL_NETLOC: Final = CACHE_MAXSIZE_DEFAULT
CACHE_MAXSIZE__URL_REDIRECT: Final = CACHE_MAXSIZE_DEFAULT
CACHE_TTL__URL_COMPRESSION: Final = 60
DB_FILENAME: Final = "posts.v2.db"
DISKCACHE_PATH: Final = PACKAGE_PATH.parent / f".{PACKAGE_NAME}_cache"
DISKCACHE_SIZE_LIMIT: Final = GiB * 2
DEDUP_STRATEGY_DEFAULT: Final = "feed"
EMOJI_REGEXP: Final[Pattern] = emoji.get_emoji_regexp()
ETAG_CACHE_PROHIBITED_NETLOCS: Final = {
    "ambcrypto.com",
    "blog.ml.cmu.edu",
    "blogs.cornell.edu",
    "bodyrecomposition.com",
    "code.fb.com",
    "cryptomining-blog.com",
    "deeplearning.ai",
    "devblogs.nvidia.com",
    "export.arxiv.org",
    "investing.com",
    "lynalden.com",
    "microsoft.com",
    "news.developer.nvidia.com",
    "protonmail.com",
    "rise.cs.berkeley.edu",
    "siliconangle.com",
}
ETAG_TEST_PROBABILITY: Final = 0.1
FEED_DEFAULTS: Final = {"new": "some", "shorten": True}
IRC_COLORS: Final = set(ircstyle.colors.idToName.values())
MIN_CHANNEL_IDLE_TIME_DEFAULT: Final = {"dev": 1}.get(ENV, 15 * 60)
MIN_CONSECUTIVE_FEED_FAILURES_FOR_ALERT: Final = 3
MIN_FEED_INTERVAL_FOR_REPEATED_ALERT: Final = 15 * 60
NEW_FEED_POSTS_MAX: Final = {"none": 0, "some": 3, "all": None}
PERIOD_HOURS_DEFAULT: Final = 1
PERIOD_HOURS_MIN: Final = {"dev": 0.0001}.get(ENV, 0.2)
PERIOD_RANDOM_PERCENT: Final = 5
PUBLISH_ATTEMPTS_MAX: Final = 2
PUBLISH_THREADS_MAX: Final = 4
PUBLISH_RETRY_SLEEP_MAX: Final = 60
QUOTE_LEN_MAX: Final = 512 - 2 - 1  # Leaving 2 for "\r\n" and 1 to prevent unexplained truncation.
READ_ATTEMPTS_MAX: Final = 3
REQUEST_TIMEOUT: Final = 90
SEARCH_CACHE_MAXSIZE: Final = 256
SEARCH_CACHE_TTL: Final = 3600 * 8
SECONDS_BETWEEN_FEED_URLS: Final = 1
SECONDS_PER_HEAD_REQUEST: Final = 0.5
SECONDS_PER_MESSAGE: Final = 2
TEMPDIR: Final = Path(tempfile.gettempdir())
TITLE_MAX_BYTES: Final = 2048  # Relevant for publishing.
USER_AGENT_DEFAULT: Final = "Mozilla/5.0 (X11; Linux x86_64; rv:96.0) Gecko/20100101 Firefox/96.0"
USER_AGENT_OVERRIDES: Final = {  # Site-specific overrides (without www prefix). Sites must be in lowercase.
    "etf.com": "Googlebot-News",
    "medscape.com": "Googlebot-News",
    "nasdaq.com": "https://www",
    "news.google.com": "(entropy)",
    "swansonvitamins.com": "FeedFetcher-Google; (+http://www.google.com/feedfetcher.html)",
    "youtube.com": "Mozilla/5.0",
}

# Calculated
LOGGING: Final = {  # Ref: https://docs.python.org/3/howto/logging.html#configuring-logging
    "version": 1,
    "formatters": {  # Ref: https://docs.python.org/3/library/logging.html#logrecord-attributes
        "detailed": {"format": "%(asctime)s %(levelname)s %(threadName)s-%(thread)x:%(name)s:%(lineno)d:%(funcName)s: %(message)s"},
    },
    "handlers": {"console": {"class": "logging.StreamHandler", "level": "DEBUG", "formatter": "detailed", "stream": "ext://sys.stdout"}},
    "loggers": {
        PACKAGE_NAME: {"level": "INFO", "handlers": ["console"], "propagate": False},
        "bitlyshortener": {"level": "INFO", "handlers": ["console"], "propagate": False},
        "peewee": {"level": "INFO", "handlers": ["console"], "propagate": False},
        "": {"level": "INFO", "handlers": ["console"]},
    },
}

configure_logging()
