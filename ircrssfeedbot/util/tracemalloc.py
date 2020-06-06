"""tracemalloc utilities."""
import logging
import threading
import time
import tracemalloc
from typing import Final, List, Union

import psutil

from .humanize import humanize_bytes

log = logging.getLogger(__name__)

_INTERVAL: Final = 3600
_NUM_FRAMES: Final = 25
_NUM_STATS: Final = 20


def _printable_stats(stats: Union[List[tracemalloc.Statistic], List[tracemalloc.StatisticDiff]]) -> str:
    return "\n".join(f" #{i:0{len(str(_NUM_STATS))}}: {s}" for i, s in enumerate(stats[:_NUM_STATS], start=1))


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
            # stats_by_lineno = _printable_stats(snapshot.statistics(key_type="lineno"))
            stats_diff_by_filename = _printable_stats([d for d in snapshot.compare_to(snapshot_prev, key_type="filename") if d.size_diff > 0])
            # stats_diff_by_lineno = _printable_stats(snapshot.compare_to(snapshot_prev, key_type="filename"))
            del snapshot_prev
            log.info(
                f"Process is using {humanize_bytes(process.memory_info().rss)}. "
                f"Memory tracing is using {humanize_bytes(tracemalloc.get_tracemalloc_memory())} "
                f"and tracing {humanize_bytes(traced_current)}."
                f"\nThe current top memory allocations by filename are:\n{stats_by_filename}"
                # f"\nThe current top memory allocations by lineno are:\n{stats_by_lineno}"
                f"\nThe current top memory allocation diffs by filename are:\n{stats_diff_by_filename}"
                # f"\nThe current top memory allocation diffs by lineno are:\n{stats_diff_by_lineno}"
            )
            time.sleep(_INTERVAL)
