import logging
import subprocess

import miniirc

from . import config

log = logging.getLogger(__name__)


class Bot:
    def __init__(self) -> None:
        log.info('Initializing bot as: %s', subprocess.check_output('id', text=True).rstrip())

        instance = config.INSTANCE
        log.info('Alerts will be sent to %s.', instance['alerts_channel'])
        self._irc = miniirc.IRC(
            ip=instance['host'],
            port=instance['ssl_port'],
            nick=instance['nick'],
            channels=instance['feeds'],
            ssl=True,
            debug=True,
            ns_identity=f"{instance['nick']} {instance['nick_password']}",
            connect_modes=instance['mode'],
            quit_message='',
            )
        log.debug('Initialized bot.')
