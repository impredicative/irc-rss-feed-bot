"""str utilities."""
from typing import Any, List


def readable_list(seq: List[Any]) -> str:
    """Return a grammatically correct human readable string (with an Oxford comma)."""
    # Ref: https://stackoverflow.com/a/53981846/
    seq = [str(s) for s in seq]
    if len(seq) < 3:
        return " and ".join(seq)
    return ", ".join(seq[:-1]) + ", and " + seq[-1]
