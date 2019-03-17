from humanize import naturalsize


def humanize_bytes(num_bytes: int) -> str:
    return naturalsize(num_bytes, gnu=True, format='%.0f')
