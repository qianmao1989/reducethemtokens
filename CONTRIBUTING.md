# Contributing to rtt

Thanks for your interest. rtt is a small, focused tool and contributions are welcome.

## Getting started

```bash
git clone https://github.com/yttrium400/reducethemtokens
cd reducethemtokens
pip install -e ".[dev]"
pytest tests/   # should all pass
```

## What to work on

Open issues are the best place to start. Issues tagged `good first issue` are deliberately self-contained - each one has a step-by-step breakdown of exactly what to change.

The most common contribution type is **adding a new language**. Each language follows the same pattern:

1. Add the `tree-sitter-<lang>` package to `pyproject.toml`
2. Create `rtt/languages/<lang>_lang.py` with `extract_fn_signature()` and `extract_class_signature()` - copy any existing module as a template
3. Register it in `rtt/languages/registry.py` and `rtt/languages/__init__.py`
4. Add `"<lang>"` to the relevant `lang_name in (...)` checks in `rtt/extractor.py`
5. Add entries to `SYMBOL_NODE_TYPES` and `_FUNCTION_BODY_TYPES` in `rtt/audit.py`
6. Add a fixture file under `tests/fixtures/` and a test in `tests/test_extractor.py`

Look at `rtt/languages/python_lang.py` and its corresponding test as a reference.

## Running tests

```bash
pytest tests/                        # all tests (~0.3s, no network)
pytest tests/test_extractor.py       # extraction only
pytest tests/ -k "test_python"       # single test by name
```

The controlled accuracy test requires an API key and is skipped by default:

```bash
ANTHROPIC_API_KEY=... pytest tests/test_accuracy_controlled.py -v -s
```

## Submitting a PR

- Keep the scope tight - one issue per PR
- Make sure `pytest tests/` passes before opening
- Add a test for anything you add (there are 91 already, adding one more is easy)
- No need to update CHANGELOG - that gets done at release time

## Code style

- No em dashes in comments or strings, use a regular hyphen instead
- No multi-line docstrings - one short line max
- No comments explaining what the code does - only add one if the why is non-obvious
