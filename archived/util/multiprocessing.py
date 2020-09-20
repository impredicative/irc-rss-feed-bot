"""multiprocessing utilities."""

# Ref: https://stackoverflow.com/a/53180921/

import multiprocessing.pool
from typing import Any


class _NoDaemonProcess(multiprocessing.Process):
    @property  # type: ignore
    def daemon(self):
        return False

    @daemon.setter
    def daemon(self, value):
        pass


class _NoDaemonContext(type(multiprocessing.get_context())):  # type: ignore
    Process = _NoDaemonProcess


class NestablePool(multiprocessing.pool.Pool):  # pylint: disable=abstract-method
    """Nestable multiprocessing pool."""

    def __init__(self, *args: Any, **kwargs: Any):
        kwargs["context"] = _NoDaemonContext()
        super().__init__(*args, **kwargs)
