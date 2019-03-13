import threading
from typing import List

import dataset

from ircrssfeedbot import config


class Database:
    def __init__(self):
        db_path = config.INSTANCE['dir'] / config.DB_FILENAME
        db = dataset.connect(f'sqlite:///{db_path}?check_same_thread=False')  # Ref: https://stackoverflow.com/a/43538853/
        self._posts = db['posts']
        self._write_lock = threading.Lock()

    def find_missing(self, channel: str, post_ids: List[str]) -> List[str]:
        posted = {post['post_id'] for post in self._posts.find(channel=channel, id=post_ids)}
        unposted = [post_id for post_id in post_ids if post_id not in posted]
        return unposted

    def insert(self, channel: str, post_ids: List[str]) -> None:
        posts = [{'channel': channel, 'post_id': post_id} for post_id in post_ids]
        with self._write_lock:
            # Note: A lock is used due to use of check_same_thread=True in the connection string.
            # Ref: https://docs.python.org/3/library/sqlite3.html#sqlite3.connect
            self._posts.insert_many(posts)
