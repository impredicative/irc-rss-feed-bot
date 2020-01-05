import logging
import threading
from typing import List, Set

import peewee
from peewee import chunked

from . import config
from .util.hashlib import Int8Hash
from .util.humanize import humanize_bytes

log = logging.getLogger(__name__)
_DATABASE = peewee.SqliteDatabase(None)


class Post(peewee.Model):
    channel = peewee.BigIntegerField(null=False, verbose_name="signed hash of channel name")
    feed = peewee.BigIntegerField(null=False, verbose_name="signed hash of feed name")
    url = peewee.BigIntegerField(null=False, verbose_name="signed hash of long URL")

    class Meta:
        database = _DATABASE
        legacy_table_names = False  # This will become a default in peewee>=4
        primary_key = peewee.CompositeKey("channel", "feed", "url")
        indexes = (
            # (('channel', 'feed', 'url'), True),  # Not needed per EXPLAIN QUERY PLAN due to sqlite_autoindex_post_1.
            (("channel", "url"), False),
        )  # True means unique.


class Database:
    def __init__(self) -> None:
        # Initialize db
        log.debug("Initializing database.")
        db_path = config.INSTANCE["dir"] / config.DB_FILENAME
        _DATABASE.init(db_path)  # If facing threading issues, consider https://stackoverflow.com/a/39024742/
        self._db = _DATABASE
        self._db.create_tables([Post])
        self._write_lock = threading.Lock()  # Unclear if necessary, but used anyway for safety.
        log.info("Initialized database having path %s.", db_path)

        # Vacuum db
        pre_vacuum_size = db_path.stat().st_size
        log.debug("Vacuuming database having pre-vacuum size %s.", humanize_bytes(pre_vacuum_size))
        self._db.execute_sql("VACUUM;")
        post_vacuum_size = db_path.stat().st_size
        vacuum_size_diff = pre_vacuum_size - post_vacuum_size
        log.info(
            "Vacuumed database having post-vacuum size %s, saving %s.",
            humanize_bytes(post_vacuum_size),
            humanize_bytes(vacuum_size_diff),
        )

        # Analyze db
        log.debug("Analyzing database.")
        self._db.execute_sql("ANALYZE;")
        log.info("Analyzed database.")

        # Helper function:
        # sql = lambda *s: list(self._db.execute_sql(*s))

    @staticmethod
    def _select_unposted(conditions: peewee.Expression, urls: List[str]) -> List[str]:
        hashes2urls = Int8Hash.as_dict(urls)
        posted_hashes: Set[int] = set()
        for hashes_batch in chunked(hashes2urls, 100):  # Ref: https://www.sqlite.org/limits.html#max_variable_number
            conditions_batch = conditions & Post.url.in_(hashes_batch)
            posted_hashes |= {post[0] for post in Post.select(Post.url).where(conditions_batch).tuples().iterator()}
        unposted_urls = [url for url_hash, url in hashes2urls.items() if url_hash not in posted_hashes]
        return unposted_urls

    @staticmethod
    def is_new_feed(channel: str, feed: str) -> bool:
        conditions = (Post.channel == Int8Hash.as_int(channel)) & (Post.feed == Int8Hash.as_int(feed))
        return not Post.select(Post.url).where(conditions).limit(1)

    def select_unposted_for_channel(self, channel: str, feed: str, urls: List[str]) -> List[str]:
        log.debug(
            "Retrieving unposted URLs from the database for channel %s having ignored feed %s out of %s URLs.",
            channel,
            feed,
            len(urls),
        )
        conditions = Post.channel == Int8Hash.as_int(channel)
        unposted_urls = self._select_unposted(conditions, urls)
        loglevel = logging.INFO if len(unposted_urls) > 0 else logging.DEBUG
        log.log(
            loglevel,
            "Returning %s unposted URLs from the database for channel %s having ignored feed %s out of %s URLs.",
            len(unposted_urls),
            channel,
            feed,
            len(urls),
        )
        return unposted_urls

    def select_unposted_for_channel_feed(self, channel: str, feed: str, urls: List[str]) -> List[str]:
        log.debug(
            "Retrieving unposted URLs from the database for channel %s having feed %s out of %s URLs.",
            channel,
            feed,
            len(urls),
        )
        conditions = (Post.channel == Int8Hash.as_int(channel)) & (Post.feed == Int8Hash.as_int(feed))
        unposted_urls = self._select_unposted(conditions, urls)
        loglevel = logging.INFO if len(unposted_urls) > 0 else logging.DEBUG
        log.log(
            loglevel,
            "Returning %s unposted URLs from the database for channel %s having feed %s out of %s URLs.",
            len(unposted_urls),
            channel,
            feed,
            len(urls),
        )
        return unposted_urls

    def insert_posted(self, channel: str, feed: str, urls: List[str]) -> None:
        log.debug("Inserting %s URLs into the database for channel %s having feed %s.", len(urls), channel, feed)
        channel_hash, feed_hash, urls_hashes = Int8Hash.as_int(channel), Int8Hash.as_int(feed), Int8Hash.as_list(urls)
        data = ({"channel": channel_hash, "feed": feed_hash, "url": url_hash} for url_hash in urls_hashes)
        with self._write_lock, self._db.atomic():
            for batch in chunked(data, 100):  # Ref: https://www.sqlite.org/limits.html#max_variable_number
                Post.insert_many(batch).execute()
                # Note: "sqlite3.IntegrityError: UNIQUE constraint failed" would be indicative of a bug elsewhere.
                # As such, prepending ".on_conflict_ignore()" before ".execute()" should not be needed.
        log.info("Inserted %s URLs into the database for channel %s having feed %s.", len(urls), channel, feed)
