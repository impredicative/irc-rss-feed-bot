import functools
import hashlib
from typing import Dict, List


class Int8Hash:

    MIN = -9_223_372_036_854_775_808
    MAX = +9_223_372_036_854_775_807

    @classmethod
    def todict(cls, texts: List[str]) -> Dict[str, int]:
        return {text: cls.toint(text) for text in texts}

    @classmethod
    @functools.lru_cache(1024)
    def toint(cls, text: str) -> int:
        seed = text.encode()
        hash_digest = hashlib.shake_128(seed).digest(8)
        hash_int = int.from_bytes(hash_digest, byteorder='big', signed=True)
        assert cls.MIN <= hash_int <= cls.MAX
        return hash_int

    @classmethod
    def tolist(cls, texts: List[str]) -> List[int]:
        return [cls.toint(text) for text in texts]


import random
import string
import unittest


class TestInt8Hash(unittest.TestCase):
    def test_range(self):
        toint = Int8Hash.toint
        localrandom = random.Random(0)
        for _ in range(10_000):
            text_len = localrandom.randrange(128)
            text = ''.join(localrandom.choice(string.printable) for _ in range(text_len))
            int8 = toint(text)
            self.assertLessEqual(Int8Hash.MIN, int8)
            self.assertGreaterEqual(Int8Hash.MAX, int8)
