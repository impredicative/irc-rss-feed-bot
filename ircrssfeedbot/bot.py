import logging
import subprocess
import threading
from time import monotonic
from typing import List, Tuple

import miniirc

from . import config

log = logging.getLogger(__name__)

_CHANNEL_LAST_MESSAGE_TIMES = {}


def _alert(irc: miniirc.IRC, msg: str, loglevel: int = logging.ERROR) -> None:
    log.log(loglevel, msg)
    irc.msg(config.INSTANCE['alerts_channel'], msg)


class Bot:
    def __init__(self) -> None:
        log.info('Initializing bot as: %s', subprocess.check_output('id', text=True).rstrip())
        instance = config.INSTANCE

        # Setup channels
        channels = instance['feeds']
        channels_str = ', '.join(channels)
        log.debug('Setting up threads and queues for %s channels (%s) with %s currently active threads.',
                  len(channels), channels_str, threading.active_count())
        for channel, channel_config in channels.items():
            log.debug('Setting up threads and queue for %s.', channel)

            log.debug('Finished setting up threads and queue for %s with %s currently active threads.',
                     channel, threading.active_count())
        log.info('Finished setting up threads and queues for %s channels (%s) with %s currently active threads.',
                 len(channels), channels_str, threading.active_count())

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

        log.info('Alerts will be sent to %s.', instance['alerts_channel'])

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
    _CHANNEL_LAST_MESSAGE_TIMES[channel] = monotonic()
    log.debug('Set the last message time for %s to %s.', channel, _CHANNEL_LAST_MESSAGE_TIMES[channel])


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
    _CHANNEL_LAST_MESSAGE_TIMES[channel] = monotonic()
    log.debug('Updated the last message time for %s to %s.', channel, _CHANNEL_LAST_MESSAGE_TIMES[channel])
