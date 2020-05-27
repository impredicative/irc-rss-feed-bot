"""tracemalloc utilities."""
import logging
import threading
import time
import tracemalloc

import psutil

from ircrssfeedbot.util.humanize import humanize_bytes

log = logging.getLogger(__name__)

_INTERVAL = 30  # 3600
_NFRAME = 25


class TraceMalloc(threading.Thread):
    def __init__(self):
        super().__init__(name=self.__class__.__name__)

    def run(self):
        process = psutil.Process()
        tracemalloc.start(_NFRAME)
        log.info(f"Started tracing memory allocations for {_NFRAME} frames.")

        while True:
            snapshot = tracemalloc.take_snapshot()
            stats = snapshot.statistics("filename")
            traced_current, traced_peak = tracemalloc.get_traced_memory()
            log.info(
                f"Process is using {humanize_bytes(process.memory_info().rss)}. "
                f"Memory tracing is using {humanize_bytes(tracemalloc.get_tracemalloc_memory())} "
                f"and tracing {humanize_bytes(traced_current)}."
            )
            for stat in stats[:7]:
                print(stat)
            time.sleep(_INTERVAL)
