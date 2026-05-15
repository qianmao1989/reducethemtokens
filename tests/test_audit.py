import textwrap
import tempfile
import os

from rtt.audit import audit_file, audit_repo, _flatten_rtt_symbols, _check_signature
from rtt import Symbol


def write_temp(content: str, suffix: str) -> str:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False)
    f.write(content)
    f.flush()
    return f.name


# ── coverage tests ────────────────────────────────────────────────────────────

def test_python_full_coverage():
    code = textwrap.dedent("""
        def alpha(x: int) -> str:
            return str(x)

        def beta():
            pass

        class MyClass:
            def method_one(self) -> None:
                pass

            def method_two(self, val: int) -> int:
                return val
    """)
    path = write_temp(code, ".py")
    try:
        result = audit_file(path)
        assert result is not None
        # ground truth: alpha, beta, MyClass, method_one, method_two = 5
        assert result.expected == 5
        # all should be found
        assert result.found == result.expected
        assert result.missing == []
    finally:
        os.unlink(path)


def test_python_decorated_function_found():
    code = textwrap.dedent("""
        def decorator(f):
            return f

        @decorator
        def wrapped(x: int) -> int:
            return x
    """)
    path = write_temp(code, ".py")
    try:
        result = audit_file(path)
        assert result is not None
        found_names = {result.path} | {gt.name for gt in result.missing}
        # 'wrapped' should not be in missing
        missing_names = {gt.name for gt in result.missing}
        assert "wrapped" not in missing_names
    finally:
        os.unlink(path)


def test_coverage_ratio():
    code = textwrap.dedent("""
        def fn_a(): pass
        def fn_b(): pass
        def fn_c(): pass
        def fn_d(): pass
    """)
    path = write_temp(code, ".py")
    try:
        result = audit_file(path)
        assert result is not None
        assert result.expected == 4
        assert result.coverage == 100.0
    finally:
        os.unlink(path)


def test_unsupported_file_returns_none():
    path = write_temp("hello world", ".txt")
    try:
        result = audit_file(path)
        assert result is None
    finally:
        os.unlink(path)


# ── signature accuracy tests ──────────────────────────────────────────────────

def test_signature_valid():
    sym = Symbol(name="foo", kind="function", signature="def foo(x: int) -> str")
    issue = _check_signature(sym, b"def foo(x: int) -> str:\n    pass", "python")
    assert issue is None


def test_signature_empty():
    sym = Symbol(name="bar", kind="function", signature="")
    issue = _check_signature(sym, b"def bar(): pass", "python")
    assert issue is not None
    assert "empty" in issue.issue


def test_signature_missing_name():
    sym = Symbol(name="baz", kind="function", signature="def qux(x: int)")
    issue = _check_signature(sym, b"def baz(x: int): pass", "python")
    assert issue is not None
    assert "baz" in issue.issue


def test_signature_unbalanced_parens():
    sym = Symbol(name="fn", kind="function", signature="def fn(x: int, y: str")
    issue = _check_signature(sym, b"def fn(x: int, y: str): pass", "python")
    assert issue is not None  # any issue caught is correct - sig is malformed


def test_signature_missing_parens():
    sym = Symbol(name="fn", kind="function", signature="def fn")
    issue = _check_signature(sym, b"def fn(): pass", "python")
    assert issue is not None
    assert "parentheses" in issue.issue


def test_class_signature_no_parens_ok():
    sym = Symbol(name="MyClass", kind="class", signature="class MyClass")
    issue = _check_signature(sym, b"class MyClass:\n    pass", "python")
    assert issue is None


# ── flatten helper ────────────────────────────────────────────────────────────

def test_flatten_nested():
    child = Symbol(name="method", kind="method", signature="def method(self)")
    parent = Symbol(name="MyClass", kind="class", signature="class MyClass", children=[child])
    flat = _flatten_rtt_symbols([parent])
    names = [s.name for s in flat]
    assert "MyClass" in names
    assert "method" in names


# ── repo-level audit ──────────────────────────────────────────────────────────

def test_audit_repo_on_self(tmp_path):
    code = textwrap.dedent("""
        def hello(name: str) -> str:
            return f"hello {name}"

        class Adder:
            def add(self, a: int, b: int) -> int:
                return a + b
    """)
    (tmp_path / "sample.py").write_text(code)
    report = audit_repo(str(tmp_path))
    assert len(report.files) == 1
    fa = report.files[0]
    assert fa.expected == 3  # hello, Adder, add
    assert fa.coverage == 100.0
    assert report.coverage == 100.0
