"""Unit tests for the #9398 Phase A gh PATH-shim.

The shim lives at ``tests/integration/fixtures/gh_shim/gh_main.py``
and is the foundation for the work-pickup half of AC-3 M-3.2 (real
agent subprocess invokes ``tracker.py`` → ``gh issue list ...``;
shim returns canned issues; assert agent picks up the top item).

These tests exercise the shim directly via subprocess. The
integration with a real agent + harness lives in
``tests/integration/test_9398_real_agent_subprocess.py`` once the
work-pickup test lands.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GH_SHIM_DIR = REPO_ROOT / "tests" / "integration" / "fixtures" / "gh_shim"
GH_MAIN = GH_SHIM_DIR / "gh_main.py"


def _run_shim(args: list[str], fixtures_dir: Path | None = None,
              extra_env: dict[str, str] | None = None
              ) -> subprocess.CompletedProcess:
    """Invoke gh_main.py directly (skips the platform-specific entry
    wrapper). The wrapper just forwards argv so testing the inner
    script is equivalent for behavioral coverage."""
    env = dict(os.environ)
    if fixtures_dir is not None:
        env["GH_SHIM_FIXTURES_DIR"] = str(fixtures_dir)
    if extra_env:
        env.update(extra_env)
    # The shim's main() consumes argv[1:] as the gh args (matching
    # how the .cmd/.sh entry point invokes it: `python gh_main.py %*`).
    # Don't prepend an extra "gh" — that would shift the argument
    # parsing by one and make every subcommand look like a leading
    # extra topic.
    return subprocess.run(
        [sys.executable, str(GH_MAIN)] + args,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        check=False,
    )


class TestGhShimReadCommands(unittest.TestCase):
    def test_list_returns_empty_array_when_no_fixture(self):
        """``gh issue list ...`` without a fixture file must return
        ``[]\\n`` so tracker.py's JSON parse succeeds and the agent
        sees 'no work'. Anything else (HTTP error, malformed JSON,
        crash) would break the agent's boot path."""
        result = _run_shim(["issue", "list", "--label", "role:skill"])
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "[]")

    def test_view_returns_empty_object_when_no_fixture(self):
        """``gh issue view N ...`` without a fixture returns ``{}``."""
        result = _run_shim(["issue", "view", "42", "--json", "labels"])
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "{}")

    def test_list_serves_default_fixture_when_present(self):
        """When ``GH_SHIM_FIXTURES_DIR/issue-list/default.json``
        exists, ``gh issue list`` returns its contents verbatim."""
        with tempfile.TemporaryDirectory() as tmp:
            fdir = Path(tmp)
            (fdir / "issue-list").mkdir()
            payload = [{"number": 42, "title": "test", "labels": []}]
            (fdir / "issue-list" / "default.json").write_text(
                json.dumps(payload), encoding="utf-8"
            )
            result = _run_shim(
                ["issue", "list", "--label", "role:skill"],
                fixtures_dir=fdir,
            )
            self.assertEqual(result.returncode, 0)
            parsed = json.loads(result.stdout)
            self.assertEqual(parsed, payload)

    def test_view_keyed_by_issue_number(self):
        """``gh issue view 99`` reads from
        ``GH_SHIM_FIXTURES_DIR/issue-view/99.json`` — keyed by the
        issue number, not the literal string 'default'."""
        with tempfile.TemporaryDirectory() as tmp:
            fdir = Path(tmp)
            (fdir / "issue-view").mkdir()
            (fdir / "issue-view" / "99.json").write_text(
                '{"number":99,"state":"open"}', encoding="utf-8"
            )
            result = _run_shim(
                ["issue", "view", "99", "--json", "state"],
                fixtures_dir=fdir,
            )
            self.assertEqual(result.returncode, 0)
            parsed = json.loads(result.stdout)
            self.assertEqual(parsed["number"], 99)

    def test_list_key_overridable_by_env(self):
        """Tests serving multiple list responses in sequence set
        ``GH_SHIM_LIST_KEY`` to swap the fixture key between
        invocations without rewriting the default.json file."""
        with tempfile.TemporaryDirectory() as tmp:
            fdir = Path(tmp)
            (fdir / "issue-list").mkdir()
            (fdir / "issue-list" / "after-pickup.json").write_text(
                "[]", encoding="utf-8"
            )
            result = _run_shim(
                ["issue", "list", "--label", "role:skill"],
                fixtures_dir=fdir,
                extra_env={"GH_SHIM_LIST_KEY": "after-pickup"},
            )
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout.strip(), "[]")


class TestGhShimWriteCommands(unittest.TestCase):
    def test_edit_logs_write_to_fixtures_dir(self):
        """``gh issue edit ...`` (a write-type command) appends a
        JSON line to ``GH_SHIM_FIXTURES_DIR/_writes.log`` so tests
        can assert on the agent's transition activity."""
        with tempfile.TemporaryDirectory() as tmp:
            fdir = Path(tmp)
            result = _run_shim(
                ["issue", "edit", "42",
                 "--remove-label", "status:approved",
                 "--add-label", "status:in-progress"],
                fixtures_dir=fdir,
            )
            self.assertEqual(result.returncode, 0)
            log = fdir / "_writes.log"
            self.assertTrue(log.exists())
            line = log.read_text(encoding="utf-8").strip()
            entry = json.loads(line)
            self.assertEqual(entry["verb"], "edit")
            self.assertIn("--add-label", entry["args"])
            self.assertIn("status:in-progress", entry["args"])

    def test_comment_logs_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            fdir = Path(tmp)
            result = _run_shim(
                ["issue", "comment", "42", "--body", "hi"],
                fixtures_dir=fdir,
            )
            self.assertEqual(result.returncode, 0)
            log = fdir / "_writes.log"
            entry = json.loads(log.read_text(encoding="utf-8").strip())
            self.assertEqual(entry["verb"], "comment")

    def test_write_without_fixtures_dir_succeeds_silently(self):
        """Agents call ``gh issue edit`` fire-and-forget on many
        paths. The shim must not crash when no fixtures dir is
        configured — return 0 with no log file."""
        result = _run_shim(
            ["issue", "edit", "42", "--add-label", "status:shipped"],
        )
        self.assertEqual(result.returncode, 0)


class TestGhShimMetaCommands(unittest.TestCase):
    def test_version_flag(self):
        """tracker.py / other tooling may probe ``gh --version``
        before doing real work. Shim must return 0."""
        result = _run_shim(["--version"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("gh-shim", result.stdout.lower())

    def test_no_args_fails_loudly(self):
        """Empty argv (just `gh`) is a programming error — shim
        exits non-zero so the test sees the bug instead of silently
        passing."""
        result = _run_shim([])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing subcommand", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
