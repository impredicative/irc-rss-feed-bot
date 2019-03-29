import functools
import random


@functools.lru_cache(4096)
def str_to_num(text: str, num_bytes: int = 8) -> int:
    local_random = random.Random(text)
    if num_bytes == 8:
        return local_random.randint(-9_223_372_036_854_775_808, 9_223_372_036_854_775_807)
    else:
        assert num_bytes == 4
        return local_random.randint(-2_147_483_648, 2_147_483_647)
