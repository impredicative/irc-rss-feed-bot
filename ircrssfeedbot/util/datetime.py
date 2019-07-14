from datetime import timedelta
from typing import Union


def timedelta_desc(seconds: Union[int, float, timedelta]) -> str:
    if isinstance(seconds, timedelta):
        seconds = seconds.total_seconds()
    return str(timedelta(seconds=round(seconds)))
