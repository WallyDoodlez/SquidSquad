"""Independent verifier tests for #13370 — tracker.py gh body via UTF-8 stdin (not argv).

Hermetic mechanism check (the definitive LIVE E2E round-trip — real create+comment
with em-dash/arrow/smart-quotes surviving intact on cp1252 Windows, artifact #13495 —
was run once during verification and recorded in QA-RESULTS-13370.md).

Verifies the fix mechanism: agent-authored prose bodies are passed to gh via
`--body-file -` on stdin, never as a `--body`/`--message` argv argument (the
cp1252-mangling path). Non-ASCII input must reach subprocess.run's `input=` intact.
"""
import sys
from pathlib import Path

import pytest


def _find_repo_root(start):
    for p in [start, *start.parents]:
        if (p / "references" / "scripts" / "tracker.py").exists():
            return p
    raise RuntimeError("could not locate repo root")


REPO_ROOT = _find_repo_root(Path(__file__).resolve())
SCRIPTS = REPO_ROOT / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import tracker  # noqa: E402

NON_ASCII = "body with em-dash — arrow → quotes “x”"


class _FakeCompleted:
    returncode = 0
    stdout = ""
    stderr = ""


@pytest.fixture
def capture_run(monkeypatch):
    calls = {}

    def fake_run(cmd, *args, **kwargs):
        calls["cmd"] = cmd
        calls["input"] = kwargs.get("input")
        calls["encoding"] = kwargs.get("encoding")
        return _FakeCompleted()

    monkeypatch.setattr(tracker.subprocess, "run", fake_run)
    return calls


def test_body_passed_via_body_file_stdin_not_argv(capture_run):
    """Body goes through --body-file - on stdin, never as a --body/--message argv arg."""
    tracker._run_gh_with_body(["gh", "issue", "comment", "1"], NON_ASCII, check=False)
    cmd = capture_run["cmd"]
    assert cmd[-2:] == ["--body-file", "-"], cmd
    assert "--body" not in cmd and "--message" not in cmd, cmd
    # The non-ASCII body must be fed on stdin intact (not mangled into argv).
    assert capture_run["input"] == NON_ASCII
    assert "—" in capture_run["input"] and "→" in capture_run["input"]


def test_stdin_encoding_is_utf8(capture_run):
    """The child's stdin encoding is UTF-8 so any Unicode body round-trips."""
    tracker._run_gh_with_body(["gh", "issue", "comment", "1"], NON_ASCII, check=False)
    assert capture_run["encoding"] == "utf-8"


def test_no_nonascii_body_left_in_argv(capture_run):
    """No element of the gh argv carries the non-ASCII prose (the crash path)."""
    tracker._run_gh_with_body(["gh", "issue", "comment", "1"], NON_ASCII, check=False)
    assert all("—" not in str(a) for a in capture_run["cmd"])


def test_regression_test_present():
    """Worker ships a regression test for the stdin body path."""
    wt = REPO_ROOT / "tests" / "test_13370_gh_body_via_stdin.py"
    assert wt.exists(), "worker regression test missing"
    txt = wt.read_text().lower()
    assert "body-file" in txt or "stdin" in txt or "input" in txt
