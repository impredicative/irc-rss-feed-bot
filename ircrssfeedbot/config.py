"""Package configuration."""
import logging.config
import os
import tempfile
import types
from pathlib import Path
from typing import Dict, Final

import ircmessage


def configure_logging() -> None:
    """Configure logging."""
    logging.config.dictConfig(LOGGING)
    log = logging.getLogger(__name__)
    log.debug("Logging is configured.")


# Meta
CACHE_MAXSIZE_DEFAULT: Final = 512
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
CACHE_TTL__URL_COMPRESSION: Final = 60
DB_FILENAME: Final = "posts.v2.db"
DISKCACHE_PATH: Final = PACKAGE_PATH.parent / f".{PACKAGE_NAME}_cache"
DISKCACHE_SIZE_LIMIT: Final = GiB * 2
DEDUP_STRATEGY_DEFAULT: Final = "channel"
ETAG_CACHE_PROHIBITED_NETLOCS: Final = {
    "blog.ml.cmu.edu",
    "blogs.cornell.edu",
    "bodyrecomposition.com",
    "deeplearning.ai",
    "devblogs.nvidia.com",
    "export.arxiv.org",
    "rise.cs.berkeley.edu",
    "siliconangle.com",
}
ETAG_TEST_PROBABILITY: Final = 0.1
FEED_DEFAULTS: Final = {"new": "some", "shorten": True}
IRC_COLORS = set(ircmessage.colors.idToName.values())
MIN_CHANNEL_IDLE_TIME_DEFAULT: Final = {"dev": 1}.get(ENV, 15 * 60)
MIN_CONSECUTIVE_FEED_FAILURES_FOR_ALERT: Final = 3
NEW_FEED_POSTS_MAX: Final = {"none": 0, "some": 3, "all": None}
PERIOD_HOURS_DEFAULT: Final = 1
PERIOD_HOURS_MIN: Final = {"dev": 0.0001}.get(ENV, 0.2)
PERIOD_RANDOM_PERCENT: Final = 5
QUOTE_LEN_MAX: Final = 510  # Leaving 2 for "\r\n".
READ_ATTEMPTS_MAX: Final = 3
REQUEST_TIMEOUT: Final = 90
SECONDS_BETWEEN_FEED_URLS: Final = 1
SECONDS_PER_MESSAGE: Final = 2
TEMPDIR: Final = Path(tempfile.gettempdir())
TITLE_MAX_BYTES = 2048  # Relevant for publishing.
USER_AGENT_DEFAULT: Final = "Mozilla/5.0 (X11; Linux x86_64; rv:76.0) Gecko/20100101 Firefox/76.0"
USER_AGENT_OVERRIDES: Final = {  # Site-specific overrides (without www prefix). Sites must be in lowercase.
    "medscape.com": "Googlebot-News",
    "m.youtube.com": "Mozilla/5.0",
    "swansonvitamins.com": "FeedFetcher-Google; (+http://www.google.com/feedfetcher.html)",
    "youtu.be": "Mozilla/5.0",
    "youtube.com": "Mozilla/5.0",
}

# Calculated
LOGGING: Final = {  # Ref: https://docs.python.org/3/howto/logging.html#configuring-logging
    "version": 1,
    "formatters": {
        "detailed": {"format": "%(asctime)s %(levelname)s %(threadName)s:%(name)s:%(lineno)d:%(funcName)s: %(message)s",},  # Note: Use %(thread)x- if needed for thread ID.
    },
    "handlers": {"console": {"class": "logging.StreamHandler", "level": "DEBUG", "formatter": "detailed", "stream": "ext://sys.stdout",},},
    "loggers": {
        PACKAGE_NAME: {"level": "INFO", "handlers": ["console"], "propagate": False},
        "bitlyshortener": {"level": "INFO", "handlers": ["console"], "propagate": False},
        "peewee": {"level": "INFO", "handlers": ["console"], "propagate": False},
        "": {"level": "INFO", "handlers": ["console"]},
    },
}

configure_logging()
