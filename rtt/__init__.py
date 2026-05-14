from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Symbol:
    name: str
    kind: str  # "function", "class", "method", "constant"
    signature: str  # e.g. "def run(self, query: str) -> Result"
    docstring: Optional[str] = None
    children: list["Symbol"] = field(default_factory=list)


@dataclass
class FileIndex:
    path: str
    language: str
    imports: list[str] = field(default_factory=list)
    symbols: list[Symbol] = field(default_factory=list)


@dataclass
class RepoIndex:
    files: list[FileIndex] = field(default_factory=list)

    @property
    def token_count(self) -> int:
        from rtt.tokenizer import count_tokens
        return count_tokens(self.text)

    @property
    def text(self) -> str:
        from rtt.formatter import format_text
        return format_text(self)


@dataclass
class CompareReport:
    path: str
    raw_tokens: int
    compressed_tokens: int
    file_count: int
    per_file: list[dict]  # {path, raw, compressed}

    @property
    def reduction_pct(self) -> float:
        if self.raw_tokens == 0:
            return 0.0
        return (1 - self.compressed_tokens / self.raw_tokens) * 100


@dataclass
class DiffReport:
    before_tokens: int
    after_tokens: int
    changed_files: list[dict]  # {path, before, after, is_new, is_deleted}

    @property
    def delta(self) -> int:
        return self.after_tokens - self.before_tokens


def index(
    path: str,
    include: Optional[list[str]] = None,
    exclude: Optional[list[str]] = None,
    max_tokens: Optional[int] = None,
    no_tests: bool = False,
) -> RepoIndex:
    from rtt.extractor import extract_repo
    return extract_repo(path, include=include, exclude=exclude,
                        max_tokens=max_tokens, no_tests=no_tests)


def compare(path: str) -> CompareReport:
    from rtt.extractor import compare_repo
    return compare_repo(path)
