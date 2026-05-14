import json
from pathlib import Path

from rtt import FileIndex, Symbol

CACHE_DIR = ".rtt-cache"
CACHE_FILE = "index.json"


def _symbol_from_dict(d: dict) -> Symbol:
    children = [_symbol_from_dict(c) for c in d.get("children", [])]
    return Symbol(
        name=d["name"],
        kind=d["kind"],
        signature=d["signature"],
        docstring=d.get("docstring"),
        children=children,
    )


def _file_index_from_dict(d: dict) -> FileIndex:
    return FileIndex(
        path=d["path"],
        language=d["language"],
        imports=d.get("imports", []),
        symbols=[_symbol_from_dict(s) for s in d.get("symbols", [])],
    )


class Cache:
    def __init__(self, repo_root: str):
        self.cache_dir = Path(repo_root) / CACHE_DIR
        self.cache_file = self.cache_dir / CACHE_FILE
        self._data: dict = {}
        self._load()

    def _load(self):
        if self.cache_file.exists():
            try:
                self._data = json.loads(self.cache_file.read_text())
            except Exception:
                self._data = {}

    def get(self, filepath: str, file_hash: str) -> FileIndex | None:
        entry = self._data.get(filepath)
        if entry and entry.get("hash") == file_hash:
            try:
                return _file_index_from_dict(entry["index"])
            except Exception:
                return None
        return None

    def set(self, filepath: str, file_hash: str, file_index: FileIndex):
        self._data[filepath] = {
            "hash": file_hash,
            "index": self._file_index_to_dict(file_index),
        }

    def _symbol_to_dict(self, sym: Symbol) -> dict:
        return {
            "name": sym.name,
            "kind": sym.kind,
            "signature": sym.signature,
            "docstring": sym.docstring,
            "children": [self._symbol_to_dict(c) for c in sym.children],
        }

    def _file_index_to_dict(self, fi: FileIndex) -> dict:
        return {
            "path": fi.path,
            "language": fi.language,
            "imports": fi.imports,
            "symbols": [self._symbol_to_dict(s) for s in fi.symbols],
        }

    def save(self):
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_file.write_text(json.dumps(self._data, indent=2))
