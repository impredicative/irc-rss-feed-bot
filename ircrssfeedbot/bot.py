"""Bot."""
import datetime
import fnmatch
import logging
import os
import queue
import random
import subprocess
import threading
import time
from typing import Callable, Dict, List, Tuple

import bitlyshortener
import miniirc

from . import config, publishers
from .db import Database
from .feed import FeedReader
from .url import URLReader
from .util.datetime import timedelta_desc
from .util.humanize import humanize_bytes
from .util.list import ensure_list

log = logging.getLogger(__name__)


class Bot:
    """Bot."""

    CHANNEL_BUSY_LOCKS: Dict[str, threading.Lock] = {}
    CHANNEL_JOIN_EVENTS: Dict[str, threading.Event] = {}
    CHANNEL_LAST_INCOMING_MSG_TIMES: Dict[str, float] = {}
    CHANNEL_QUEUES: Dict[str, queue.Queue] = {}
    EXITCODE_QUEUE: queue.SimpleQueue = queue.SimpleQueue()
    FEED_GROUP_BARRIERS: Dict[str, threading.Barrier] = {}

    def __init__(self) -> None:
        log.info(f"Initializing bot as: {subprocess.check_output('id', text=True).rstrip()}")  # pylint: disable=unexpected-keyword-arg
        instance = config.INSTANCE
        self._active = True
        self._outgoing_msg_lock = threading.Lock()  # Used for rate limiting across multiple channels.
        self._db = Database()
        self._url_shortener = bitlyshortener.Shortener(
            tokens=[token.strip() for token in os.environ["BITLY_TOKENS"].strip().split(",")], max_cache_size=config.CACHE_MAXSIZE__BITLY_SHORTENER,
        )
        self._publishers = [getattr(getattr(publishers, p), "Publisher")() for p in dir(publishers) if ((not p.startswith("_")) and (p in (instance.get("publish") or {})))]

        # Setup miniirc
        log.debug("Initializing IRC client.")
        config.runtime.channel_topics = {}
        self._irc = miniirc.IRC(
            ip=instance["host"],
            port=instance["ssl_port"],
            nick=instance["nick"],
            channels=instance["feeds"],
            ssl=True,
            debug=False,
            ns_identity=(instance["nick"], os.environ["IRC_PASSWORD"]),
            connect_modes=instance.get("mode"),
            quit_message="",
            ping_interval=30,
        )
        log.info("Initialized IRC client.")
        self._setup_alerter()
        self._setup_channels()
        self._log_config()
        self._exit()  # Blocks.

    def _exit(self) -> None:
        code = self.EXITCODE_QUEUE.get()
        self._active = False
        log.info(f"Initiated graceful exit with code {code}.")
        alerter = config.runtime.alert

        # Acquire all channel busy locks
        for channel in config.INSTANCE["feeds"]:
            channel_lock = self.CHANNEL_BUSY_LOCKS[channel]
            if not channel_lock.acquire(blocking=False):
                alerter(f"Draining {channel}.", log.info)
                channel_lock.acquire()

        # Exit
        log.info(f"Gracefully exiting with code {code}.")
        self._irc.disconnect(auto_reconnect=False)
        # Note: sys.exit doesn't exit the application as it doesn't exit all threads.
        os._exit(code)  # pylint: disable=protected-access

    @staticmethod
    def _log_config() -> None:
        diskcache_size = sum(f.stat().st_size for f in config.DISKCACHE_PATH.glob("**/*") if f.is_file())
        log.info(f"Disk cache path is {config.DISKCACHE_PATH} and its current size is {humanize_bytes(diskcache_size)}.")
        log.info(f"Alerts will be sent to {config.INSTANCE['alerts_channel']}.")
        if admin := config.INSTANCE.get("admin"):
            log.info(f"Administrative commands will be accepted as private messages or directed public messages from {admin}.")

    def _msg_channel(self, channel: str) -> None:  # pylint: disable=too-many-branches,too-many-locals,too-many-statements
        log.debug(f"Channel messenger for {channel} is starting and is waiting to be notified of channel join.")
        instance = config.INSTANCE
        alerter = config.runtime.alert
        outgoing_msg_lock = self._outgoing_msg_lock
        channel_busy_lock = self.CHANNEL_BUSY_LOCKS[channel]
        channel_queue = self.CHANNEL_QUEUES[channel]
        irc = self._irc
        self.CHANNEL_JOIN_EVENTS[channel].wait()
        self.CHANNEL_JOIN_EVENTS[instance["alerts_channel"]].wait()
        log.info(f"Channel messenger for {channel} has started.")
        while self._active:  # pylint: disable=too-many-nested-blocks
            feed = channel_queue.get()
            log.debug(f"Dequeued {feed}.")
            min_channel_idle_time = feed.reader.min_channel_idle_time
            log.debug(f"The minimum required channel idle time for {feed} is {timedelta_desc(min_channel_idle_time)}.")
            try:
                if not feed.is_postable:
                    feed.mark_posted()  # channel_busy_lock is not acquired here because there are no posts.
                else:
                    try:
                        while True:
                            if not outgoing_msg_lock.acquire(blocking=False):
                                log.info(f"Waiting to acquire outgoing message lock to post {feed}.")
                                outgoing_msg_lock.acquire()
                            last_incoming_msg_time = Bot.CHANNEL_LAST_INCOMING_MSG_TIMES[channel]
                            time_elapsed_since_last_ic_msg = time.monotonic() - last_incoming_msg_time
                            sleep_time = max(0, min_channel_idle_time - time_elapsed_since_last_ic_msg)
                            if sleep_time == 0:
                                break  # Lock will be released later after posting messages.
                            outgoing_msg_lock.release()  # Releasing lock before sleeping.
                            log.info(f"Will wait {timedelta_desc(sleep_time)} for channel inactivity to post {feed}.")
                            time.sleep(sleep_time)

                        log.debug("Checking IRC client connection state.")
                        if not irc.connected:  # In case of netsplit.
                            log.warning(f"Will wait for IRC client to connect so as to post {feed}.")
                            disconnect_time = time.monotonic()
                            while not irc.connected:
                                time.sleep(5)
                            disconnection_time = time.monotonic() - disconnect_time
                            log.info(f"IRC client is connected after waiting {timedelta_desc(disconnection_time)}.")

                        with channel_busy_lock:
                            feed.post()
                            feed.mark_posted()
                            feed.publish()
                    finally:
                        outgoing_msg_lock.release()
            except Exception as exc:  # pylint: disable=broad-except
                msg = f"Error processing {feed}: {exc}"
                alerter(msg)
            channel_queue.task_done()
        log.debug(f"Channel messenger for {channel} has stopped.")

    def _read_feed(self, channel: str, feed_name: str) -> None:  # pylint: disable=too-many-locals,too-many-statements
        log.debug(f"Feed reader for feed {feed_name} of {channel} is starting and is waiting to be notified of channel join.")
        instance = config.INSTANCE
        alerter = config.runtime.alert
        feed_config = instance["feeds"][channel][feed_name]

        channel_queue = Bot.CHANNEL_QUEUES[channel]
        feed_period_avg = max(config.PERIOD_HOURS_MIN, feed_config.get("period", config.PERIOD_HOURS_DEFAULT)) * 3600
        feed_period_min = feed_period_avg * (1 - config.PERIOD_RANDOM_PERCENT / 100)
        feed_period_max = feed_period_avg * (1 + config.PERIOD_RANDOM_PERCENT / 100)
        num_consecutive_failures = 0

        feed_reader = FeedReader(
            channel=channel,
            name=feed_name,
            irc=self._irc,
            db=self._db,
            url_reader=URLReader(max_cache_age=feed_period_min / 2),
            url_shortener=self._url_shortener,
            publishers=self._publishers,
        )
        log.debug(f"Feed reader for feed {feed_name} of {channel} has initialized and is waiting to be notified of channel join.")

        query_time = time.monotonic() - (feed_period_avg / 2)  # Delays first read by half of feed period.
        self.CHANNEL_JOIN_EVENTS[channel].wait()
        self.CHANNEL_JOIN_EVENTS[instance["alerts_channel"]].wait()
        log.debug(f"Feed reader for feed {feed_name} of {channel} has started.")
        while self._active:
            feed_period = random.uniform(feed_period_min, feed_period_max)
            query_time = max(time.monotonic(), query_time + feed_period)  # "max" is used in case of wait using "put".
            sleep_time = max(0.0, query_time - time.monotonic())
            if sleep_time != 0:
                log.debug(f"Will wait {timedelta_desc(sleep_time)} to read feed {feed_name} of {channel}.")
                time.sleep(sleep_time)

            try:
                # Read feed
                log.debug(f"Retrieving feed {feed_name} of {channel}.")
                feed = feed_reader.read()
                log.info(f"Retrieved in {feed.read_time_used:.1f}s the {feed} with {len(feed.entries)} approved entries via {feed.read_approach}.")

                # Wait for other feeds in group
                if feed_config.get("group"):
                    feed_group = feed_config["group"]
                    group_barrier = Bot.FEED_GROUP_BARRIERS[feed_group]
                    num_other = group_barrier.parties - 1
                    num_pending = num_other - group_barrier.n_waiting
                    if num_pending > 0:  # This is not thread-safe but that's okay for logging.
                        log.debug(f"Will wait for {num_pending} of {num_other} other feeds in group {feed_group} to also be read before queuing {feed}.")
                    group_barrier.wait()
                    log.debug(f"Finished waiting for other feeds in group {feed_group} to also be read before queuing {feed}.")

                # Queue feed
                # FIXME: This doesn't work correctly when `feed_reader.min_channel_idle_time == 0`.
                try:
                    channel_queue.put_nowait(feed)
                except queue.Full:
                    msg = (
                        f"The {feed} cannot currently be queued for being posted to {channel}, "
                        f"perhaps because the channel has been too active. "
                        f"The queue for this channel is full. The feed will be put in the queue in blocking mode."
                    )
                    alerter(msg, log.warning)
                    channel_queue.put(feed)
                log.debug(f"Queued {feed}.")
            except Exception as exc:  # pylint: disable=broad-except
                num_consecutive_failures += 1
                msg = "Failed"
                if num_consecutive_failures > 1:
                    msg += f" {num_consecutive_failures} consecutive times"
                msg += f" while reading or processing feed {feed_name} of {channel}: {exc}"
                if feed_config.get("alerts", {}).get("read", True) and (num_consecutive_failures >= config.MIN_CONSECUTIVE_FEED_FAILURES_FOR_ALERT):
                    alerter(msg)
                    alerter("Either check the feed configuration, or wait for its next successful read, or set `alerts/read` to `false` for it.")
                else:
                    log.error(msg)  # Not logging as exception.
            else:
                if instance.get("once"):
                    log.warning(f"Discontinuing reader for {feed}.")
                    return
                del feed
                num_consecutive_failures = 0
        log.debug(f"Feed reader for feed {feed_name} of {channel} has stopped.")

    def _setup_alerter(self) -> None:
        def alerter(msg: str, logger: Callable[[str], None] = log.exception) -> None:
            logger(msg)
            self._irc.msg(config.INSTANCE["alerts_channel"], msg)

        config.runtime.alert = alerter

    def _setup_channels(self) -> None:  # pylint: disable=too-many-locals
        instance = config.INSTANCE
        channels = instance["feeds"]
        channels_str = ", ".join(channels)
        log.debug(
            "Setting up threads and queues for %s channels (%s) and their feeds with %s currently active " "threads.", len(channels), channels_str, threading.active_count(),
        )
        num_feeds_setup = 0
        num_urls = 0
        num_reads_daily = 0
        barriers_parties: Dict[str, int] = {}
        for channel, channel_config in channels.items():
            log.debug("Setting up threads and queue for %s.", channel)
            num_channel_feeds = len(channel_config)
            self.CHANNEL_BUSY_LOCKS[channel] = threading.Lock()
            self.CHANNEL_JOIN_EVENTS[channel] = threading.Event()
            self.CHANNEL_QUEUES[channel] = queue.Queue(maxsize=num_channel_feeds * 2)
            threading.Thread(target=self._msg_channel, name=f"ChannelMessenger-{channel}", args=(channel,)).start()
            for feed, feed_config in channel_config.items():
                threading.Thread(target=self._read_feed, name=f"FeedReader-{channel}-{feed}", args=(channel, feed)).start()
                num_feed_urls = len(ensure_list(feed_config["url"]))
                num_urls += num_feed_urls
                feed_period = max(config.PERIOD_HOURS_MIN, feed_config.get("period", config.PERIOD_HOURS_DEFAULT))
                num_feed_reads_daily = (24 / feed_period) * num_feed_urls
                num_reads_daily += num_feed_reads_daily
                if feed_config.get("group"):
                    group = feed_config["group"]
                    barriers_parties[group] = barriers_parties.get(group, 0) + 1
                num_feeds_setup += 1
            log.debug(
                "Finished setting up threads and queue for %s and its %s feeds with %s currently active threads.", channel, num_channel_feeds, threading.active_count(),
            )
        for barrier, parties in barriers_parties.items():
            self.FEED_GROUP_BARRIERS[barrier] = threading.Barrier(parties)

        # Log counts
        log.info(
            "Finished setting up %s channels (%s) and their %s feeds having %s URLs with %s currently active threads.",
            len(channels),
            channels_str,
            num_feeds_setup,
            num_urls,
            threading.active_count(),
        )
        read_period_msg = f"Ignoring any caches and crawls, {round(num_reads_daily):,} URL reads are expected daily."
        if num_reads_daily:
            avg_read_period = timedelta_desc(datetime.timedelta(days=1) / num_reads_daily)
            read_period_msg += f" That's once every {avg_read_period} on an average."
        log.info(read_period_msg)


# Refs: https://tools.ietf.org/html/rfc1459 https://modern.ircdocs.horse


@miniirc.Handler(900, colon=False)
def _handle_900_loggedin(irc: miniirc.IRC, hostmask: Tuple[str, str, str], args: List[str]) -> None:
    # Parse message
    log.debug("Handling RPL_LOGGEDIN (900): hostmask=%s, args=%s", hostmask, args)
    runtime_config = config.runtime
    runtime_config.identity = identity = args[1]
    nick = identity.split("!", 1)[0]
    runtime_config.nick_casefold = nick_casefold = nick.casefold()
    log.info("The client identity as <nick>!<user>@<host> is %s.", identity)
    if nick_casefold != config.INSTANCE["nick:casefold"]:
        runtime_config.alert(
            f"The client nick was configured to be {config.INSTANCE['nick']} but it is {nick}. " "The configured nick will be regained.", log.warning,
        )
        irc.msg("nickserv", "REGAIN", config.INSTANCE["nick"], os.environ["IRC_PASSWORD"])


@miniirc.Handler("NICK", colon=False)
def _handle_nick(_irc: miniirc.IRC, hostmask: Tuple[str, str, str], args: List[str]) -> None:
    log.debug("Handling nick change: hostmask=%s, args=%s", hostmask, args)
    old_nick, _ident, _hostname = hostmask
    runtime_config = config.runtime

    # Ignore if not actionable
    if old_nick.casefold() != runtime_config.nick_casefold:
        return

    # Update identity, possibly after a nick regain
    new_nick = args[0]
    runtime_config.identity = identity = runtime_config.identity.replace(old_nick, new_nick, 1)
    runtime_config.nick_casefold = new_nick.casefold()
    runtime_config.alert(f"The updated client identity as <nick>!<user>@<host> is inferred to be {identity}.", log.info)


@miniirc.Handler("JOIN", colon=False)
def _handle_join(_irc: miniirc.IRC, hostmask: Tuple[str, str, str], args: List[str]) -> None:
    # Parse message
    log.debug("Handling channel join: hostmask=%s, args=%s", hostmask, args)
    user, _ident, _hostname = hostmask
    channel = args[0]

    # Ignore if not actionable
    if (user.casefold() != config.runtime.nick_casefold) or (channel.casefold() not in config.INSTANCE["channels:casefold"]):
        return

    # Update channel last message time
    Bot.CHANNEL_JOIN_EVENTS[channel].set()
    Bot.CHANNEL_LAST_INCOMING_MSG_TIMES[channel] = msg_time = time.monotonic()
    log.debug(f"Set the last incoming message time for {channel} to {msg_time}.")


@miniirc.Handler("PRIVMSG", colon=False)
def _handle_privmsg(_irc: miniirc.IRC, hostmask: Tuple[str, str, str], args: List[str]) -> None:
    # Parse message
    log.debug("Handling incoming message: hostmask=%s, args=%s", hostmask, args)
    channel = args[0]
    user, ident, hostname = hostmask
    msg = args[-1]
    is_channel_msg = channel.casefold() in config.INSTANCE["channels:casefold"]
    is_private_msg = channel.casefold() == config.runtime.nick_casefold
    sender = f"{user}!{ident}@{hostname}"
    is_command = (
        (admin := config.INSTANCE.get("admin"))
        and fnmatch.fnmatch(sender, admin)  # pylint: disable=used-before-assignment
        and (is_private_msg or (is_channel_msg and msg.strip().casefold().startswith(f"{config.runtime.nick_casefold}:")))
    )

    # Check assumptions for safety
    assert is_channel_msg != is_private_msg  # Ref: https://stackoverflow.com/a/433161/

    # Update channel last message time
    if is_channel_msg:
        Bot.CHANNEL_LAST_INCOMING_MSG_TIMES[channel] = msg_time = time.monotonic()
        log.debug("Updated the last incoming message time for %s to %s.", channel, msg_time)

    # Alert if non-command PM
    if is_private_msg and (not is_command) and (msg != "\x01VERSION\x01"):
        # Ignoring private message from freenode-connect having ident frigg and hostname freenode/utility-bot/frigg: VERSION
        config.runtime.alert(f"Ignoring private message from {sender}: {msg}", log.warning)

    # Execute if command
    if is_command and (command := (msg.strip() if is_private_msg else msg.split(":", 1)[1].strip())):
        log.info(f"Received command from {sender}: {command}")
        if command == "exit":
            Bot.EXITCODE_QUEUE.put(0)
        elif command == "fail":
            Bot.EXITCODE_QUEUE.put(1)


@miniirc.Handler(332, colon=False)
def _handle_332_notice(_irc: miniirc.IRC, hostmask: Tuple[str, str, str], args: List[str]) -> None:
    log.debug("Received initial topic: hostmask=%s args=%s", hostmask, args)
    _nick, channel, topic = args

    # Store topic
    config.runtime.channel_topics[channel] = topic
    log.debug(f"Received initial topic of {channel}: {topic}")


@miniirc.Handler("TOPIC", colon=False)
def _handle_topic(_irc: miniirc.IRC, hostmask: Tuple[str, str, str], args: List[str]) -> None:
    log.debug("Received updated topic: hostmask=%s, args=%s", hostmask, args)
    channel, topic = args
    channel_topics = config.runtime.channel_topics

    # Store topic if changed
    if topic != channel_topics.get(channel):
        channel_topics[channel] = topic
        log.debug(f"Received updated topic of {channel}: {topic}")
