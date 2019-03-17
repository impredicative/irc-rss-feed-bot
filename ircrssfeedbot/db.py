import logging
from pathlib import Path
import threading
from typing import List, Optional

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
        posts = Post.select(Post.post).where(conditions).limit(1).tuples()
        return not posts

    @staticmethod
    def select_missing(channel: str, feed: Optional[str], posts: List[str]) -> List[str]:
        if feed:
            conditions = (Post.channel == channel) & (Post.feed == feed) & Post.post.not_in(posts)
        else:
            conditions = (Post.channel == channel) & Post.post.not_in(posts)
        missing = Post.select(Post.post).where(conditions).tuples().iterator()
        missing_ordered = [post for post in posts if post in missing]  # Sort by original order.
        assert missing == missing_ordered  # TODO: Remove assertion after thoroughly confirming it.
        return missing_ordered

    def insert(self, channel: str, feed: str, posts: List[str]) -> None:
        data = ({'channel': channel, 'feed': feed, 'post': post} for post in posts)
        with self._write_lock, self._db.atomic():
            for batch in chunked(data, 100):
                Post.insert_many(batch).execute()
                # Note: Try prepending ".on_conflict_ignore()" before ".execute()" if needed.
