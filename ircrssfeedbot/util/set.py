"""set utilities."""
import unittest
from typing import Any, Dict, Set


def leaves(struct: Any) -> Set[Any]:
    """Return a set of leaf values found in nested dicts and lists excluding None values."""
    values = set()
    if isinstance(struct, dict):
        for sub_struct in struct.values():
            values.update(leaves(sub_struct))
    elif isinstance(struct, list):
        for sub_struct in struct:
            values.update(leaves(sub_struct))
    elif struct is not None:
        values.add(struct)
    return values


# pylint: disable=missing-class-docstring,missing-function-docstring
class TestLeaves(unittest.TestCase):
    def test_dict(self):
        struct: Dict[str, Any] = {
            "k0": None,
            "k1": "v1",
            "k2": ["v0", None, "v1"],
            "k3": ["v0", ["v1", "v2", None, ["v3"], ["v4", "v5"], []]],
            "k4": {"k0": None},
            "k5": {"k1": {"k2": {"k3": "v3", "k4": "v6"}, "k4": {}}},
            "k6": [{}, {"k1": "v7"}, {"k2": "v8", "k3": "v9", "k4": {"k5": {"k6": "v10"}, "k7": {}}}],
            "k7": {
                "k0": [],
                "k1": ["v11"],
                "k2": ["v12", "v13"],
                "k3": ["v14", ["v15"]],
                "k4": [["v16"], ["v17"]],
                "k5": ["v18", ["v19", "v20", ["v21", "v22", []]]],
            },
        }
        expected_values = {f"v{i}" for i in range(23)}
        actual_values = leaves(struct)
        self.assertEqual(expected_values, actual_values)
        # print(sorted(actual_values, key=lambda s: int(s[1:])))

    def test_list(self):
        struct = ["aa", "bb", "cc", ["dd", "ee", ["ff", "gg"], None, []]]
        expected_values = {f"{s}{s}" for s in "abcdefg"}
        actual_values = leaves(struct)
        self.assertEqual(expected_values, actual_values)
        # print(sorted(actual_values))
