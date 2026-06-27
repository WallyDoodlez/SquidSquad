"""QA independent REAL-git verification for #13261 — git_ops.pull must abort an
in-progress merge before restoring the stash on a genuine-conflict retry, so the
clone is not left MERGING and the stashed local change is not silently dropped.

This is the every-agent cwd pull path (higher blast radius than the deploy-path
#13215 sibling). NOTE: git_ops._run pins ``cwd=str(REPO_ROOT)`` (a module global),
so the function always operates on REPO_ROOT — an ``os.chdir`` into a temp clone
has NO effect. The correct way to point it at a test clone is to patch
``git_ops.REPO_ROOT``. Complements skill's mocked
TestPull::test_pull_retry_fail_aborts_merge_before_pop with a real-git proof that
the stash survives. Authored by verifier (qa); preserved permanently.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "references", "scripts"))

import git_ops  # noqa: E402


def _g(cwd, *a):
    return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True)


@unittest.skipIf(shutil.which("git") is None, "git not available")
class TestPullMergeAbort13261(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.origin = os.path.join(self.tmp, "o")
        self.clone = os.path.join(self.tmp, "c")
        os.makedirs(self.origin)
        _g(self.origin, "init", "-q", "-b", "main")
        _g(self.origin, "config", "user.email", "t@t")
        _g(self.origin, "config", "user.name", "t")
        for fn in ("a.txt", "b.txt"):
            with open(os.path.join(self.origin, fn), "w") as f:
                f.write("base\n")
        _g(self.origin, "add", ".")
        _g(self.origin, "commit", "-q", "-m", "A")
        _g(self.tmp, "clone", "-q", self.origin, self.clone)
        _g(self.clone, "config", "user.email", "t@t")
        _g(self.clone, "config", "user.name", "t")
        # origin advances both files
        with open(os.path.join(self.origin, "a.txt"), "w") as f:
            f.write("origin-a\n")
        with open(os.path.join(self.origin, "b.txt"), "w") as f:
            f.write("origin-b\n")
        _g(self.origin, "add", ".")
        _g(self.origin, "commit", "-q", "-m", "B")
        # clone: committed divergence on b.txt (conflicts on merge)
        with open(os.path.join(self.clone, "b.txt"), "w") as f:
            f.write("local-b-committed\n")
        _g(self.clone, "add", "b.txt")
        _g(self.clone, "commit", "-q", "-m", "local-b")
        # clone: dirty uncommitted a.txt (B touches a.txt -> first pull aborts)
        with open(os.path.join(self.clone, "a.txt"), "w") as f:
            f.write("local-a-dirty-uncommitted\n")
        _g(self.clone, "fetch", "-q", "origin")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_retry_conflict_aborts_merge_and_preserves_stash(self):
        # Point git_ops at the test clone (it pins cwd=REPO_ROOT, ignoring chdir).
        with patch.object(git_ops, "REPO_ROOT", self.clone):
            ok = git_ops.pull()

        self.assertFalse(ok, "pull must report failure on a genuine conflict")
        self.assertFalse(os.path.exists(os.path.join(self.clone, ".git", "MERGE_HEAD")),
                         "clone must not be left MERGING (merge --abort)")
        with open(os.path.join(self.clone, "b.txt")) as f:
            self.assertNotIn("<<<<<<<", f.read(), "no conflict markers may leak")
        with open(os.path.join(self.clone, "a.txt")) as f:
            self.assertEqual(f.read().strip(), "local-a-dirty-uncommitted",
                             "stashed dirty change must be preserved, not dropped")


if __name__ == "__main__":
    unittest.main()
