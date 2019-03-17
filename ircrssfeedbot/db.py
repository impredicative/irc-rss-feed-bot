import logging
from pathlib import Path
import threading
from typing import List, Union

import peewee
from peewee import chunked

from . import config
from .util.humanize import humanize_bytes

log = logging.getLogger(__name__)
_DATABASE = peewee.SqliteDatabase(None)


class Post(peewee.Model):
    channel = peewee.CharField(64, null=False, verbose_name='channel name')
    feed = peewee.CharField(32, null=False, verbose_name='feed name')
    post = peewee.CharField(10, null=False, verbose_name='post ID')

    class Meta:
        database = _DATABASE
        legacy_table_names = False  # This will become a default in peewee>=4
        primary_key = peewee.CompositeKey('channel', 'feed', 'post')
        indexes = (
            # (('channel', 'feed', 'post'), True),
            (('channel', 'post'), False),
        )  # True means unique.


class Database:
    def __init__(self):
        log.debug('Initializing database.')
        db_path = Path('/tmp/sq.db')  # TODO: Use config.INSTANCE['dir'] / config.DB_FILENAME
        _DATABASE.init(db_path)
        self._db = _DATABASE
        self._db.create_tables([Post])
        self._write_lock = threading.Lock()
        log.info('Initialized database having path %s and size %s.', db_path, humanize_bytes(db_path.stat().st_size))

    def is_new_feed(self, channel: str, feed: str) -> bool:
        conditions = (Post.channel == channel) & (Post.feed == feed)
        return not Post.select(Post.post).where(conditions).limit(1)

    @staticmethod
    def select_missing(channel: str, feed: Union[str, None], posts: List[str]) -> List[str]:
        log.debug('Requesting missing posts for channel %s having feed %s out of %s posts.', channel, feed, len(posts))
        present = []
        for posts_batch in chunked(posts, 100):  # Ref: https://www.sqlite.org/limits.html#max_variable_number
            if feed:
                conditions = (Post.channel == channel) & (Post.feed == feed) & Post.post.in_(posts_batch)
            else:
                conditions = (Post.channel == channel) & Post.post.in_(posts_batch)
            present_batch = Post.select(Post.post).where(conditions).tuples().iterator()
            present_batch = [post[0] for post in present_batch]
            present.extend(present_batch)
        missing = [post for post in posts if post not in present]  # This also implicitly avoids returning duplicates.
        log.info('Returning %s missing posts for channel %s having feed %s out of %s posts.',
                 len(missing), channel, feed, len(posts))
        return missing

    def insert(self, channel: str, feed: str, posts: List[str]) -> None:
        log.debug('Inserting %s posts for channel %s having feed %s.', len(posts), channel, feed)
        data = ({'channel': channel, 'feed': feed, 'post': post} for post in posts)
        with self._write_lock, self._db.atomic():
            for batch in chunked(data, 100):  # Ref: https://www.sqlite.org/limits.html#max_variable_number
                Post.insert_many(batch).execute()
                # Note: Try prepending ".on_conflict_ignore()" before ".execute()" if needed.
        log.info('Inserted %s posts for channel %s having feed %s.', len(posts), channel, feed)

