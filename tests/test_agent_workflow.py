"""
Agent workflow test - measures whether the skeleton prevents unnecessary file reads.

Core metric: does the agent request a file read (stop_reason="tool_use") or answer
directly from context (stop_reason="end_turn")?

Design: ONE API call per question per condition. No tool execution, no agentic loops,
no accumulating message history. The tool is declared so the model can call it if it
wants - but we only check whether it chose to, not execute it.

Total API calls: len(QUESTIONS) * 2 + 1 judge call = ~13 calls, ~$0.02.

Two conditions:
  A. No skeleton - agent has only the question
  B. With skeleton - agent has the rtt skeleton + question

Pass criteria:
  - Structural questions: agent should NOT request file reads when it has the skeleton
  - No condition should produce fewer correct answers than the other
    (quality check via one batch judge call)

Run with:
    ANTHROPIC_API_KEY=... python -m pytest tests/test_agent_workflow.py -v -s
"""
from __future__ import annotations
import os
import textwrap
from pathlib import Path

import pytest

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
pytestmark = pytest.mark.skipif(
    not ANTHROPIC_API_KEY,
    reason="ANTHROPIC_API_KEY not set",
)

REPO = "/Users/swastiklohchab/Desktop/Ventriko"

QUESTIONS = [
    # structural - skeleton has the full answer; agent should not need files
    {"q": "What API routes exist under src/app/api/admin/?",                                    "kind": "structural"},
    {"q": "Which files import from auth.authOptions?",                                          "kind": "structural"},
    {"q": "What functions are exported from src/app/api/_disabled/keys/route.ts?",              "kind": "structural"},
    # navigation - skeleton helps find the right file; agent may still open it
    {"q": "I want to add a new admin API endpoint. Which existing file should I model it on?",  "kind": "navigation"},
    {"q": "Where is email queuing handled? Which file should I look at to add a new email type?","kind": "navigation"},
    # implementation - must read source; skeleton cannot help
    {"q": "How exactly does the POST handler in the admin migrate route work?",                  "kind": "implementation"},
    {"q": "What does the emailQueue do when POST is called on process-emails?",                  "kind": "implementation"},
]

TOOL_DEF = {
    "name": "read_file",
    "description": "Read a source file from the repo when you need implementation details.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": f"Path relative to {REPO}, e.g. src/app/api/admin/migrate/route.ts"}
        },
        "required": ["path"],
    },
}

SYSTEM = (
    f"You are a coding assistant. The developer is working on a Next.js/TypeScript codebase at {REPO}. "
    "Use read_file only when you genuinely need implementation details to answer. "
    "If you can answer from what you already know or from context provided, do so directly."
)


def _ask_once(client, question: str, skeleton: str | None) -> dict:
    """Single API call. Returns whether agent wanted files and its token usage."""
    import time
    content = question
    if skeleton:
        content = (
            "I have a structural skeleton of this codebase below "
            "(imports, signatures, class hierarchies - no function bodies). "
            "Use it to answer structural questions directly without reading files.\n\n"
            f"{skeleton}\n\n---\n\n{question}"
        )

    for attempt in range(3):
        try:
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=300,
                system=SYSTEM,
                tools=[TOOL_DEF],
                messages=[{"role": "user", "content": content}],
            )
            break
        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(10 * (attempt + 1))

    wanted_files = resp.stop_reason == "tool_use"
    answer = " ".join(
        block.text for block in resp.content if hasattr(block, "text")
    ).strip()
    if wanted_files:
        files = [b.input.get("path", "?") for b in resp.content if b.type == "tool_use"]
        answer += f" [would read: {', '.join(files)}]"

    return {
        "wanted_files": wanted_files,
        "input_tokens": resp.usage.input_tokens,
        "answer": answer,
    }


def _batch_judge(client, rows: list[dict]) -> dict[int, str]:
    """One call to judge answer quality for all questions. Returns {idx: GOOD|PARTIAL|WRONG}."""
    pairs = "\n\n".join(
        f"Q{i+1} [{r['kind']}]: {r['question']}\n"
        f"Answer A (no skeleton): {r['a_answer'][:250]}\n"
        f"Answer B (with skeleton): {r['b_answer'][:250]}"
        for i, r in enumerate(rows)
    )
    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{"role": "user", "content": (
            "Rate each answer. One line per question, exact format:\n"
            "Q<n>: A=GOOD|PARTIAL|WRONG B=GOOD|PARTIAL|WRONG\n\n"
            + pairs
        )}],
    )
    out = {}
    for line in resp.content[0].text.strip().splitlines():
        if line.startswith("Q") and "A=" in line and "B=" in line:
            try:
                n     = int(line.split(":")[0][1:]) - 1
                a_val = line.split("A=")[1].split()[0].strip(",.").upper()
                b_val = line.split("B=")[1].split()[0].strip(",.").upper()
                out[n] = {"a": a_val, "b": b_val}
            except Exception:
                pass
    return out


def test_agent_workflow(capsys):
    import anthropic
    from rtt.extractor import extract_repo
    from rtt.formatter import format_text
    from rtt.tokenizer import count_tokens

    assert Path(REPO).exists(), f"Repo not found at {REPO}"

    repo        = extract_repo(REPO, use_cache=True, no_tests=True)
    skeleton    = format_text(repo)
    skel_tokens = count_tokens(skeleton)
    client      = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    rows = []

    with capsys.disabled():
        print(f"\n{'='*65}")
        print(f"Agent workflow - Ventriko ({len(repo.files)} files, {skel_tokens:,} token skeleton)")
        print(f"One API call per question per condition. No loops.")
        print(f"{'='*65}\n")

        for i, item in enumerate(QUESTIONS, 1):
            q, kind = item["q"], item["kind"]
            a = _ask_once(client, q, skeleton=None)
            b = _ask_once(client, q, skeleton=skeleton)

            saved = a["input_tokens"] - b["input_tokens"]
            print(f"[{i}/{len(QUESTIONS)}] {kind.upper()}")
            print(f"  Q: {q}")
            print(f"  No skeleton:   {a['input_tokens']:>5,} tok  files={'YES' if a['wanted_files'] else 'no '}")
            print(f"  With skeleton: {b['input_tokens']:>5,} tok  files={'YES' if b['wanted_files'] else 'no '}  (skeleton overhead: +{skel_tokens:,})")
            print(f"  Token delta:   {saved:>+,}")
            print()

            rows.append({
                "question": q, "kind": kind,
                "a_tokens": a["input_tokens"], "b_tokens": b["input_tokens"],
                "a_files":  a["wanted_files"],  "b_files":  b["wanted_files"],
                "a_answer": a["answer"],         "b_answer": b["answer"],
            })

        print("Judging answer quality (1 API call)...")
        quality = _batch_judge(client, rows)
        for i, r in enumerate(rows):
            r["a_quality"] = quality.get(i, {}).get("a", "?")
            r["b_quality"] = quality.get(i, {}).get("b", "?")

        # ── Summary ──────────────────────────────────────────────────────────
        total_a = sum(r["a_tokens"] for r in rows)
        total_b = sum(r["b_tokens"] for r in rows)

        by_kind: dict = {}
        for r in rows:
            k = r["kind"]
            if k not in by_kind:
                by_kind[k] = {"a_tok": 0, "b_tok": 0, "a_files": 0, "b_files": 0, "n": 0}
            by_kind[k]["a_tok"]   += r["a_tokens"]
            by_kind[k]["b_tok"]   += r["b_tokens"]
            by_kind[k]["a_files"] += r["a_files"]
            by_kind[k]["b_files"] += r["b_files"]
            by_kind[k]["n"]       += 1

        print(f"\n{'='*65}")
        print("SUMMARY")
        print(f"{'='*65}")
        print(f"\n  {'Kind':<18} {'N':>2}  {'No-skel tok':>11}  {'W/skel tok':>10}  {'File reads A→B':>14}")
        print(f"  {'-'*18} {'-'*2}  {'-'*11}  {'-'*10}  {'-'*14}")
        for kind, d in sorted(by_kind.items()):
            print(f"  {kind:<18} {d['n']:>2}  {d['a_tok']:>11,}  {d['b_tok']:>10,}  {d['a_files']} → {d['b_files']}")
        print(f"\n  {'TOTAL':<18} {len(rows):>2}  {total_a:>11,}  {total_b:>10,}")
        print(f"\n  Skeleton added {skel_tokens:,} tokens to each condition-B prompt.")
        net = (total_a - total_b) - skel_tokens * len(rows)
        print(f"  Net token delta (saved minus overhead): {net:,}")

        print(f"\n  Answer quality:")
        for r in rows:
            reg = "  <-- WORSE" if r["b_quality"] == "WRONG" and r["a_quality"] != "WRONG" else ""
            print(f"  [{r['kind']:>14}]  A={r['a_quality']:<7} B={r['b_quality']:<7}  {r['question'][:52]}{reg}")
        print(f"\n{'='*65}\n")

    # ── Assertions ────────────────────────────────────────────────────────────
    structural     = [r for r in rows if r["kind"] == "structural"]
    files_a_struct = sum(r["a_files"] for r in structural)
    files_b_struct = sum(r["b_files"] for r in structural)

    assert files_b_struct < files_a_struct, (
        f"Skeleton did not reduce file reads on structural questions: "
        f"{files_a_struct} reads without skeleton, {files_b_struct} with. "
        f"The instruction is not working."
    )

    regressions = [r for r in rows if r["b_quality"] == "WRONG" and r["a_quality"] != "WRONG"]
    assert not regressions, (
        f"Skeleton caused {len(regressions)} quality regression(s):\n"
        + "\n".join(f"  {r['question']}" for r in regressions)
    )
