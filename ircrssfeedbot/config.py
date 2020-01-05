import logging.config
import os
import tempfile
import types
from pathlib import Path
from typing import Dict, Final


def configure_logging() -> None:
    logging.config.dictConfig(LOGGING)
    log = logging.getLogger(__name__)
    log.debug("Logging is configured.")


# Meta
INSTANCE: Dict = {}  # Gets set from YAML config file.
runtime = types.SimpleNamespace()  # Set at runtime.
PACKAGE_NAME: Final = Path(__file__).parent.stem
ENV: Final = os.getenv(f"{PACKAGE_NAME.upper()}_ENV", "prod")  # Externally set as needed: IRCRSSFEEDBOT_ENV='dev'

# Main
ALERTS_CHANNEL_FORMAT_DEFAULT: Final = "##{nick}-alerts"
BITLY_SHORTENER_MAX_CACHE_SIZE: Final = 2048
DB_FILENAME: Final = "posts.v2.db"
DEDUP_STRATEGY_DEFAULT: Final = "channel"
ETAG_CACHE_PROHIBITED_NETLOCS: Final = {
    "blogs.cornell.edu",
    "bodyrecomposition.com",
    "deeplearning.ai",
    "export.arxiv.org",
    "rise.cs.berkeley.edu",
    "siliconangle.com",
}
ETAG_TEST_PROBABILITY: Final = 0.1
FEED_DEFAULTS: Final = {"new": "some", "shorten": True}
MESSAGE_FORMAT: Final = "[{feed}] {title} → {url}"
MIN_CHANNEL_IDLE_TIME_DEFAULT: Final = {"dev": 1}.get(ENV, 15 * 60)
MIN_CONSECUTIVE_FEED_FAILURES_FOR_ALERT: Final = 3
NEW_FEED_POSTS_MAX: Final = {"none": 0, "some": 3, "all": None}
PERIOD_HOURS_DEFAULT: Final = 1
PERIOD_HOURS_MIN: Final = {"dev": 0.0001}.get(ENV, 0.2)
PERIOD_RANDOM_PERCENT: Final = {"dev": 20}.get(ENV, 5)
QUOTE_LEN_MAX: Final = 510  # Leaving 2 for "\r\n".
READ_ATTEMPTS_MAX: Final = 3
REQUEST_TIMEOUT: Final = 90
SECONDS_PER_MESSAGE: Final = 2
TEMPDIR: Final = Path(tempfile.gettempdir())
USER_AGENT_DEFAULT: Final = "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:71.0) Gecko/20100101 Firefox/71.0"
USER_AGENT_OVERRIDES: Final = {  # Site-specific overrides (without www prefix). Sites must be in lowercase.
    "medscape.com": "Googlebot-News",
    "m.youtube.com": "Mozilla/5.0",
    "swansonvitamins.com": "FeedFetcher-Google; (+http://www.google.com/feedfetcher.html)",
    "youtu.be": "Mozilla/5.0",
    "youtube.com": "Mozilla/5.0",
}

# Calculated
PRIVMSG_FORMAT: Final = f":{{identity}} PRIVMSG {{channel}} :{MESSAGE_FORMAT}"  # Assumed.
URL_CACHE_TTL: Final = PERIOD_HOURS_MIN * 3600 * ((100 - PERIOD_RANDOM_PERCENT) / 100) * 0.99

LOGGING: Final = {  # Ref: https://docs.python.org/3/howto/logging.html#configuring-logging
    "version": 1,
    "formatters": {
        "detailed": {
            "format": "%(asctime)s %(levelname)s %(threadName)s:%(name)s:%(lineno)d:%(funcName)s: %(message)s",
        },  # Note: Use %(thread)x- if needed for thread ID.
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "detailed",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        PACKAGE_NAME: {"level": "INFO", "handlers": ["console"], "propagate": False},
        "bitlyshortener": {"level": "INFO", "handlers": ["console"], "propagate": False},
        "peewee": {"level": "INFO", "handlers": ["console"], "propagate": False},
        "": {"level": "INFO", "handlers": ["console"],},
    },
}

configure_logging()
