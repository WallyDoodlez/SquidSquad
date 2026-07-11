"""Regression tests for #13517 — issue/PR TITLES are passed as a gh ``--title``
ARGV argument (gh has no ``--title-file``), so #13370's stdin fix for non-ASCII
BODIES cannot cover them. A non-ASCII title (em-dash U+2014, arrow, smart quote)
still crashed gh on a cp1252 Windows console. create_issue/create_task now
transliterate the title to ASCII (with an encode('ascii','replace') backstop)
before ``--title`` so gh can never crash on the argv.

Sibling of #13370 (bodies via stdin) and #13185 (crash-proof print surface).
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import tracker


def _ok(stdout="https://github.com/o/r/issues/7"):
    r = MagicMock()
    r.returncode = 0
    r.stdout = stdout
    r.stderr = ""
    return r


class TestAsciiizeTitle:
    def test_ascii_unchanged(self):
        assert tracker._asciiize_title("Plain ASCII title-123") == "Plain ASCII title-123"

    def test_em_dash(self):
        assert tracker._asciiize_title("fix — thing") == "fix -- thing"

    def test_en_dash(self):
        assert tracker._asciiize_title("a – b") == "a - b"

    def test_arrows(self):
        assert tracker._asciiize_title("x → y ← z ↔ w") == "x -> y <- z <-> w"

    def test_smart_quotes(self):
        assert tracker._asciiize_title("“it’s”") == '"it\'s"'

    def test_ellipsis_and_bullet_and_nbsp(self):
        assert tracker._asciiize_title("a…b") == "a...b"
        assert tracker._asciiize_title("x•y") == "x*y"
        assert tracker._asciiize_title("x y") == "x y"

    def test_residual_non_ascii_replaced_not_crashed(self):
        out = tracker._asciiize_title("cjk 中文 end")
        assert out.isascii()
        assert out == "cjk ?? end"

    def test_output_is_always_ascii(self):
        for t in ("plain", "em—dash", "中", "arrow→", "’quote"):
            assert tracker._asciiize_title(t).isascii()

    def test_none_passthrough(self):
        assert tracker._asciiize_title(None) is None


class TestCreateRoutesAsciiTitle:
    def _run_create(self, create_fn, *args):
        captured = {}

        def fake_run(cmd, **kw):
            if "create" in cmd:
                captured["cmd"] = cmd
                return _ok("https://github.com/o/r/issues/8")
            return _ok("[]")  # gh label list -> empty

        tracker._REPO_LABELS_CACHE = None
        with patch("tracker._resolve_gh_bin", return_value="gh"), \
             patch("tracker._get_forge_adapter", return_value=None), \
             patch("tracker.subprocess.run", side_effect=fake_run):
            create_fn(*args)
        tracker._REPO_LABELS_CACHE = None
        return captured["cmd"]

    def test_create_issue_title_is_ascii(self):
        cmd = self._run_create(
            tracker.create_issue, "crash on em-dash — here → now", "body", "skill", "low")
        title = cmd[cmd.index("--title") + 1]
        assert title.isascii(), f"title not ASCII-safe: {title!r}"
        assert "—" not in title and "→" not in title
        assert "ISSUE: crash on em-dash -- here -> now" == title

    def test_create_task_title_is_ascii(self):
        cmd = self._run_create(
            tracker.create_task, "task with smart ’quote’", "body", "skill", "medium")
        title = cmd[cmd.index("--title") + 1]
        assert title.isascii(), f"title not ASCII-safe: {title!r}"
        assert title == "TASK: task with smart 'quote'"

    def test_ascii_title_passes_through_unchanged(self):
        cmd = self._run_create(
            tracker.create_issue, "plain ascii title", "body", "skill", "low")
        title = cmd[cmd.index("--title") + 1]
        assert title == "ISSUE: plain ascii title"
