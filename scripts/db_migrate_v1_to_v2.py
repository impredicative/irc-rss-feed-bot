import logging
from pathlib import Path

import peewee

from ircrssfeedbot import config
from ircrssfeedbot.util.humanize import humanize_bytes
from ircrssfeedbot.util.hashlib import Int8Hash

# Customize:
DB_PATH_V1 = Path('/home/devuser/Documents/db-backups/posts.v1.db')
DB_PATH_V2 = Path('/home/devuser/Documents/db-backups/posts.v2.db')

config.configure_logging()
log = logging.getLogger(__name__)
_DATABASE_V1 = peewee.SqliteDatabase(None)
_DATABASE_V2 = peewee.SqliteDatabase(None)


class ModelV1:
    class Post(peewee.Model):
        channel = peewee.CharField(64, null=False, verbose_name='channel name')
        feed = peewee.CharField(32, null=False, verbose_name='feed name')
        url = peewee.CharField(512, null=False, verbose_name='long URL')
        # Note: The reason for using the "long URL" instead of the "short URL path" is that the latter can change
        # surprisingly if the array of Bitly tokens is changed in any way, leading to deduplication errors.

        class Meta:
            database = _DATABASE_V1
            legacy_table_names = False  # This will become a default in peewee>=4
            primary_key = peewee.CompositeKey('channel', 'feed', 'url')
            indexes = (
                # (('channel', 'feed', 'url'), True),  # Not needed per EXPLAIN QUERY PLAN due to sqlite_autoindex_post_1.
                (('channel', 'url'), False),
            )  # True means unique.


class ModelV2:
    class Post(peewee.Model):
        channel = peewee.BigIntegerField(null=False, verbose_name='channel name')
        feed = peewee.BigIntegerField(null=False, verbose_name='feed name')
        url = peewee.BigIntegerField(null=False, verbose_name='long URL')
        # Note: The reason for using the "long URL" instead of the "short URL path" is that the latter can change
        # surprisingly if the array of Bitly tokens is changed in any way, leading to deduplication errors.

        class Meta:
            database = _DATABASE_V2
            legacy_table_names = False  # This will become a default in peewee>=4
            primary_key = peewee.CompositeKey('channel', 'feed', 'url')
            indexes = (
                # (('channel', 'feed', 'url'), True),  # Not needed per EXPLAIN QUERY PLAN due to sqlite_autoindex_post_1.
                (('channel', 'url'), False),
            )  # True means unique.


class DatabaseV1:
    def __init__(self) -> None:
        log.info('Initializing v1 database.')
        _DATABASE_V1.init(DB_PATH_V1)  # If facing threading issues, consider https://stackoverflow.com/a/39024742/
        self._db = _DATABASE_V1
        self._db.create_tables([ModelV1.Post])
        log.info('Initialized v1 database having path %s.', DB_PATH_V1)
        self.optimize()

    def optimize(self):
        log.info('Vacuuming v1 database having pre-vacuum size %s.', humanize_bytes(DB_PATH_V1.stat().st_size))
        self._db.execute_sql('VACUUM;')
        log.info('Vacuumed v1 database having post-vacuum size %s.', humanize_bytes(DB_PATH_V1.stat().st_size))

        log.info('Analyzing v1 database.')
        self._db.execute_sql('ANALYZE;')
        log.info('Analyzed v1 database.')

    def select(self):
        page_num = 1
        while True:
            rows = list(ModelV1.Post.select().paginate(page_num, 1000).dicts().iterator())
            if rows:
                log.info('Yielding %s rows for page %s.', len(rows), page_num)
                yield rows
                page_num += 1
            else:
                log.warning('No rows exist for page %s.', page_num)
                break


class DatabaseV2:
    def __init__(self) -> None:
        log.info('Initializing v2 database.')
        try:
            DB_PATH_V2.unlink()
        except FileNotFoundError:
            pass
        else:
            log.info('Deleted preexisting v2 database having path %s.', DB_PATH_V2)
        _DATABASE_V2.init(DB_PATH_V2)  # If facing threading issues, consider https://stackoverflow.com/a/39024742/
        self._db = _DATABASE_V2
        self._db.create_tables([ModelV2.Post])
        log.info('Initialized v2 database having path %s.', DB_PATH_V2)
        # self.optimize()

    def optimize(self):
        log.info('Vacuuming v2 database having pre-vacuum size %s.', humanize_bytes(DB_PATH_V2.stat().st_size))
        self._db.execute_sql('VACUUM;')
        log.info('Vacuumed v2 database having post-vacuum size %s.', humanize_bytes(DB_PATH_V2.stat().st_size))

        log.info('Analyzing v2 database.')
        self._db.execute_sql('ANALYZE;')
        log.info('Analyzed v2 database.')

    def insert(self, rows):
        with self._db.atomic():
            ModelV2.Post.insert_many(rows).execute()
        log.info('Inserted %s rows.', len(rows))


def migrate():
    db1 = DatabaseV1()
    db2 = DatabaseV2()

    for rows in db1.select():
        for row in rows:
            for key in row:
                row[key] = Int8Hash.as_int(row[key])
        db2.insert(rows)

    db2.optimize()


if __name__ == '__main__':
    migrate()
