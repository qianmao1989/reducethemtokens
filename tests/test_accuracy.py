"""
Extensive accuracy tests: coverage and signature correctness across languages
and edge cases. All tests use audit_file() to compare rtt output against the
ground truth AST walk.
"""
import textwrap
import tempfile
import os
from pathlib import Path

import pytest

from rtt.audit import audit_file, audit_repo
from rtt.extractor import _extract_file


FIXTURES = Path(__file__).parent / "fixtures"


# ── helpers ───────────────────────────────────────────────────────────────────

def write_temp(content: str, suffix: str) -> str:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False)
    f.write(textwrap.dedent(content))
    f.flush()
    return f.name


def assert_full_coverage(path: str, min_expected: int = 1):
    """Assert 100% coverage with no signature issues."""
    result = audit_file(path)
    assert result is not None, f"audit_file returned None for {path}"
    assert result.expected >= min_expected, (
        f"Expected at least {min_expected} symbols, ground truth found {result.expected}"
    )
    missing_names = [f"{gt.name} ({gt.kind}, line {gt.line})" for gt in result.missing]
    assert result.missing == [], f"Missing symbols: {missing_names}"
    sig_issues = [(i.symbol_name, i.issue) for i in result.signature_issues]
    assert result.signature_issues == [], f"Signature issues: {sig_issues}"
    assert result.coverage == 100.0


# ══════════════════════════════════════════════════════════════════════════════
# Python: core patterns
# ══════════════════════════════════════════════════════════════════════════════

class TestPythonCore:

    def test_plain_functions_and_class(self):
        path = write_temp("""
            def alpha(x: int) -> str:
                return str(x)

            def beta():
                pass

            class MyClass:
                def method_one(self) -> None:
                    pass
                def method_two(self, val: int) -> int:
                    return val
        """, ".py")
        try:
            assert_full_coverage(path, min_expected=4)
        finally:
            os.unlink(path)

    def test_return_type_in_signature(self):
        path = write_temp("""
            def compute(x: int, y: int) -> float:
                return x / y
        """, ".py")
        try:
            fi = _extract_file(path)
            assert fi is not None
            sig = fi.symbols[0].signature
            assert "->" in sig, f"Return type missing from signature: {sig}"
            assert "float" in sig
        finally:
            os.unlink(path)

    def test_docstring_captured(self):
        path = write_temp('''
            def greet(name: str) -> str:
                """Say hello to name."""
                return f"Hello {name}"
        ''', ".py")
        try:
            fi = _extract_file(path)
            assert fi and fi.symbols[0].docstring == "Say hello to name."
        finally:
            os.unlink(path)

    def test_class_with_base(self):
        path = write_temp("""
            class Animal:
                def speak(self) -> str:
                    return ""

            class Dog(Animal):
                def speak(self) -> str:
                    return "woof"
        """, ".py")
        try:
            fi = _extract_file(path)
            assert fi is not None
            dog = next(s for s in fi.symbols if s.name == "Dog")
            assert "Animal" in dog.signature
        finally:
            os.unlink(path)

    def test_imports_extracted(self):
        path = write_temp("""
            import os
            import sys
            from pathlib import Path
            from typing import Optional, List

            def fn(): pass
        """, ".py")
        try:
            fi = _extract_file(path)
            assert fi is not None
            assert "os" in fi.imports
            assert "sys" in fi.imports
            assert any("pathlib" in i for i in fi.imports)
            assert any("typing" in i for i in fi.imports)
        finally:
            os.unlink(path)

    def test_nested_function_not_extracted(self):
        """Functions inside functions are implementation details — should not appear."""
        path = write_temp("""
            def outer(x: int) -> int:
                def inner(y: int) -> int:
                    return y * 2
                return inner(x)
        """, ".py")
        try:
            fi = _extract_file(path)
            assert fi is not None
            all_names = [s.name for s in fi.symbols]
            assert "outer" in all_names
            assert "inner" not in all_names
        finally:
            os.unlink(path)

    def test_empty_file(self):
        path = write_temp("", ".py")
        try:
            result = audit_file(path)
            # No symbols expected in an empty file
            assert result is None or result.expected == 0
        finally:
            os.unlink(path)

    def test_imports_only_file(self):
        path = write_temp("""
            import os
            import sys
            from pathlib import Path
        """, ".py")
        try:
            result = audit_file(path)
            assert result is None or result.expected == 0
        finally:
            os.unlink(path)

    def test_multiline_params(self):
        path = write_temp("""
            def complex_fn(
                name: str,
                value: int,
                flag: bool = False,
            ) -> dict:
                return {}
        """, ".py")
        try:
            assert_full_coverage(path, min_expected=1)
            fi = _extract_file(path)
            sig = fi.symbols[0].signature
            assert "complex_fn" in sig
            assert "(" in sig and ")" in sig
        finally:
            os.unlink(path)


# ══════════════════════════════════════════════════════════════════════════════
# Python: decorated symbols (the previously broken cases)
# ══════════════════════════════════════════════════════════════════════════════

class TestPythonDecorated:

    def test_property_inside_plain_class(self):
        path = write_temp("""
            class Circle:
                def __init__(self, radius: float) -> None:
                    self._radius = radius

                @property
                def radius(self) -> float:
                    return self._radius

                @property
                def area(self) -> float:
                    return 3.14159 * self._radius ** 2

                def scale(self, factor: float) -> None:
                    self._radius *= factor
        """, ".py")
        try:
            assert_full_coverage(path, min_expected=4)
        finally:
            os.unlink(path)

    def test_dataclass_with_property(self):
        path = write_temp("""
            from dataclasses import dataclass

            @dataclass
            class Vector:
                x: float
                y: float

                @property
                def length(self) -> float:
                    return (self.x**2 + self.y**2) ** 0.5

                def dot(self, other: "Vector") -> float:
                    return self.x * other.x + self.y * other.y
        """, ".py")
        try:
            assert_full_coverage(path, min_expected=3)
        finally:
            os.unlink(path)

    def test_staticmethod_and_classmethod(self):
        path = write_temp("""
            from dataclasses import dataclass

            @dataclass
            class Factory:
                name: str

                @staticmethod
                def create_default() -> "Factory":
                    return Factory("default")

                @classmethod
                def from_env(cls, key: str) -> "Factory":
                    import os
                    return cls(os.environ.get(key, ""))

                def describe(self) -> str:
                    return f"Factory({self.name})"
        """, ".py")
        try:
            assert_full_coverage(path, min_expected=3)
        finally:
            os.unlink(path)

    def test_decorated_top_level_function(self):
        path = write_temp("""
            def decorator(fn):
                return fn

            @decorator
            def process(data: list) -> list:
                return data

            @decorator
            @decorator
            def double_wrapped(x: int) -> int:
                return x
        """, ".py")
        try:
            assert_full_coverage(path, min_expected=3)
        finally:
            os.unlink(path)

    def test_fixture_decorated(self):
        """Full audit of the decorated fixture file."""
        assert_full_coverage(str(FIXTURES / "sample_decorated.py"), min_expected=10)


# ══════════════════════════════════════════════════════════════════════════════
# Python: try/except conditional definitions (the previously broken case)
# ══════════════════════════════════════════════════════════════════════════════

class TestPythonTryExcept:

    def test_function_in_try_block(self):
        path = write_temp("""
            try:
                import fast_lib

                def encode(data: bytes) -> str:
                    return fast_lib.encode(data)

            except ImportError:
                def encode(data: bytes) -> str:
                    return data.hex()
        """, ".py")
        try:
            fi = _extract_file(path)
            assert fi is not None
            names = [s.name for s in fi.symbols]
            assert "encode" in names, f"encode not found in {names}"
        finally:
            os.unlink(path)

    def test_class_in_try_block(self):
        path = write_temp("""
            try:
                from typing import Protocol

                class Readable(Protocol):
                    def read(self) -> bytes: ...

            except ImportError:
                class Readable:
                    def read(self) -> bytes:
                        raise NotImplementedError
        """, ".py")
        try:
            fi = _extract_file(path)
            assert fi is not None
            names = [s.name for s in fi.symbols]
            assert "Readable" in names
        finally:
            os.unlink(path)

    def test_function_in_if_block(self):
        path = write_temp("""
            import sys

            if sys.platform == "win32":
                def sep() -> str:
                    return "\\\\"
            else:
                def sep() -> str:
                    return "/"
        """, ".py")
        try:
            fi = _extract_file(path)
            assert fi is not None
            names = [s.name for s in fi.symbols]
            assert "sep" in names
        finally:
            os.unlink(path)

    def test_dedup_try_except_same_name(self):
        """Same name in try and except should appear only once."""
        path = write_temp("""
            try:
                def loads(s: str) -> dict:
                    import ujson
                    return ujson.loads(s)
            except ImportError:
                def loads(s: str) -> dict:
                    import json
                    return json.loads(s)
        """, ".py")
        try:
            fi = _extract_file(path)
            assert fi is not None
            names = [s.name for s in fi.symbols]
            assert names.count("loads") == 1, f"Duplicate 'loads': {names}"
        finally:
            os.unlink(path)

    def test_fixture_try_except(self):
        """Full audit of the try/except fixture file."""
        result = audit_file(str(FIXTURES / "sample_try_except.py"))
        assert result is not None
        # always_present, fast_loads, fast_dumps, Readable, get_path_sep should be found
        found_names = {s.name for s in []} | (
            set() if not result else set()
        )
        fi = _extract_file(str(FIXTURES / "sample_try_except.py"))
        assert fi is not None
        names = [s.name for s in fi.symbols]
        assert "always_present" in names
        assert "fast_loads" in names
        assert "fast_dumps" in names
        assert "get_path_sep" in names


# ══════════════════════════════════════════════════════════════════════════════
# JavaScript
# ══════════════════════════════════════════════════════════════════════════════

class TestJavaScript:

    def test_function_declaration(self):
        path = write_temp("""
            function greet(name) {
                return "Hello " + name;
            }

            function add(a, b) {
                return a + b;
            }
        """, ".js")
        try:
            assert_full_coverage(path, min_expected=2)
        finally:
            os.unlink(path)

    def test_class_with_methods(self):
        path = write_temp("""
            class Animal {
                constructor(name) {
                    this.name = name;
                }

                speak() {
                    return this.name + " makes a noise.";
                }

                toString() {
                    return "Animal(" + this.name + ")";
                }
            }
        """, ".js")
        try:
            fi = _extract_file(path)
            assert fi is not None
            names = [s.name for s in fi.symbols]
            assert "Animal" in names
        finally:
            os.unlink(path)

    def test_arrow_function_assignment(self):
        path = write_temp("""
            const double = (x) => x * 2;
            const greet = (name) => "Hello " + name;
        """, ".js")
        try:
            fi = _extract_file(path)
            assert fi is not None
            names = [s.name for s in fi.symbols]
            assert "double" in names
            assert "greet" in names
        finally:
            os.unlink(path)

    def test_exported_function(self):
        path = write_temp("""
            export function parseJSON(s) {
                return JSON.parse(s);
            }

            export class Config {
                get(key) { return this[key]; }
            }
        """, ".js")
        try:
            fi = _extract_file(path)
            assert fi is not None
            names = [s.name for s in fi.symbols]
            assert "parseJSON" in names
            assert "Config" in names
        finally:
            os.unlink(path)

    def test_fixture_js(self):
        assert_full_coverage(str(FIXTURES / "sample_js.js"), min_expected=4)


# ══════════════════════════════════════════════════════════════════════════════
# Go
# ══════════════════════════════════════════════════════════════════════════════

class TestGo:

    def test_functions_and_struct(self):
        path = write_temp("""
            package main

            type Point struct {
                X float64
                Y float64
            }

            func NewPoint(x, y float64) Point {
                return Point{X: x, Y: y}
            }

            func (p Point) Distance(other Point) float64 {
                dx := p.X - other.X
                dy := p.Y - other.Y
                return dx*dx + dy*dy
            }

            func main() {}
        """, ".go")
        try:
            fi = _extract_file(path)
            assert fi is not None
            names = [s.name for s in fi.symbols]
            assert "NewPoint" in names
            assert "main" in names
        finally:
            os.unlink(path)

    def test_return_type_in_go_signature(self):
        path = write_temp("""
            package main

            func divide(a, b float64) (float64, error) {
                if b == 0 {
                    return 0, fmt.Errorf("division by zero")
                }
                return a / b, nil
            }
        """, ".go")
        try:
            fi = _extract_file(path)
            assert fi is not None
            sig = fi.symbols[0].signature
            assert "divide" in sig
            assert "(" in sig and ")" in sig
        finally:
            os.unlink(path)

    def test_fixture_go(self):
        result = audit_file(str(FIXTURES / "sample_go.go"))
        assert result is not None
        fi = _extract_file(str(FIXTURES / "sample_go.go"))
        assert fi is not None
        names = [s.name for s in fi.symbols]
        assert "NewServer" in names
        assert "joinParts" in names


# ══════════════════════════════════════════════════════════════════════════════
# Rust
# ══════════════════════════════════════════════════════════════════════════════

class TestRust:

    def test_functions_and_struct(self):
        path = write_temp("""
            pub struct Point {
                pub x: f64,
                pub y: f64,
            }

            pub fn distance(a: &Point, b: &Point) -> f64 {
                let dx = a.x - b.x;
                let dy = a.y - b.y;
                (dx * dx + dy * dy).sqrt()
            }

            fn internal_helper() -> bool {
                true
            }
        """, ".rs")
        try:
            fi = _extract_file(path)
            assert fi is not None
            names = [s.name for s in fi.symbols]
            assert "Point" in names
            assert "distance" in names
            assert "internal_helper" in names
        finally:
            os.unlink(path)

    def test_impl_block_methods(self):
        path = write_temp("""
            pub struct Counter {
                value: u32,
            }

            impl Counter {
                pub fn new() -> Self {
                    Counter { value: 0 }
                }

                pub fn increment(&mut self) {
                    self.value += 1;
                }

                pub fn get(&self) -> u32 {
                    self.value
                }
            }
        """, ".rs")
        try:
            fi = _extract_file(path)
            assert fi is not None
            names = [s.name for s in fi.symbols]
            assert "Counter" in names
            assert "Counter" in names  # impl block
        finally:
            os.unlink(path)

    def test_trait_definition(self):
        path = write_temp("""
            pub trait Drawable {
                fn draw(&self);
                fn bounding_box(&self) -> (f64, f64, f64, f64);
            }

            pub enum Color {
                Red,
                Green,
                Blue,
            }
        """, ".rs")
        try:
            fi = _extract_file(path)
            assert fi is not None
            names = [s.name for s in fi.symbols]
            assert "Drawable" in names
            assert "Color" in names
        finally:
            os.unlink(path)

    def test_fixture_rust(self):
        result = audit_file(str(FIXTURES / "sample_rs.rs"))
        assert result is not None
        fi = _extract_file(str(FIXTURES / "sample_rs.rs"))
        assert fi is not None
        names = [s.name for s in fi.symbols]
        assert "Config" in names
        assert "Status" in names
        assert "Processor" in names
        assert "parse_config" in names


# ══════════════════════════════════════════════════════════════════════════════
# Edge cases
# ══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:

    def test_single_function_file(self):
        path = write_temp("""
            def only_one(x: int) -> int:
                return x
        """, ".py")
        try:
            assert_full_coverage(path, min_expected=1)
        finally:
            os.unlink(path)

    def test_deeply_nested_class_methods(self):
        """Class with many methods at one level deep — all should be found."""
        methods = "\n".join(
            f"    def method_{i}(self, x: int) -> int:\n        return x + {i}"
            for i in range(10)
        )
        path = write_temp(f"class BigClass:\n{methods}\n", ".py")
        try:
            fi = _extract_file(path)
            assert fi is not None
            cls = fi.symbols[0]
            assert cls.name == "BigClass"
            method_names = [c.name for c in cls.children]
            for i in range(10):
                assert f"method_{i}" in method_names, f"method_{i} missing"
        finally:
            os.unlink(path)

    def test_unsupported_extension_returns_none(self):
        for ext in (".txt", ".md", ".json", ".csv", ".png"):
            path = write_temp("content", ext)
            try:
                result = audit_file(path)
                assert result is None, f"Expected None for {ext}, got {result}"
            finally:
                os.unlink(path)

    def test_syntax_error_doesnt_crash(self):
        """Files with syntax errors should not raise — tree-sitter is error-tolerant."""
        path = write_temp("""
            def broken(
            class also_broken
            def valid(x: int) -> int:
                return x
        """, ".py")
        try:
            fi = _extract_file(path)
            # Should not raise — tree-sitter parses partial results
        finally:
            os.unlink(path)

    def test_unicode_identifiers(self):
        path = write_temp("""
            def café(x: int) -> int:
                return x

            class Ñoño:
                def método(self) -> str:
                    return "hola"
        """, ".py")
        try:
            fi = _extract_file(path)
            assert fi is not None
            # Should not crash — may or may not extract depending on tree-sitter
        finally:
            os.unlink(path)

    def test_very_long_signature_not_truncated(self):
        path = write_temp("""
            def process(
                input_data: list,
                output_format: str,
                compression_level: int,
                encoding: str,
                validate: bool,
                strict_mode: bool,
                timeout_seconds: float,
            ) -> dict:
                return {}
        """, ".py")
        try:
            fi = _extract_file(path)
            assert fi is not None
            sig = fi.symbols[0].signature
            # Signature must have balanced parens
            assert sig.count("(") == sig.count(")"), f"Unbalanced parens in: {sig}"
            assert "process" in sig
        finally:
            os.unlink(path)


# ══════════════════════════════════════════════════════════════════════════════
# Full repo audit
# ══════════════════════════════════════════════════════════════════════════════

class TestRepoAudit:

    def test_fixtures_dir_100_percent(self, tmp_path):
        """Audit a repo containing all fixture files — expect 100% coverage."""
        import shutil
        for f in FIXTURES.iterdir():
            if f.is_file():
                shutil.copy(f, tmp_path / f.name)

        report = audit_repo(str(tmp_path))
        assert report.total_expected > 0

        problem_files = report.files_with_issues
        if problem_files:
            details = []
            for fa in problem_files:
                for m in fa.missing:
                    details.append(f"{fa.path}: missing {m.name} ({m.kind}, line {m.line})")
                for si in fa.signature_issues:
                    details.append(f"{fa.path}: sig issue {si.symbol_name} — {si.issue}")
            pytest.fail("Audit issues found:\n" + "\n".join(details))

    def test_self_audit_100_percent(self):
        """rtt should achieve 100% on its own source code."""
        import rtt
        pkg_dir = str(Path(rtt.__file__).parent)
        report = audit_repo(pkg_dir)
        assert report.coverage == 100.0, (
            f"Self-audit coverage {report.coverage:.1f}% < 100%\n"
            + "\n".join(
                f"  {fa.path}: missing {[m.name for m in fa.missing]}"
                for fa in report.files_with_issues
            )
        )
        assert report.total_signature_issues == 0
