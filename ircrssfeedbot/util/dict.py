"""dict utilities."""


def dict_repr(data: dict) -> str:
    """Return a humanized string with canonical values from the items in the given dictionary."""
    return ", ".join(f"{k}={v!r}" for k, v in data.items())


def dict_str(data: dict) -> str:
    """Return a humanized string from the items in the given dictionary."""
    return ", ".join(f"{k}={v}" for k, v in data.items())
