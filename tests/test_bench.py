"""Tests for the benchmark module - heuristic scoring only (no LLM calls)."""
import textwrap
import tempfile
import os
from pathlib import Path

import pytest

from rtt import FileIndex, Symbol
from rtt.bench import (
    BenchQuestion,
    generate_questions,
    score_heuristic,
    _param_names,
    _return_type,
    _symbol_lines,
    _class_block,
    _imports_line,
    run_bench,
    _split_params,
    _extract_outer_params,
)
from rtt.extractor import extract_repo
from rtt.formatter import format_file_text


FIXTURES = Path(__file__).parent / "fixtures"


# ── unit tests for helpers ────────────────────────────────────────────────────

class TestParamNames:

    def test_basic_params(self):
        assert _param_names("def foo(x: int, y: str)") == ["x", "y"]

    def test_skips_self(self):
        assert "self" not in _param_names("def method(self, x: int)")
        assert "x" in _param_names("def method(self, x: int)")

    def test_skips_cls(self):
        assert "cls" not in _param_names("def from_env(cls, key: str)")

    def test_star_args(self):
        names = _param_names("def fn(*args, **kwargs)")
        assert "args" in names
        assert "kwargs" in names

    def test_default_values(self):
        names = _param_names("def fn(x: int = 0, y: str = 'hi')")
        assert "x" in names
        assert "y" in names

    def test_no_params(self):
        assert _param_names("def fn()") == []
        assert _param_names("def fn(self)") == []

    def test_go_style(self):
        assert "a" in _param_names("func add(a int, b int) int")

    def test_rust_style(self):
        assert "input" in _param_names("fn parse(input: &str) -> Config")

    def test_nested_default_does_not_pollute(self):
        # typer.Argument(".", help="...") should not produce "help" as a param name
        sig = 'def cmd(path: str = typer.Argument(".", help="desc"), flag: bool = False)'
        names = _param_names(sig)
        assert "path" in names
        assert "flag" in names
        assert "help" not in names
        assert "desc" not in names

    def test_split_params_respects_nesting(self):
        block = 'x: int, y: Callable[[int], str], z: bool'
        parts = _split_params(block)
        assert len(parts) == 3
        assert parts[0].strip() == "x: int"


class TestReturnType:

    def test_simple(self):
        assert _return_type("def fn(x: int) -> str") == "str"

    def test_optional(self):
        assert _return_type("def fn() -> Optional[str]") == "Optional"

    def test_custom_type(self):
        assert _return_type("def build() -> Config") == "Config"

    def test_none_filtered(self):
        assert _return_type("def fn() -> None") is None

    def test_primitives_returned(self):
        # Primitives are valid return types and should be returned
        assert _return_type("def fn() -> int") == "int"
        assert _return_type("def fn() -> bool") == "bool"
        assert _return_type("def fn() -> str") == "str"

    def test_no_arrow(self):
        assert _return_type("def fn(x: int)") is None

    def test_go_style_post_paren(self):
        # Go functions don't use -> - return type follows closing paren
        assert _return_type("func Start() error") == "error"
        assert _return_type("func NewServer(config Config) *Server") == "Server"


class TestSkeletonSearchHelpers:

    SKELETON = textwrap.dedent("""\
        # src/engine.py [python]
        imports: os, sys, pathlib
        class Engine:
          def __init__(self, config: Config) -> None
          def run(self, query: str) -> Result
          def stop(self) -> None
        def create_engine(path: str) -> Engine
    """)

    def test_symbol_lines_function(self):
        lines = _symbol_lines("create_engine", self.SKELETON)
        assert "create_engine" in lines
        assert "path" in lines

    def test_symbol_lines_method(self):
        lines = _symbol_lines("run", self.SKELETON)
        assert "query" in lines
        assert "Result" in lines

    def test_class_block_captures_children(self):
        block = _class_block("Engine", self.SKELETON)
        assert "__init__" in block
        assert "run" in block
        assert "stop" in block
        assert "create_engine" not in block  # top-level function, outside class

    def test_imports_line(self):
        line = _imports_line(self.SKELETON)
        assert "os" in line
        assert "sys" in line
        assert "pathlib" in line

    def test_imports_line_missing(self):
        assert _imports_line("# foo.py [python]\ndef fn(): pass") == ""


# ── question generation ───────────────────────────────────────────────────────

class TestQuestionGeneration:

    def _make_repo(self, code: str, lang: str = "python") -> tuple:
        ext = {"python": ".py", "javascript": ".js", "go": ".go", "rust": ".rs"}[lang]
        f = tempfile.NamedTemporaryFile(mode="w", suffix=ext, delete=False, dir="/tmp")
        f.write(textwrap.dedent(code))
        f.flush()
        return f.name

    def test_generates_params_question(self, tmp_path):
        (tmp_path / "a.py").write_text("def process(data: list, flag: bool) -> list:\n    pass\n")
        repo = extract_repo(str(tmp_path), use_cache=False)
        questions = generate_questions(repo)
        kinds = [q.kind for q in questions]
        assert "params" in kinds
        params_q = next(q for q in questions if q.kind == "params")
        assert "data" in params_q.expected_terms
        assert "flag" in params_q.expected_terms

    def test_generates_return_type_question(self, tmp_path):
        (tmp_path / "a.py").write_text("def build() -> Config:\n    pass\n")
        repo = extract_repo(str(tmp_path), use_cache=False)
        questions = generate_questions(repo)
        ret_qs = [q for q in questions if q.kind == "return_type"]
        assert ret_qs, "Expected at least one return_type question"
        assert any("Config" in q.expected_terms for q in ret_qs)

    def test_generates_methods_question(self, tmp_path):
        (tmp_path / "a.py").write_text(textwrap.dedent("""\
            class Foo:
                def alpha(self): pass
                def beta(self): pass
                def gamma(self): pass
        """))
        repo = extract_repo(str(tmp_path), use_cache=False)
        questions = generate_questions(repo)
        method_qs = [q for q in questions if q.kind == "methods"]
        assert method_qs
        q = method_qs[0]
        assert "alpha" in q.expected_terms
        assert "beta" in q.expected_terms
        assert "gamma" in q.expected_terms

    def test_generates_imports_question(self, tmp_path):
        (tmp_path / "a.py").write_text(textwrap.dedent("""\
            import os
            import sys
            from pathlib import Path

            def fn(): pass
        """))
        repo = extract_repo(str(tmp_path), use_cache=False)
        questions = generate_questions(repo)
        import_qs = [q for q in questions if q.kind == "imports"]
        assert import_qs
        q = import_qs[0]
        assert "os" in q.expected_terms

    def test_no_params_question_for_self_only(self, tmp_path):
        (tmp_path / "a.py").write_text("class Foo:\n    def method(self): pass\n")
        repo = extract_repo(str(tmp_path), use_cache=False)
        questions = generate_questions(repo)
        # No params question should be generated since 'self' is the only param
        params_qs = [q for q in questions if q.kind == "params"]
        assert all("self" not in q.expected_terms for q in params_qs)

    def test_no_imports_question_for_single_import(self, tmp_path):
        (tmp_path / "a.py").write_text("import os\ndef fn(): pass\n")
        repo = extract_repo(str(tmp_path), use_cache=False)
        questions = generate_questions(repo)
        import_qs = [q for q in questions if q.kind == "imports"]
        assert not import_qs  # need >= 2 imports to generate question


# ── heuristic scoring ─────────────────────────────────────────────────────────

class TestHeuristicScoring:

    def test_params_pass(self, tmp_path):
        (tmp_path / "a.py").write_text("def fn(alpha: int, beta: str) -> None:\n    pass\n")
        repo = extract_repo(str(tmp_path), use_cache=False)
        questions = generate_questions(repo)
        results = score_heuristic(questions, repo)
        params_results = [r for r in results if r.question.kind == "params"]
        assert params_results
        for r in params_results:
            assert r.passed, f"params failed: missing {r.missing_terms}"

    def test_return_type_pass(self, tmp_path):
        (tmp_path / "a.py").write_text("def build() -> Config:\n    pass\n")
        repo = extract_repo(str(tmp_path), use_cache=False)
        questions = generate_questions(repo)
        results = score_heuristic(questions, repo)
        ret_results = [r for r in results if r.question.kind == "return_type"]
        for r in ret_results:
            assert r.passed, f"return_type failed: missing {r.missing_terms}"

    def test_methods_pass(self, tmp_path):
        (tmp_path / "a.py").write_text(textwrap.dedent("""\
            class Processor:
                def load(self, path: str) -> None: pass
                def run(self, data: list) -> list: pass
                def save(self, path: str) -> None: pass
        """))
        repo = extract_repo(str(tmp_path), use_cache=False)
        questions = generate_questions(repo)
        results = score_heuristic(questions, repo)
        method_results = [r for r in results if r.question.kind == "methods"]
        assert method_results
        for r in method_results:
            assert r.passed, f"methods failed: missing {r.missing_terms}"

    def test_imports_pass(self, tmp_path):
        (tmp_path / "a.py").write_text(textwrap.dedent("""\
            import os
            import sys
            from pathlib import Path
            def fn(): pass
        """))
        repo = extract_repo(str(tmp_path), use_cache=False)
        questions = generate_questions(repo)
        results = score_heuristic(questions, repo)
        import_results = [r for r in results if r.question.kind == "imports"]
        for r in import_results:
            assert r.passed, f"imports failed: missing {r.missing_terms}"

    def test_detects_missing_term(self):
        """Manually constructed failing question."""
        fi = FileIndex(
            path="fake.py",
            language="python",
            imports=[],
            symbols=[Symbol(
                name="fn",
                kind="function",
                # 'secret_param' deliberately absent
                signature="def fn(other: int) -> None",
            )],
        )
        from rtt import RepoIndex
        repo = RepoIndex(files=[fi])
        q = BenchQuestion(
            kind="params",
            question="What params does fn take?",
            file="fake.py",
            symbol="fn",
            expected_terms=["secret_param"],
        )
        results = score_heuristic([q], repo)
        assert len(results) == 1
        assert not results[0].passed
        assert "secret_param" in results[0].missing_terms

    def test_score_property(self, tmp_path):
        (tmp_path / "a.py").write_text(textwrap.dedent("""\
            import os, sys
            def alpha(x: int, y: str) -> Config: pass
            class Beta:
                def run(self): pass
                def stop(self): pass
        """))
        repo = extract_repo(str(tmp_path), use_cache=False)
        from rtt.bench import BenchReport, run_bench
        report = run_bench(str(tmp_path))
        assert report.heuristic_score == 100.0
        assert report.total_questions > 0
        assert report.llm_score is None  # LLM not run


# ── full fixture bench ────────────────────────────────────────────────────────

class TestBenchOnFixtures:

    def test_fixtures_100_percent(self, tmp_path):
        """All fixture files should achieve 100% on the heuristic bench."""
        import shutil
        for f in FIXTURES.iterdir():
            if f.is_file():
                shutil.copy(f, tmp_path / f.name)

        report = run_bench(str(tmp_path))
        assert report.total_questions > 0

        failing = report.heuristic_failing
        if failing:
            details = [
                f"{r.question.file}::{r.question.symbol}({r.question.kind})"
                f" missing={r.missing_terms}"
                for r in failing
            ]
            pytest.fail("Bench failures:\n" + "\n".join(details))

    def test_self_bench_100_percent(self):
        """rtt's own source should score 100% on the heuristic bench."""
        import rtt as rtt_pkg
        pkg_dir = str(Path(rtt_pkg.__file__).parent.parent)
        report = run_bench(pkg_dir)
        assert report.total_questions > 0
        assert report.heuristic_score == 100.0, (
            f"Self-bench score {report.heuristic_score:.1f}% < 100%\n"
            + "\n".join(
                f"  {r.question.file}::{r.question.symbol} missing {r.missing_terms}"
                for r in report.heuristic_failing
            )
        )
