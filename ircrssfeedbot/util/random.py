import functools
import random


@functools.lru_cache(1024)
def strtoint(text: str) -> int:
    return random.Random(text).randint(-9_223_372_036_854_775_808, 9_223_372_036_854_775_807)
