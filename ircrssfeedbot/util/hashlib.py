"""hashlib utilities."""
import functools
import hashlib
import random
import string
import unittest
from typing import Dict, List, Union

from ..config import CACHE_MAXSIZE__INT8HASH


def hash4(content: Union[bytes, str]) -> str:
    """Return a 4 byte hash encoded as a hex string."""
    if isinstance(content, str):
        content = content.encode()
    return hashlib.shake_128(content).hexdigest(4)  # pylint: disable=too-many-function-args


class Int8Hash:
    """8 byte signed integer hash of string."""

    BYTES = 8
    BITS = BYTES * 8
    BITS_MINUS1 = BITS - 1
    MIN = -(2**BITS_MINUS1)
    MAX = 2**BITS_MINUS1 - 1

    @classmethod
    def as_dict(cls, texts: List[str]) -> Dict[int, str]:
        """Return a mapping of integer hashes corresponding to the given list of strings."""
        return {cls.as_int(text): text for text in texts}  # Intentionally Dict[int, str], not Dict[str, int].

    @classmethod
    @functools.lru_cache(CACHE_MAXSIZE__INT8HASH)
    def as_int(cls, text: str) -> int:
        """Return an integer hash of a string."""
        seed = text.encode()
        hash_digest = hashlib.shake_128(seed).digest(cls.BYTES)  # pylint: disable=too-many-function-args
        hash_int = int.from_bytes(hash_digest, byteorder="big", signed=True)
        assert cls.MIN <= hash_int <= cls.MAX
        return hash_int

    @classmethod
    def as_list(cls, texts: List[str]) -> List[int]:
        """Return a list of integer hashes corresponding to the given list of strings."""
        return [cls.as_int(text) for text in texts]


# pylint: disable=missing-class-docstring,missing-function-docstring
class TestInt8Hash(unittest.TestCase):
    def test_range(self):
        localrandom = random.Random(0)
        for _ in range(10_000):
            text_len = localrandom.randrange(128)
            text = "".join(localrandom.choice(string.printable) for _ in range(text_len))
            int8 = Int8Hash.as_int(text)
            self.assertLessEqual(Int8Hash.MIN, int8)
            self.assertGreaterEqual(Int8Hash.MAX, int8)


# python -m unittest -v ircrssfeedbot.util.hashlib
