"""Module with conditional definitions inside try/except and if blocks."""

try:
    import ujson as json

    def fast_loads(s: str) -> dict:
        """Parse JSON using ujson."""
        return json.loads(s)

    def fast_dumps(obj: dict) -> str:
        return json.dumps(obj)

except ImportError:
    import json

    def fast_loads(s: str) -> dict:
        """Parse JSON using stdlib json."""
        return json.loads(s)

    def fast_dumps(obj: dict) -> str:
        return json.dumps(obj)


try:
    from typing import Protocol

    class Readable(Protocol):
        def read(self) -> bytes: ...

except ImportError:
    class Readable:
        def read(self) -> bytes:
            raise NotImplementedError


import sys

if sys.platform == "win32":
    def get_path_sep() -> str:
        return "\\"
else:
    def get_path_sep() -> str:
        return "/"


def always_present(x: int) -> int:
    """This function is always at top level."""
    return x * 2
