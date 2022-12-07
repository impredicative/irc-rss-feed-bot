"""time utilities."""
import time
from typing import Union


def sleep_long(secs: int | float) -> None:
    """Sleep for up to an extended number of seconds, beyond what `time.sleep` may natively support."""
    # Ref: https://stackoverflow.com/a/74712113/
    max_secs = 9217972800  # Ref: datetime.timedelta(days=292.3 * 365).total_seconds()
    if secs <= max_secs:
        time.sleep(secs)
    else:
        while secs > 0:
            sleep_time = min(secs, max_secs)
            time.sleep(sleep_time)
            secs -= max_secs


class Throttle:
    """Provide a context manager which uses at least the given number of seconds."""

    class Break(Exception):
        """Raise this exception to disable the requirement of using at least the given number of seconds."""

    def __init__(self, seconds: Union[int, float]):
        self._seconds = seconds

    def __enter__(self):
        self._start_time = time.monotonic()  # pylint: disable=attribute-defined-outside-init
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type == self.Break:
            return True
        sleep_time = max(0.0, self._start_time + self._seconds - time.monotonic())
        time.sleep(sleep_time)
        return None
