"""Import all parsers."""
from importlib import import_module
from pathlib import Path

for f in Path(__file__).parent.glob("*.py"):
    module = f.stem
    if module != "base":
        import_module(f".{module}", __package__)
del import_module, Path
