"""str utilities."""
from typing import Any, List


def list_irc_modes(mode: str) -> List[str]:
    """Return a list of IRC modes from a mode string.

    Examples
    --------
    '+Six' -> ['+S', '+i', '+x']
    '-Six' -> ['-S', '-i', '-x']
    '+S-ix' -> ['+S', '-i', '-x']

    """
    modes = []
    for char in mode:
        if char in ("+", "-"):
            sign = char
        else:
            modes.append(f"{sign}{char}")
    return modes


def readable_list(seq: List[Any]) -> str:
    """Return a grammatically correct human readable string (with an Oxford comma)."""
    # Ref: https://stackoverflow.com/a/53981846/
    seq = [str(s) for s in seq]
    if len(seq) < 3:
        return " and ".join(seq)
    return ", ".join(seq[:-1]) + ", and " + seq[-1]
