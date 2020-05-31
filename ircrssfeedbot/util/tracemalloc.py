"""tracemalloc utilities."""
import logging
import threading
import time
import tracemalloc
from typing import List, Union

import psutil

from ircrssfeedbot.util.humanize import humanize_bytes

log = logging.getLogger(__name__)

_INTERVAL = 30  # 3600
_NUM_FRAMES = 25
_NUM_STATS = 5


def _printable_stats(stats: Union[List[tracemalloc.Statistic], List[tracemalloc.StatisticDiff]]) -> str:
    return "\n".join(f"#{i}: {s}" for i, s in enumerate(stats[:_NUM_STATS], start=1))


class TraceMalloc(threading.Thread):
    """Trace memory usage for help with identifying any memory leaks."""

    def __init__(self) -> None:
        super().__init__(name=self.__class__.__name__)

    def run(self):
        process = psutil.Process()
        tracemalloc.start(_NUM_FRAMES)
        log.info(f"Started tracing memory allocations for {_NUM_FRAMES} frames.")

        snapshot = tracemalloc.take_snapshot()
        while True:
            snapshot_prev = snapshot
            snapshot = tracemalloc.take_snapshot()
            traced_current, _traced_peak = tracemalloc.get_traced_memory()
            stats_by_filename = _printable_stats(snapshot.statistics(key_type="filename"))
            stats_by_lineno = _printable_stats(snapshot.statistics(key_type="lineno"))
            stats_diff_by_filename = _printable_stats(snapshot.compare_to(snapshot_prev, key_type="filename"))
            stats_diff_by_lineno = _printable_stats(snapshot.compare_to(snapshot_prev, key_type="filename"))
            del snapshot_prev
            log.info(
                f"Process is using {humanize_bytes(process.memory_info().rss)}. "
                f"Memory tracing is using {humanize_bytes(tracemalloc.get_tracemalloc_memory())} "
                f"and tracing {humanize_bytes(traced_current)}."
                f"\nThe current top memory usage stats by filename are:\n{stats_by_filename}"
                f"\nThe current top memory usage stats by lineno are:\n{stats_by_lineno}"
                f"\nThe current top memory usage stats diff by filename are:\n{stats_diff_by_filename}"
                f"\nThe current top memory usage stats diff by lineno are:\n{stats_diff_by_lineno}"
            )
            time.sleep(_INTERVAL)
