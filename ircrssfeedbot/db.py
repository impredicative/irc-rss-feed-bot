from ircrssfeedbot import config


class Database:
    def __init__(self):
        self._path = config.INSTANCE['dir'] / config.DB_FILENAME

    def select(self, channel, long_urls):
        pass

    def insert(self, channel, long_urls):
        pass
