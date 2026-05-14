import importlib
from pathlib import Path
from typing import Optional

EXTENSION_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".rb": "ruby",
    ".swift": "swift",
}

LANGUAGE_MODULES = {
    "python": "tree_sitter_python",
    "javascript": "tree_sitter_javascript",
    "typescript": "tree_sitter_typescript",
    "go": "tree_sitter_go",
    "rust": "tree_sitter_rust",
    "java": "tree_sitter_java",
    "c": "tree_sitter_c",
    "cpp": "tree_sitter_cpp",
    "ruby": "tree_sitter_ruby",
}


def detect_language(filepath: str) -> Optional[str]:
    ext = Path(filepath).suffix.lower()
    return EXTENSION_MAP.get(ext)


def get_ts_language(lang_name: str):
    module_name = LANGUAGE_MODULES.get(lang_name)
    if not module_name:
        return None
    try:
        mod = importlib.import_module(module_name)
        from tree_sitter import Language
        return Language(mod.language())
    except (ImportError, AttributeError, Exception):
        return None
