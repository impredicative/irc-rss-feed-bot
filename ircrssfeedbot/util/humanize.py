"""humanize utilities."""
from humanize import naturalsize


def humanize_bytes(num_bytes: int) -> str:
    """Return a human friendly string size representation of a given number of bytes."""
    return naturalsize(num_bytes, gnu=True, format="%.0f")


def humanize_size(text: bytes) -> str:
    """Return a human friendly string size representation of the length of the given bytes."""
    assert isinstance(text, bytes)  # The returned value won't be correct for a string.
    return humanize_bytes(len(text))
