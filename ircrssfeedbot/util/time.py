"""time utilities."""
import time


class Throttle:
    """Provide a context manager which uses at least the given number of seconds."""

    class Break(Exception):
        """Raise this exception to disable the requirement of using at least the given number of seconds."""

    def __init__(self, seconds: int):
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
