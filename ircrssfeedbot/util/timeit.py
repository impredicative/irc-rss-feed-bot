"""timeit utilities."""

import datetime
import timeit


class Timer:
    """Measure time used."""

    # Ref: https://stackoverflow.com/a/57931660/
    def __init__(self, round_ndigits: int = 0):
        self._round_ndigits = round_ndigits
        self._start_time = timeit.default_timer()

    def __call__(self) -> float:
        return timeit.default_timer() - self._start_time

    def __str__(self) -> str:
        return str(datetime.timedelta(seconds=round(self(), self._round_ndigits)))
