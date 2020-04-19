"""Import all utility modules."""
from importlib import import_module
from pathlib import Path

for f in Path(__file__).parent.glob("*.py"):
    if not f.stem.startswith("_"):
        import_module(f".{f.stem}", __package__)
del import_module, Path

# # pylint: disable=redefined-builtin
# from . import datetime, float, hashlib, hext, humanize, ircmessage, list, lxml, set, textwrap, timeit, urllib
