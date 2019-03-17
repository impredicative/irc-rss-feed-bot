import logging
import subprocess

import miniirc

from . import config

log = logging.getLogger(__name__)


class Bot:
    def __init__(self) -> None:
        log.info('Initializing bot as: %s', subprocess.check_output('id', text=True).rstrip())

    def serve(self) -> None:
        pass
