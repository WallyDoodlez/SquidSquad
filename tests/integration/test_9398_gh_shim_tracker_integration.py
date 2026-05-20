"""Integration tests: gh PATH-shim ↔ tracker.py CLI handshake (#9398 Phase A).

The gh shim itself is unit-tested in
``tests/test_9398_gh_shim.py``. This test exercises the next layer
up: when ``tracker.py`` is invoked as a subprocess with the shim
prepended to ``PATH``, does its ``gh issue list ...`` call get
intercepted, get the canned response, and parse it correctly?

That contract is the load-bearing piece for the §4.1 work-pickup
test that lands next: a real agent subprocess shells out to
``tracker.py list-tasks`` from inside ``cycle_pre``. If the
shim's response shape disagrees with what ``tracker.py``'s JSON
parse expects, the agent sees malformed data and the test fails
in a confusing way far from the root cause. Pin the contract
here first.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "tests" / "integration"))

from fixtures import event_mode_subprocess as ems  # noqa: E402

TRACKER_PY = REPO_ROOT / "references" / "scripts" / "tracker.py"


class TestTrackerListTasksThroughShim(unittest.TestCase):
    """``tracker.py list-tasks <role> --status approved`` shells out
    to ``gh issue list --label LABEL --state open --json
    number,title,labels --limit 50``. The shim must intercept that
    call and the canned response must parse and print correctly.

    Was skipped on Windows before #9398's tracker.py `_resolve_gh_bin`
    patch (cycle 1194) — Python's `subprocess.run(["gh", ...])` uses
    `CreateProcessW` which skips `.cmd` files in PATH lookup, so the
    shim's `gh.cmd` lost to the real `gh.exe`. The patch routes the
    invocation through `shutil.which("gh")` (PATHEXT-aware), which
    DOES find `.cmd` files. Works cross-platform now."""

    def test_list_tasks_returns_canned_approved_task(self):
        with tempfile.TemporaryDirectory(prefix="gh-shim-fix-") as tmp:
            fdir = Path(tmp)
            (fdir / "issue-list").mkdir()
            canned = [{
                "number": 12345,
                "title": "TASK: synthetic approved task for #9398 shim test",
                "labels": [
                    {"name": "type:task"},
                    {"name": "role:skill"},
                    {"name": "status:approved"},
                    {"name": "priority:medium"},
                ],
            }]
            (fdir / "issue-list" / "default.json").write_text(
                json.dumps(canned), encoding="utf-8"
            )

            env = ems.env_with_gh_shim(fixtures_dir=fdir)
            proc = subprocess.run(
                [sys.executable, str(TRACKER_PY),
                 "list-tasks", "skill", "--status", "approved"],
                env=env, cwd=str(REPO_ROOT),
                capture_output=True, text=True,
                encoding="utf-8", errors="replace",
                timeout=15, check=False,
            )

            self.assertEqual(
                proc.returncode, 0,
                msg=(
                    f"tracker.py list-tasks exited rc={proc.returncode}. "
                    f"stderr: {proc.stderr[:500]!r}; "
                    f"stdout: {proc.stdout[:500]!r}"
                ),
            )
            # tracker.list_issues prints the parsed JSON to stdout
            # (line 382 in tracker.py at time of writing). Strip the
            # `json.dumps(..., indent=2)` formatting and check it
            # round-trips to our canned list.
            parsed = json.loads(proc.stdout)
            self.assertEqual(len(parsed), 1)
            self.assertEqual(parsed[0]["number"], 12345)
            self.assertEqual(
                parsed[0]["title"],
                "TASK: synthetic approved task for #9398 shim test",
            )

    def test_list_tasks_returns_empty_when_no_fixture(self):
        """With the shim active but no fixture file, tracker.py
        should see an empty list and exit cleanly — not crash on
        a malformed response."""
        with tempfile.TemporaryDirectory(prefix="gh-shim-empty-") as tmp:
            fdir = Path(tmp)
            env = ems.env_with_gh_shim(fixtures_dir=fdir)
            proc = subprocess.run(
                [sys.executable, str(TRACKER_PY),
                 "list-tasks", "skill", "--status", "approved"],
                env=env, cwd=str(REPO_ROOT),
                capture_output=True, text=True,
                encoding="utf-8", errors="replace",
                timeout=15, check=False,
            )
            self.assertEqual(
                proc.returncode, 0,
                msg=f"stderr: {proc.stderr[:500]!r}",
            )
            parsed = json.loads(proc.stdout)
            self.assertEqual(parsed, [])


class TestCheckGhThroughShim(unittest.TestCase):
    """``tracker.py check-gh`` is the boot-time gh-permissions
    probe every SquidSquad agent runs. It calls ``gh issue list
    --limit 1`` and accepts any non-error exit as 'gh works'. The
    shim's read-fallback (empty list) makes this probe pass — pin
    that contract so future shim refactors don't break agent boot
    under the test fixture."""

    def test_check_gh_passes_through_shim(self):
        with tempfile.TemporaryDirectory(prefix="gh-shim-check-") as tmp:
            env = ems.env_with_gh_shim(fixtures_dir=Path(tmp))
            proc = subprocess.run(
                [sys.executable, str(TRACKER_PY), "check-gh"],
                env=env, cwd=str(REPO_ROOT),
                capture_output=True, text=True,
                encoding="utf-8", errors="replace",
                timeout=15, check=False,
            )
            self.assertEqual(
                proc.returncode, 0,
                msg=(
                    f"tracker.py check-gh failed through shim. "
                    f"stderr: {proc.stderr[:500]!r}; "
                    f"stdout: {proc.stdout[:500]!r}"
                ),
            )
            self.assertIn("OK", proc.stdout)


if __name__ == "__main__":
    unittest.main()
