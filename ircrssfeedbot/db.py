import logging
import threading
from typing import List, Union, Set

import peewee
from peewee import chunked

from . import config
from .util.humanize import humanize_bytes

log = logging.getLogger(__name__)
_DATABASE = peewee.SqliteDatabase(None)


class Post(peewee.Model):
    channel = peewee.CharField(64, null=False, verbose_name='channel name')
    feed = peewee.CharField(32, null=False, verbose_name='feed name')
    url = peewee.CharField(512, null=False, verbose_name='long URL')
    # Note: The reason for using the "long URL" instead of the "short URL path" is that the latter can change
    # surprisingly if the array of Bitly tokens is changed in any way, leading to deduplication errors.

    class Meta:
        database = _DATABASE
        legacy_table_names = False  # This will become a default in peewee>=4
        primary_key = peewee.CompositeKey('channel', 'feed', 'url')
        indexes = (
            # (('channel', 'feed', 'url'), True),
            (('channel', 'url'), False),
        )  # True means unique.


class Database:
    def __init__(self):
        log.debug('Initializing database.')
        db_path = config.INSTANCE.get('dir', config.TEMPDIR) / config.DB_FILENAME
        _DATABASE.init(db_path)  # If facing threading issues, consider https://stackoverflow.com/a/39024742/
        self._db = _DATABASE
        self._db.create_tables([Post])
        self._write_lock = threading.Lock()  # Unclear if necessary, but used anyway for safety.
        log.info('Initialized database having path %s and size %s.', db_path, humanize_bytes(db_path.stat().st_size))

    @staticmethod
    def _select_unposted(conditions: peewee.Expression, urls: List[str]) -> List[str]:
        posted: Set[str] = set()
        for urls_batch in chunked(urls, 100):  # Ref: https://www.sqlite.org/limits.html#max_variable_number
            conditions_batch = (conditions & Post.url.in_(urls_batch))
            posted |= {post[0] for post in Post.select(Post.url).where(conditions_batch).tuples().iterator()}
        unposted = [url for url in urls if url not in posted]
        return unposted

    @staticmethod
    def is_new_feed(channel: str, feed: str) -> bool:
        conditions = (Post.channel == channel) & (Post.feed == feed)
        return not Post.select(Post.url).where(conditions).limit(1)

    def select_unposted_for_channel(self, channel: str, urls: List[str]) -> List[str]:
        log.debug('Requesting unposted URLs for channel %s out of %s URLs.', channel, len(urls))
        conditions = (Post.channel == channel)
        unposted_urls = self._select_unposted(conditions, urls)
        log.info('Returning %s unposted URLs for channel %s out of %s URLs.', len(unposted_urls), channel, len(urls))
        return unposted_urls

    def select_unposted_for_channel_feed(self, channel: str, feed: Union[str, None], urls: List[str]) -> List[str]:
        log.debug('Requesting unposted URLs for channel %s having feed %s out of %s URLs.', channel, feed, len(urls))
        conditions = (Post.channel == channel) & (Post.feed == feed)
        unposted_urls = self._select_unposted(conditions, urls)
        log.info('Returning %s unposted URLs for channel %s having feed %s out of %s URLs.',
                 len(unposted_urls), channel, feed, len(urls))
        return unposted_urls

    def insert_posted(self, channel: str, feed: str, urls: List[str]) -> None:
        log.debug('Inserting %s URLs for channel %s having feed %s.', len(urls), channel, feed)
        data = ({'channel': channel, 'feed': feed, 'url': url} for url in urls)
        with self._write_lock, self._db.atomic():
            for batch in chunked(data, 100):  # Ref: https://www.sqlite.org/limits.html#max_variable_number
                Post.insert_many(batch).execute()
                # Note: Try prepending ".on_conflict_ignore()" before ".execute()" if needed.
        log.info('Inserted %s URLs for channel %s having feed %s.', len(urls), channel, feed)
