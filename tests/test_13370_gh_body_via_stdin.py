"""Regression tests for #13370 — tracker.py must pass agent-authored gh bodies
via `--body-file -` (UTF-8 stdin), not as an argv `--body`/`--message`, so a
non-ASCII body (em-dash U+2014, arrow U+2192) does not crash gh on a cp1252
Windows console.

Sibling of shipped #13185 (which crash-proofed the stdout/stderr PRINT surface —
a different call surface that did not cover this argv path).
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import tracker

# Non-ASCII body: em-dash + arrow (the exact class that crashed gh live).
EM_DASH_BODY = "Body with an em-dash — and an arrow → end."


def _ok(stdout="https://github.com/o/r/issues/7"):
    r = MagicMock()
    r.returncode = 0
    r.stdout = stdout
    r.stderr = ""
    return r


class TestRunGhWithBody:
    def test_body_goes_via_stdin_not_argv(self):
        captured = {}

        def fake_run(cmd, **kw):
            captured["cmd"] = cmd
            captured["input"] = kw.get("input")
            captured["encoding"] = kw.get("encoding")
            return _ok()

        with patch("tracker._resolve_gh_bin", return_value="gh"), \
             patch("tracker.subprocess.run", side_effect=fake_run):
            tracker._run_gh_with_body(["gh", "issue", "comment", "123"], EM_DASH_BODY)

        assert "--body-file" in captured["cmd"]
        assert captured["cmd"][captured["cmd"].index("--body-file") + 1] == "-"
        assert captured["input"] == EM_DASH_BODY          # body fed on stdin
        assert captured["encoding"] == "utf-8"
        assert EM_DASH_BODY not in captured["cmd"]         # never a bare argv arg
        assert "--body" not in captured["cmd"]


class TestCommentUsesStdin:
    def test_comment_routes_body_via_stdin(self):
        captured = {}

        def fake_run(cmd, **kw):
            captured["cmd"] = cmd
            captured["input"] = kw.get("input")
            return _ok()

        with patch("tracker._resolve_gh_bin", return_value="gh"), \
             patch("tracker._get_forge_adapter", return_value=None), \
             patch("tracker.subprocess.run", side_effect=fake_run):
            tracker.comment(123, "skill-lead (skill)", EM_DASH_BODY, _suppress_event=True)

        assert "--body-file" in captured["cmd"]
        assert EM_DASH_BODY in captured["input"]           # role-prefixed body on stdin
        assert "--body" not in captured["cmd"]
        assert EM_DASH_BODY not in captured["cmd"]


class TestCreateIssueUsesStdin:
    def test_create_issue_routes_body_via_stdin(self):
        captured = {}

        def fake_run(cmd, **kw):
            # _repo_labels() issues a `gh label list` first; only capture create.
            if "create" in cmd:
                captured["cmd"] = cmd
                captured["input"] = kw.get("input")
                return _ok("https://github.com/o/r/issues/8")
            return _ok("[]")  # label list -> empty -> filter falls back to primary

        tracker._REPO_LABELS_CACHE = None
        with patch("tracker._resolve_gh_bin", return_value="gh"), \
             patch("tracker._get_forge_adapter", return_value=None), \
             patch("tracker.subprocess.run", side_effect=fake_run):
            tracker.create_issue("title", EM_DASH_BODY, "skill", "low")

        assert "--body-file" in captured["cmd"]
        assert EM_DASH_BODY in captured["input"]
        assert "--body" not in captured["cmd"]
        tracker._REPO_LABELS_CACHE = None
