from datetime import timedelta


def timedelta_desc(seconds: float) -> str:
    return str(timedelta(seconds=round(seconds)))
