"""Regression for #13472 — _safe_pull_in_clone must not leave a clone MERGING on
a genuine committed conflict.

When the FIRST `git pull --no-rebase` hits a genuine committed conflict it starts
a merge and leaves an unmerged index; the subsequent `git stash --include-untracked`
then fails ("could not write index"), and the pre-fix code returned at the
stash-failed early branch BEFORE the retry-branch's `git merge --abort` — leaving
the clone MERGING (.git/MERGE_HEAD), which wedges the NEXT deploy's `checkout main`
(the exact state the function's docstring says it prevents). The fix runs
`git merge --abort` on the stash-failed path.

Pre-existing gap (NOT introduced by #13456); surfaced during #13456 verification.
Sibling of tests/test_feat_13215_deploy_pull_dirty_clone.py.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "references", "scripts"))

import harness  # noqa: E402


def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


@unittest.skipIf(shutil.which("git") is None, "git not available")
class TestSafePullCommittedConflict13472(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.origin = os.path.join(self.tmp, "origin")
        self.clone = os.path.join(self.tmp, "clone")
        os.makedirs(self.origin)
        _git(self.origin, "init", "-q", "-b", "main")
        _git(self.origin, "config", "user.email", "t@t.t")
        _git(self.origin, "config", "user.name", "t")
        with open(os.path.join(self.origin, "shared.txt"), "w") as f:
            f.write("base\n")
        _git(self.origin, "add", ".")
        _git(self.origin, "commit", "-q", "-m", "c1")
        _git(self.tmp, "clone", "-q", self.origin, self.clone)
        _git(self.clone, "config", "user.email", "t@t.t")
        _git(self.clone, "config", "user.name", "t")
        # origin COMMITS a change to the shared line
        with open(os.path.join(self.origin, "shared.txt"), "w") as f:
            f.write("origin-line\n")
        _git(self.origin, "add", ".")
        _git(self.origin, "commit", "-q", "-m", "c2 origin")
        # clone COMMITS a DIVERGENT change to the same line (committed, not dirty)
        with open(os.path.join(self.clone, "shared.txt"), "w") as f:
            f.write("clone-line\n")
        _git(self.clone, "add", ".")
        _git(self.clone, "commit", "-q", "-m", "c2 clone divergent")
        _git(self.clone, "fetch", "-q", "origin")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _merging(self):
        return os.path.exists(os.path.join(self.clone, ".git", "MERGE_HEAD"))

    def test_committed_conflict_does_not_leave_merging(self):
        # Reproduce: a bare merge-pull on the divergent-committed tree conflicts
        # and leaves the clone MERGING.
        bare = _git(self.clone, "pull", "--no-rebase", "--no-edit", "origin", "main")
        self.assertNotEqual(bare.returncode, 0)
        self.assertTrue(self._merging(), "bare pull should leave MERGING (bug precondition)")
        # Clean up that bare-merge state so we test _safe_pull_in_clone from a
        # non-merging start (its own first pull re-creates the conflict).
        _git(self.clone, "merge", "--abort")
        self.assertFalse(self._merging())

        # The fix: _safe_pull_in_clone must report failure AND not leave MERGING.
        ok, detail = harness._safe_pull_in_clone(self.clone)
        self.assertFalse(ok, f"a genuine committed conflict must fail; detail={detail}")
        self.assertFalse(
            self._merging(),
            "clone must NOT be left MERGING after a committed-conflict deploy-pull "
            "(#13472) — a lingering MERGE_HEAD wedges the next deploy's checkout main",
        )


if __name__ == "__main__":
    unittest.main()
