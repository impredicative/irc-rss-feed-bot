import functools
import random
from typing import Dict, List


class DBHash:

    @classmethod
    def todict(cls, texts: List[str]) -> Dict[str, int]:
        return {text: cls.toint(text) for text in texts}

    @staticmethod
    @functools.lru_cache(1024)
    def toint(text: str) -> int:
        return random.Random(text).randint(-9_223_372_036_854_775_808, 9_223_372_036_854_775_807)

    @classmethod
    def tolist(cls, texts: List[str]) -> List[int]:
        return [cls.toint(text) for text in texts]
