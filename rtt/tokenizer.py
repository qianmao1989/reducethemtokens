import os
from pathlib import Path

try:
    import tiktoken
    _enc = tiktoken.get_encoding("cl100k_base")

    def count_tokens(text: str) -> int:
        return len(_enc.encode(text))
except ImportError:
    def count_tokens(text: str) -> int:
        return len(text.split()) * 4 // 3  # rough fallback


SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "__pycache__", ".pytest_cache",
    "venv", ".venv", "env", ".env", "dist", "build", ".next", ".nuxt",
    "target", ".rtt-cache",
}

TEXT_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java",
    ".c", ".h", ".cpp", ".cc", ".cxx", ".hpp", ".rb", ".swift",
    ".sh", ".bash", ".zsh", ".fish", ".json", ".yaml", ".yml",
    ".toml", ".ini", ".cfg", ".conf", ".md", ".txt", ".html",
    ".css", ".scss", ".sass", ".less", ".xml", ".sql",
}


def count_file_tokens(filepath: str) -> int:
    try:
        path = Path(filepath)
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            return 0
        text = path.read_text(errors="replace")
        return count_tokens(text)
    except Exception:
        return 0


def count_raw_repo_tokens(path: str) -> tuple[int, dict[str, int]]:
    root = Path(path).resolve()
    total = 0
    per_file = {}

    for dirpath, dirnames, filenames in os.walk(str(root)):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            rel = os.path.relpath(filepath, str(root))
            n = count_file_tokens(filepath)
            if n > 0:
                per_file[rel] = n
                total += n

    return total, per_file
