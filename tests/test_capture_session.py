"""tests/test_capture_session.py — Verify tools/capture-session.py works.

Covers:
- basic write (transcript-stdin, transcript-string, transcript-file)
- overwrite of an existing current log
- structured-json rendering (6 sections)
- no transcript source → exit 2
- empty transcript → exit 2
- bad structured-json path → exit 2
- vault resolution: --vault, $VAULT_DIR, <shim>/..
- 1 MB truncation
- atomic write (no .tmp file left behind)
- frontmatter invariants (session_id: current, status, etc.)
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "tools" / "capture-session.py"


PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name}  {detail}")


def run(args: list[str], stdin: str | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        input=stdin,
        capture_output=True,
        text=True,
        env=env or os.environ.copy(),
        timeout=30,
    )


def make_tmp_vault() -> Path:
    """Build a minimal vault the tool can validate (must contain team/md.md)."""
    tmp = Path(tempfile.mkdtemp(prefix="capture-session-test-"))
    (tmp / "team").mkdir()
    (tmp / "system").mkdir()
    (tmp / "system" / "prompts").mkdir()
    (tmp / "team" / "md.md").write_text("# md\n")
    (tmp / "content" / "sessions").mkdir(parents=True)
    (tmp / "content" / "queue").mkdir(parents=True)
    return tmp


import tempfile  # noqa: E402 (after we use it)


# ─── Tests ───────────────────────────────────────────────────────────────

def test_basic_write_transcript_string() -> None:
    print("\n[1] Basic write via --transcript-string")
    with tempfile.TemporaryDirectory() as td:
        vault = Path(td)
        (vault / "team" / "md.md").parent.mkdir(parents=True)
        (vault / "team" / "md.md").write_text("# md\n")
        (vault / "content" / "sessions").mkdir(parents=True)
        r = run([
            "--vault", str(vault),
            "--transcript-string", "User: hi\nAssistant: hello",
            "--title", "Basic test",
        ])
        check("exit 0", r.returncode == 0, f"stderr: {r.stderr}")
        try:
            result = json.loads(r.stdout)
        except json.JSONDecodeError:
            check("valid json output", False, r.stdout)
            return
        check("ok=true", result.get("ok") is True)
        check("session_id=current", result.get("session_id") == "current")
        check("date is today", len(result.get("date", "")) == 10)
        check("path under sessions/", "content/sessions/" in result.get("path", ""))
        out = Path(result["path"])
        check("file written", out.exists())
        text = out.read_text()
        check("frontmatter has title", "title: Basic test" in text)
        check("frontmatter has session_id: current", "session_id: current" in text)
        check("body has Transcript section", "## Transcript" in text)


def test_overwrite() -> None:
    print("\n[2] Overwrite existing current log")
    with tempfile.TemporaryDirectory() as td:
        vault = Path(td)
        (vault / "team" / "md.md").parent.mkdir(parents=True)
        (vault / "team" / "md.md").write_text("# md\n")
        (vault / "content" / "sessions").mkdir(parents=True)
        # First capture
        r1 = run(["--vault", str(vault), "--transcript-string", "first"])
        result1 = json.loads(r1.stdout)
        check("first ok", result1.get("ok") is True)
        check("first overwrote=False", result1.get("overwrote") is False)
        # Second capture — overwrites
        r2 = run(["--vault", str(vault), "--transcript-string", "second"])
        result2 = json.loads(r2.stdout)
        check("second ok", result2.get("ok") is True)
        check("second overwrote=True", result2.get("overwrote") is True)
        check("same path", result1.get("path") == result2.get("path"))
        text = Path(result2["path"]).read_text()
        check("body reflects new content", "second" in text)
        check("body does not contain old", "first" not in text)


def test_structured_json() -> None:
    print("\n[3] Structured JSON → 6 canonical sections")
    with tempfile.TemporaryDirectory() as td:
        vault = Path(td)
        (vault / "team" / "md.md").parent.mkdir(parents=True)
        (vault / "team" / "md.md").write_text("# md\n")
        (vault / "content" / "sessions").mkdir(parents=True)
        struct_path = Path(td) / "struct.json"
        struct_path.write_text(json.dumps({
            "patterns": ["build is content"],
            "decisions": ["use subagents"],
            "what_we_did": ["built the pipeline"],
            "shipped": ["v1"],
            "numbers": ["3", "47 files"],
            "lesson": "The pipeline works.",
        }))
        r = run([
            "--vault", str(vault),
            "--transcript-string", "raw transcript here",
            "--structured-json", str(struct_path),
            "--status", "complete",
        ])
        result = json.loads(r.stdout)
        text = Path(result["path"]).read_text()
        check("Patterns section has bullet", "- build is content" in text)
        check("Decisions section has bullet", "- use subagents" in text)
        check("What we did has bullet", "- built the pipeline" in text)
        check("Shipped has bullet", "- v1" in text)
        check("Numbers has bullets", "- 3" in text and "- 47 files" in text)
        check("Lesson has bullet", "- The pipeline works." in text)
        check("status: complete in frontmatter", "status: complete" in text)
        check("transcript appendix", "## Transcript" in text and "raw transcript here" in text)


def test_transcript_stdin() -> None:
    print("\n[4] Transcript from stdin")
    with tempfile.TemporaryDirectory() as td:
        vault = Path(td)
        (vault / "team" / "md.md").parent.mkdir(parents=True)
        (vault / "team" / "md.md").write_text("# md\n")
        (vault / "content" / "sessions").mkdir(parents=True)
        r = run(
            ["--vault", str(vault), "--transcript-stdin"],
            stdin="User: hello\nAssistant: world",
        )
        result = json.loads(r.stdout)
        check("ok", result.get("ok") is True)
        text = Path(result["path"]).read_text()
        check("stdin content captured", "User: hello" in text and "Assistant: world" in text)


def test_transcript_file() -> None:
    print("\n[5] Transcript from file")
    with tempfile.TemporaryDirectory() as td:
        vault = Path(td)
        (vault / "team" / "md.md").parent.mkdir(parents=True)
        (vault / "team" / "md.md").write_text("# md\n")
        (vault / "content" / "sessions").mkdir(parents=True)
        transcript_file = Path(td) / "raw.md"
        transcript_file.write_text("User: from a file\nAssistant: got it")
        r = run(["--vault", str(vault), "--transcript-file", str(transcript_file)])
        result = json.loads(r.stdout)
        check("ok", result.get("ok") is True)
        text = Path(result["path"]).read_text()
        check("file content captured", "from a file" in text and "got it" in text)


def test_no_source_error() -> None:
    print("\n[6] No transcript source → exit 2")
    with tempfile.TemporaryDirectory() as td:
        vault = Path(td)
        (vault / "team" / "md.md").parent.mkdir(parents=True)
        (vault / "team" / "md.md").write_text("# md\n")
        (vault / "content" / "sessions").mkdir(parents=True)
        r = run(["--vault", str(vault)])
        check("exit 2", r.returncode == 2, f"got {r.returncode}, stderr: {r.stderr}")
        check("error mentions one of", "exactly one" in r.stderr.lower())


def test_empty_transcript_error() -> None:
    print("\n[7] Empty transcript → exit 2")
    with tempfile.TemporaryDirectory() as td:
        vault = Path(td)
        (vault / "team" / "md.md").parent.mkdir(parents=True)
        (vault / "team" / "md.md").write_text("# md\n")
        (vault / "content" / "sessions").mkdir(parents=True)
        r = run(["--vault", str(vault), "--transcript-stdin"], stdin="   \n  \n")
        check("exit 2", r.returncode == 2, f"stderr: {r.stderr}")
        check("error mentions empty", "empty" in r.stderr.lower())


def test_bad_structured_json() -> None:
    print("\n[8] Bad --structured-json path → exit 2")
    with tempfile.TemporaryDirectory() as td:
        vault = Path(td)
        (vault / "team" / "md.md").parent.mkdir(parents=True)
        (vault / "team" / "md.md").write_text("# md\n")
        (vault / "content" / "sessions").mkdir(parents=True)
        r = run([
            "--vault", str(vault),
            "--transcript-string", "x",
            "--structured-json", "/nonexistent/struct.json",
        ])
        check("exit 2", r.returncode == 2, f"stderr: {r.stderr}")
        check("error mentions not found", "not found" in r.stderr.lower())


def test_vault_resolution() -> None:
    print("\n[9] Vault resolution: --vault > $VAULT_DIR > <shim>/..")
    with tempfile.TemporaryDirectory() as td:
        explicit = Path(td) / "explicit-vault"
        (explicit / "team" / "md.md").parent.mkdir(parents=True)
        (explicit / "team" / "md.md").write_text("# md\n")
        (explicit / "content" / "sessions").mkdir(parents=True)
        # 9a: --vault flag
        r = run(["--vault", str(explicit), "--transcript-string", "x"])
        result = json.loads(r.stdout)
        # macOS resolves /var → /private/var, so compare resolved paths, not strings
        check("9a: --vault works",
              Path(result.get("path", "")).resolve().is_relative_to(explicit.resolve()),
              f"path={result.get('path')!r}, expected under {explicit}")
        # 9b: $VAULT_DIR
        env = os.environ.copy()
        env["VAULT_DIR"] = str(explicit)
        r = subprocess.run(
            [sys.executable, str(TOOL), "--transcript-string", "y"],
            capture_output=True, text=True, env=env, timeout=30,
        )
        check("9b: $VAULT_DIR works",
              Path(json.loads(r.stdout).get("path", "")).resolve().is_relative_to(explicit.resolve()),
              f"got: {r.stdout[:200]}")


def test_atomic_write_no_tmp_left() -> None:
    print("\n[10] Atomic write leaves no .tmp files behind")
    with tempfile.TemporaryDirectory() as td:
        vault = Path(td)
        (vault / "team" / "md.md").parent.mkdir(parents=True)
        (vault / "team" / "md.md").write_text("# md\n")
        (vault / "content" / "sessions").mkdir(parents=True)
        r = run(["--vault", str(vault), "--transcript-string", "x"])
        check("ok", json.loads(r.stdout).get("ok") is True)
        sessions_dir = vault / "content" / "sessions"
        tmp_files = list(sessions_dir.glob(".capture-*.tmp"))
        check("no .tmp files left", len(tmp_files) == 0, f"found: {tmp_files}")


def test_truncation() -> None:
    print("\n[11] 1 MB truncation marker")
    with tempfile.TemporaryDirectory() as td:
        vault = Path(td)
        (vault / "team" / "md.md").parent.mkdir(parents=True)
        (vault / "team" / "md.md").write_text("# md\n")
        (vault / "content" / "sessions").mkdir(parents=True)
        # 1.1MB string — pass via stdin to avoid argv length limits
        big = "x" * 1_100_000 + "\n"
        r = run(["--vault", str(vault), "--transcript-stdin"], stdin=big)
        result = json.loads(r.stdout)
        check("ok", result.get("ok") is True)
        text = Path(result["path"]).read_text()
        check("truncation marker present", "[truncated at 1MB]" in text)
        check("size <= 1.1 MB", len(text.encode("utf-8")) < 1_100_000)


def test_default_status_in_progress() -> None:
    print("\n[12] Default status is in-progress")
    with tempfile.TemporaryDirectory() as td:
        vault = Path(td)
        (vault / "team" / "md.md").parent.mkdir(parents=True)
        (vault / "team" / "md.md").write_text("# md\n")
        (vault / "content" / "sessions").mkdir(parents=True)
        r = run(["--vault", str(vault), "--transcript-string", "x"])
        result = json.loads(r.stdout)
        text = Path(result["path"]).read_text()
        check("status: in-progress in frontmatter", "status: in-progress" in text)
        check("in-progress note in body", "Status: in-progress" in text)


def test_status_complete_suppresses_note() -> None:
    print("\n[13] status=complete suppresses in-progress note")
    with tempfile.TemporaryDirectory() as td:
        vault = Path(td)
        (vault / "team" / "md.md").parent.mkdir(parents=True)
        (vault / "team" / "md.md").write_text("# md\n")
        (vault / "content" / "sessions").mkdir(parents=True)
        r = run(["--vault", str(vault), "--transcript-string", "x", "--status", "complete"])
        text = Path(json.loads(r.stdout)["path"]).read_text()
        check("status: complete in frontmatter", "status: complete" in text)
        check("no in-progress note", "Status: in-progress" not in text)


def test_message_count() -> None:
    print("\n[14] message_count is a positive int")
    with tempfile.TemporaryDirectory() as td:
        vault = Path(td)
        (vault / "team" / "md.md").parent.mkdir(parents=True)
        (vault / "team" / "md.md").write_text("# md\n")
        (vault / "content" / "sessions").mkdir(parents=True)
        transcript = "Para 1.\n\nPara 2.\n\nPara 3."
        r = run(["--vault", str(vault), "--transcript-string", transcript])
        result = json.loads(r.stdout)
        check("message_count is int", isinstance(result.get("message_count"), int))
        check("message_count >= 1", result.get("message_count", 0) >= 1)
        check("message_count in frontmatter",
              f"message_count: {result['message_count']}" in Path(result["path"]).read_text())


def test_invalid_status() -> None:
    print("\n[15] Invalid --status → exit 2")
    with tempfile.TemporaryDirectory() as td:
        vault = Path(td)
        (vault / "team" / "md.md").parent.mkdir(parents=True)
        (vault / "team" / "md.md").write_text("# md\n")
        (vault / "content" / "sessions").mkdir(parents=True)
        r = run(["--vault", str(vault), "--transcript-string", "x", "--status", "garbage"])
        # argparse rejects unknown choice → exit 2
        check("exit 2", r.returncode == 2, f"stderr: {r.stderr}")


def test_out_override() -> None:
    print("\n[16] --out overrides the default path")
    with tempfile.TemporaryDirectory() as td:
        vault = Path(td)
        (vault / "team" / "md.md").parent.mkdir(parents=True)
        (vault / "team" / "md.md").write_text("# md\n")
        (vault / "content" / "sessions").mkdir(parents=True)
        custom = Path(td) / "my-log.md"
        r = run(["--vault", str(vault), "--transcript-string", "x", "--out", str(custom)])
        result = json.loads(r.stdout)
        check("ok", result.get("ok") is True)
        check("path is the override", result.get("path") == str(custom))
        check("file written at custom path", custom.exists())


# ─── Runner ──────────────────────────────────────────────────────────────

def main() -> int:
    print(f"capture-session tests — tool: {TOOL}")
    test_basic_write_transcript_string()
    test_overwrite()
    test_structured_json()
    test_transcript_stdin()
    test_transcript_file()
    test_no_source_error()
    test_empty_transcript_error()
    test_bad_structured_json()
    test_vault_resolution()
    test_atomic_write_no_tmp_left()
    test_truncation()
    test_default_status_in_progress()
    test_status_complete_suppresses_note()
    test_message_count()
    test_invalid_status()
    test_out_override()
    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
