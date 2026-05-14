import textwrap
import tempfile
import os
from pathlib import Path

from rtt.extractor import _extract_file
from rtt.formatter import format_file_text, format_file_markdown


def write_temp(content: str, suffix: str) -> str:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False)
    f.write(content)
    f.flush()
    return f.name


def test_python_function():
    code = textwrap.dedent("""
        def greet(name: str) -> str:
            \"\"\"Say hello.\"\"\"
            return f"Hello {name}"

        class Greeter:
            def hello(self, name: str) -> None:
                pass
    """)
    path = write_temp(code, ".py")
    try:
        fi = _extract_file(path)
        assert fi is not None
        assert fi.language == "python"
        names = [s.name for s in fi.symbols]
        assert "greet" in names
        assert "Greeter" in names
        greet = next(s for s in fi.symbols if s.name == "greet")
        assert greet.docstring == "Say hello."
    finally:
        os.unlink(path)


def test_format_text():
    from rtt import FileIndex, Symbol
    fi = FileIndex(
        path="src/foo.py",
        language="python",
        imports=["os", "sys"],
        symbols=[
            Symbol(name="bar", kind="function", signature="def bar(x: int) -> str", docstring="Does bar.")
        ]
    )
    text = format_file_text(fi)
    assert "src/foo.py" in text
    assert "def bar(x: int) -> str" in text
    assert "Does bar." in text


def test_format_markdown():
    from rtt import FileIndex, Symbol
    fi = FileIndex(
        path="src/foo.py",
        language="python",
        imports=["os"],
        symbols=[Symbol(name="bar", kind="function", signature="def bar(x: int) -> str")]
    )
    md = format_file_markdown(fi)
    assert "## `src/foo.py`" in md
    assert "bar" in md


def test_token_count():
    from rtt.tokenizer import count_tokens
    n = count_tokens("hello world")
    assert n > 0
