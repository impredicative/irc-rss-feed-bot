from typing import List

from ircrssfeedbot import config


class Database:
    def __init__(self):
        self._path = config.INSTANCE['dir'] / config.DB_FILENAME

    def antiselect(self, channel: str, post_ids: List[str]) -> List[str]:
        pass

    def insert(self, channel: str, post_ids: List[str]) -> None:
        pass
