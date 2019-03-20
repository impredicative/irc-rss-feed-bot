import logging
import math
import queue
import subprocess
import threading
import time
from typing import Dict, List, Tuple

import bitlyshortener
import humanize
import miniirc

from . import config
from .db import Database
from .feed import Feed

log = logging.getLogger(__name__)


def _alert(irc: miniirc.IRC, msg: str, loglevel: int = logging.ERROR) -> None:
    log.log(loglevel, msg)
    irc.msg(config.INSTANCE['alerts_channel'], msg)


class Bot:
    CHANNEL_JOIN_EVENTS: Dict[str, threading.Event] = {}
    CHANNEL_LAST_MESSAGE_TIMES: Dict[str, float] = {}
    CHANNEL_QUEUES: Dict[str, queue.Queue] = {}

    def __init__(self) -> None:
        log.info('Initializing bot as: %s', subprocess.check_output('id', text=True).rstrip())
        instance = config.INSTANCE
        self._db = Database()
        self._url_shortener = bitlyshortener.Shortener(tokens=instance['tokens']['bitly'],
                                                       max_cache_size=config.BITLY_SHORTENER_MAX_CACHE_SIZE)

        # Setup miniirc
        log.debug('Initializing IRC client.')
        self._irc = miniirc.IRC(
            ip=instance['host'],
            port=instance['ssl_port'],
            nick=instance['nick'],
            channels=instance['feeds'],
            ssl=True,
            debug=False,
            ns_identity=f"{instance['nick']} {instance['nick_password']}",
            connect_modes=instance['mode'],
            quit_message='',
            )
        log.info('Initialized IRC client.')

        self._setup_channels()
        log.info('Alerts will be sent to %s.', instance['alerts_channel'])

    def _msg_channel(self, channel: str) -> None:
        log.debug('Channel messenger for %s is starting and is waiting to be notified of channel join.', channel)
        instance = config.INSTANCE
        channel_queue = Bot.CHANNEL_QUEUES[channel]
        db = self._db
        irc = self._irc
        message_format = config.MESSAGE_FORMAT
        min_channel_idle_time = config.MIN_CHANNEL_IDLE_TIME
        Bot.CHANNEL_JOIN_EVENTS[channel].wait()
        Bot.CHANNEL_JOIN_EVENTS[instance['alerts_channel']].wait()
        log.info('Channel messenger for %s has started.', channel)
        while True:
            feed = channel_queue.get()
            log.debug('Dequeued %s.', feed)

            try:
                if feed.postable_entries:  # Result gets cached.
                    while True:
                        time_elapsed_since_last_message = time.monotonic() - Bot.CHANNEL_LAST_MESSAGE_TIMES[channel]
                        sleep_time = max(0, min_channel_idle_time - time_elapsed_since_last_message)
                        if sleep_time == 0:
                            break
                        log.info('Waiting %s to post %s.', humanize.naturaldelta(sleep_time), feed)
                        time.sleep(sleep_time)

                    log.debug('Posting %s entries for %s.', len(feed.postable_entries), feed)
                    for entry in feed.postable_entries:
                        msg = message_format.format(feed=feed.name, title=entry.title, url=entry.post_url)
                        irc.msg(channel, msg)
                    log.info('Posted %s entries for %s.', len(feed.postable_entries), feed)

                if feed.unposted_entries:  # Note: feed.postable_entries is intentionally not used here.
                    db.insert_posted(channel, feed.name, [entry.long_url for entry in feed.unposted_entries])

            except Exception as exc:
                msg = f'Error processing {feed}: {exc}'
                _alert(irc, msg)

    def _read_feed(self, channel: str, feed_name: str) -> None:
        log.debug('Feed reader for feed %s of %s is starting and is waiting to be notified of channel join.',
                  feed_name, channel)
        instance = config.INSTANCE
        feed_config = instance['feeds'][channel][feed_name]
        channel_queue = Bot.CHANNEL_QUEUES[channel]
        feed_url = feed_config['url']
        feed_freq = feed_config.get('freq', config.FREQ_HOURS_DEFAULT) * 3600
        irc = self._irc
        db = self._db
        url_shortener = self._url_shortener
        query_time = -math.inf
        Bot.CHANNEL_JOIN_EVENTS[channel].wait()  # Optional.
        Bot.CHANNEL_JOIN_EVENTS[instance['alerts_channel']].wait()
        log.info('Feed reader for feed %s of %s has started.', feed_name, channel)
        while True:
            query_time = max(time.monotonic(), query_time + feed_freq)  # "max" is used in case of delay using "put".
            sleep_time = max(0., query_time - time.monotonic())
            if sleep_time != 0:
                log.info('Waiting %s to read feed %s of %s.', humanize.naturaldelta(sleep_time), feed_name, channel)
                time.sleep(sleep_time)

            try:
                log.debug('Reading feed %s of %s.', feed_name, channel)
                feed = Feed(channel=channel, name=feed_name, url=feed_url, db=db, url_shortener=url_shortener)
                log.info('Read %s with %s entries.', feed, len(feed.entries))
                channel_queue.put(feed)
                log.info('Queued %s with %s entries.', feed, len(feed.entries))
            except Exception as exc:
                msg = f'Error reading feed {feed_name} of {channel}: {exc}'
                _alert(irc, msg)

    def _setup_channels(self) -> None:
        instance = config.INSTANCE
        channels = instance['feeds']
        channels_str = ', '.join(channels)
        log.debug('Setting up threads and queues for %s channels (%s) and their feeds with %s currently active '
                  'threads.', len(channels), channels_str, threading.active_count())
        num_feeds = 0
        for channel, channel_config in channels.items():
            log.debug('Setting up threads and queue for %s.', channel)
            self.CHANNEL_JOIN_EVENTS[channel] = threading.Event()
            self.CHANNEL_QUEUES[channel] = queue.Queue(config.MAX_CHANNEL_QUEUE_SIZE)
            threading.Thread(target=self._msg_channel, name=f'ChannelMessenger-{channel}',
                             args=(channel,)).start()
            for feed in channel_config:
                threading.Thread(target=self._read_feed, name=f'FeedReader-{channel}-{feed}',
                                 args=(channel, feed)).start()
                num_feeds += 1
            log.debug('Finished setting up threads and queue for %s and its %s feeds with %s currently active threads.',
                     channel, len(channel_config), threading.active_count())
        log.info('Finished setting up threads and queues for %s channels (%s) and their %s feeds with %s currently '
                 'active threads.', len(channels), channels_str, num_feeds, threading.active_count())

# Ref: https://tools.ietf.org/html/rfc1459


@miniirc.Handler('JOIN')
def _handle_join(_irc: miniirc.IRC, hostmask: Tuple[str, str, str], args: List[str]) -> None:
    # Parse message
    log.debug('Handling channel join: hostmask=%s, args=%s', hostmask, args)
    user, ident, hostname = hostmask
    channel = args[0]

    # Ignore if not actionable
    if (user != config.INSTANCE['nick']) or (channel.casefold() not in config.INSTANCE['channels:casefold']):
        return

    # Update channel last message time
    Bot.CHANNEL_JOIN_EVENTS[channel].set()
    Bot.CHANNEL_LAST_MESSAGE_TIMES[channel] = time.monotonic()
    log.debug('Set the last message time for %s to %s.', channel, Bot.CHANNEL_LAST_MESSAGE_TIMES[channel])


@miniirc.Handler('PRIVMSG')
def _handle_privmsg(irc: miniirc.IRC, hostmask: Tuple[str, str, str], args: List[str]) -> None:
    # Parse message
    log.debug('Handling incoming message: hostmask=%s, args=%s', hostmask, args)
    channel = args[0]

    # Ignore if not actionable
    if channel.casefold() not in config.INSTANCE['channels:casefold']:
        assert channel.casefold() == config.INSTANCE['nick:casefold']
        user, ident, hostname = hostmask
        msg = args[-1]
        assert msg.startswith(':')
        msg = msg[1:]
        _alert(irc, f'Ignoring private message from {user} having ident {ident} and hostname {hostname}: {msg}',
               logging.WARNING)
        return

    # Update channel last message time
    Bot.CHANNEL_LAST_MESSAGE_TIMES[channel] = time.monotonic()
    log.debug('Updated the last message time for %s to %s.', channel, Bot.CHANNEL_LAST_MESSAGE_TIMES[channel])
