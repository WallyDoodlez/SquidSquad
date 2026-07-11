"""Regression for #13456 — deploy-pull survives an UNTRACKED-file collision.

REAL git (not mocked): builds an origin + a clone where the clone has an
UNTRACKED file at a path the incoming commit now tracks — the exact trigger where
`git pull` ABORTS ("untracked working tree files would be overwritten by merge").
A plain `git stash` (the #13215 fix for dirty TRACKED files) does NOT stash
untracked files, so the retry pull still aborted (recurring dm boot deploy-error).
Asserts harness._safe_pull_in_clone now survives via --include-untracked + the
pulled-wins untracked-restore resolution in _safe_stash_pop_in_clone.

Sibling of tests/test_feat_13215_deploy_pull_dirty_clone.py (dirty TRACKED case).
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
class TestDeployPullUntrackedCollision13456(unittest.TestCase):
    # A nested path mirrors the observed .squidsquad/vault/galaxy/<file> case.
    REL = os.path.join("vault", "galaxy", "note.txt")

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.origin = os.path.join(self.tmp, "origin")
        self.clone = os.path.join(self.tmp, "clone")
        os.makedirs(self.origin)
        _git(self.origin, "init", "-q", "-b", "main")
        _git(self.origin, "config", "user.email", "t@t.t")
        _git(self.origin, "config", "user.name", "t")
        with open(os.path.join(self.origin, "base.txt"), "w") as f:
            f.write("base\n")
        _git(self.origin, "add", ".")
        _git(self.origin, "commit", "-q", "-m", "c1")
        _git(self.tmp, "clone", "-q", self.origin, self.clone)
        _git(self.clone, "config", "user.email", "t@t.t")
        _git(self.clone, "config", "user.name", "t")
        # origin adds a NEW tracked file at REL (the incoming commit)
        opath = os.path.join(self.origin, self.REL)
        os.makedirs(os.path.dirname(opath), exist_ok=True)
        with open(opath, "w") as f:
            f.write("origin-tracked\n")
        _git(self.origin, "add", ".")
        _git(self.origin, "commit", "-q", "-m", "c2 adds tracked note")
        # clone creates the SAME path as an UNTRACKED file (the #13456 trigger)
        cpath = os.path.join(self.clone, self.REL)
        os.makedirs(os.path.dirname(cpath), exist_ok=True)
        with open(cpath, "w") as f:
            f.write("untracked-local\n")
        _git(self.clone, "fetch", "-q", "origin")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_bare_pull_aborts_then_safe_pull_survives(self):
        # The bug: a bare merge-pull aborts on the untracked collision.
        bare = _git(self.clone, "pull", "--no-rebase", "--no-edit", "origin", "main")
        self.assertNotEqual(bare.returncode, 0)
        self.assertIn("untracked working tree files would be overwritten",
                      (bare.stdout + bare.stderr).lower(),
                      "bare pull should abort on the untracked collision (bug reproduced)")

        # The fix: _safe_pull_in_clone survives.
        ok, detail = harness._safe_pull_in_clone(self.clone)
        self.assertTrue(ok, f"_safe_pull_in_clone must succeed; detail={detail}")

        clone_head = _git(self.clone, "rev-parse", "HEAD").stdout.strip()
        origin_head = _git(self.origin, "rev-parse", "HEAD").stdout.strip()
        self.assertEqual(clone_head, origin_head, "deploy-sync must land (HEADs equal)")
        self.assertFalse(os.path.exists(os.path.join(self.clone, ".git", "MERGE_HEAD")),
                         "clone must not be left in MERGING state")
        with open(os.path.join(self.clone, self.REL)) as f:
            self.assertEqual(f.read().strip(), "origin-tracked",
                             "pulled (authoritative) content must win over the untracked local file")
        # The moved-aside untracked stash must be DROPPED (pulled wins), not linger —
        # a lingering stash would silently accumulate on every deploy.
        stash_list = _git(self.clone, "stash", "list").stdout.strip()
        self.assertEqual(stash_list, "", "untracked-restore stash must be dropped, not left behind")

    def test_dirty_tracked_still_works_with_include_untracked(self):
        """The #13215 dirty-TRACKED path must still survive after the -u change."""
        # Make base.txt dirty (tracked) and also diverge origin's base.txt.
        with open(os.path.join(self.origin, "base.txt"), "w") as f:
            f.write("base-v2-origin\n")
        _git(self.origin, "add", "base.txt")
        _git(self.origin, "commit", "-q", "-m", "c3 base changes")
        with open(os.path.join(self.clone, "base.txt"), "w") as f:
            f.write("base-dirty-local\n")
        _git(self.clone, "fetch", "-q", "origin")

        ok, detail = harness._safe_pull_in_clone(self.clone)
        self.assertTrue(ok, f"_safe_pull_in_clone must survive dirty tracked; detail={detail}")
        clone_head = _git(self.clone, "rev-parse", "HEAD").stdout.strip()
        origin_head = _git(self.origin, "rev-parse", "HEAD").stdout.strip()
        self.assertEqual(clone_head, origin_head, "deploy-sync must land (HEADs equal)")
        self.assertFalse(os.path.exists(os.path.join(self.clone, ".git", "MERGE_HEAD")),
                         "clone must not be left in MERGING state")


if __name__ == "__main__":
    unittest.main()
