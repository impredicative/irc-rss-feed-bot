from typing import List, Optional

from ircrssfeedbot import config

import peewee

DATABASE = peewee.SqliteDatabase(None)


class Post(peewee.Model):
    channel = peewee.CharField(64, null=False, verbose_name='channel name')
    feed = peewee.CharField(32, null=False, verbose_name='feed name')
    post = peewee.CharField(12, null=False, verbose_name='post ID')

    class Meta:
        database = DATABASE
        primary_key = peewee.CompositeKey('channel', 'feed', 'post')
        indexes = (
            # (('channel', 'feed', 'post'), True),
            (('channel', 'post'), False),
        )  # True means unique.


class Database:
    def __init__(self):
        db_path = '/tmp/sq.db'  # config.INSTANCE['dir'] / config.DB_FILENAME
        DATABASE.init(db_path)
        self._db = DATABASE
        self._db.create_tables([Post])

    def find_missing(self, channel: str, feed: Optional[str], posts: List[str]) -> List[str]:
        if feed:
            return Post.get(Post.channel == channel, Post.feed == feed, Post.post not in posts)
        return Post.get(Post.channel == channel, Post.post not in posts)

    def insert(self, channel: str, feed: str, posts: List[str]) -> None:
        pass
