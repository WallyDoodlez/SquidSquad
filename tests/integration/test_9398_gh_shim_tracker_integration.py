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


def _make_hermetic_git_workspace(root: Path) -> Path:
    """A throwaway scripts-copy install whose ``origin`` is a LOCAL bare
    repo (#13957). Returns the workspace root; the runnable tracker is at
    ``<work>/references/scripts/tracker.py``.

    ``check-gh`` grew a real-git push path in #13863 (``git_ops.py
    push-doctor``: credential-helper rewrite into ``.git/config`` +
    ``git push --dry-run origin HEAD``), and ``git_ops`` pins every git
    command to the repo root derived from its OWN file location — cwd is
    ignored. Running the real clone's tracker therefore (a) fails on any
    clone whose credential chain routes through the PATH-shimmed fake
    ``gh`` — the doctor's dry-run authenticates against the REAL origin
    with credentials served by the fake — and (b) worse, rewrites the
    developer's real ``.git/config`` as a test side effect. Copying
    ``references/scripts`` into a scratch git repo re-roots git_ops there;
    its local (non-https) origin makes the doctor take its own documented
    non-https early-return ("nothing to heal"), touching nothing real.
    """
    import shutil

    bare = root / "origin.git"
    work = root / "work"
    (work / "references").mkdir(parents=True)
    shutil.copytree(REPO_ROOT / "references" / "scripts",
                    work / "references" / "scripts")
    subprocess.run(["git", "init", "--bare", str(bare)],
                   capture_output=True, check=True, timeout=15)
    subprocess.run(["git", "init"], cwd=str(work),
                   capture_output=True, check=True, timeout=15)
    subprocess.run(["git", "-c", "user.name=shim-test",
                    "-c", "user.email=shim@test",
                    "commit", "--allow-empty", "-m", "seed"],
                   cwd=str(work), capture_output=True, check=True, timeout=15)
    subprocess.run(["git", "remote", "add", "origin", str(bare)],
                   cwd=str(work), capture_output=True, check=True, timeout=15)
    return work


class TestCheckGhThroughShim(unittest.TestCase):
    """``tracker.py check-gh`` is the boot-time gh-permissions
    probe every SquidSquad agent runs. It calls ``gh issue list
    --limit 1`` and accepts any non-error exit as 'gh works'. The
    shim's read-fallback (empty list) makes this probe pass — pin
    that contract so future shim refactors don't break agent boot
    under the test fixture.

    Runs in a hermetic scratch workspace (#13957), NOT the real repo:
    the #13863 push-doctor half of check-gh must neither depend on the
    host's credential chain (which the fake ``gh`` breaks) nor mutate
    the real clone's ``.git/config``."""

    def test_check_gh_passes_through_shim(self):
        with tempfile.TemporaryDirectory(prefix="gh-shim-check-") as tmp:
            fdir = Path(tmp) / "fixtures"
            fdir.mkdir()
            work = _make_hermetic_git_workspace(Path(tmp))
            hermetic_tracker = work / "references" / "scripts" / "tracker.py"
            env = ems.env_with_gh_shim(fixtures_dir=fdir)
            proc = subprocess.run(
                [sys.executable, str(hermetic_tracker), "check-gh"],
                env=env, cwd=str(work),
                capture_output=True, text=True,
                encoding="utf-8", errors="replace",
                timeout=60, check=False,
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

    def test_check_gh_does_not_doctor_the_hermetic_workspace(self):
        """The push-doctor's non-https early-return must fire: no
        credential-helper entries written into the scratch repo's local
        config proves the doctoring path was skipped, not merely lucky
        (#13957). This is the pin that the shim test stays hermetic even
        if a future refactor reorders the doctor's guard."""
        with tempfile.TemporaryDirectory(prefix="gh-shim-doctor-") as tmp:
            fdir = Path(tmp) / "fixtures"
            fdir.mkdir()
            work = _make_hermetic_git_workspace(Path(tmp))
            hermetic_tracker = work / "references" / "scripts" / "tracker.py"
            env = ems.env_with_gh_shim(fixtures_dir=fdir)
            proc = subprocess.run(
                [sys.executable, str(hermetic_tracker), "check-gh"],
                env=env, cwd=str(work),
                capture_output=True, text=True,
                encoding="utf-8", errors="replace",
                timeout=60, check=False,
            )
            # Guard against a vacuum pass (external-review finding): if
            # check-gh died before reaching push-doctor, no helper entries
            # would be written either — returncode 0 proves the doctor ran
            # and the emptiness below is its early-return, not an accident.
            self.assertEqual(
                proc.returncode, 0,
                msg=f"check-gh failed: stderr={proc.stderr[:500]!r}",
            )
            helpers = subprocess.run(
                ["git", "config", "--local", "--get-all", "credential.helper"],
                cwd=str(work), capture_output=True, text=True,
                timeout=15, check=False,
            )
            # Exit 1 + empty output = key entirely absent (never written).
            self.assertEqual((helpers.stdout or "").strip(), "")


if __name__ == "__main__":
    unittest.main()
