"""QA independent verification for #13215 — deploy-pull survives a dirty clone.

REAL git (not mocked): builds an origin + a clone behind it with an uncommitted
change to a file the incoming commit also touches — the exact bug trigger where a
bare `git pull` ABORTS ('local changes would be overwritten by merge'). Asserts
harness._safe_pull_in_clone survives: deploy-sync lands and the clone is not left
MERGING. Complements skill's mocked TestSafePullInClone13215.

Authored by verifier (qa). Preserved permanently per the verifier preserved-tests rule.
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
class TestDeployPullDirtyClone13215(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.origin = os.path.join(self.tmp, "origin")
        self.clone = os.path.join(self.tmp, "clone")
        os.makedirs(self.origin)
        _git(self.origin, "init", "-q", "-b", "main")
        _git(self.origin, "config", "user.email", "t@t.t")
        _git(self.origin, "config", "user.name", "t")
        with open(os.path.join(self.origin, "shared.txt"), "w") as f:
            f.write("v1\n")
        _git(self.origin, "add", ".")
        _git(self.origin, "commit", "-q", "-m", "c1")
        _git(self.tmp, "clone", "-q", self.origin, self.clone)
        _git(self.clone, "config", "user.email", "t@t.t")
        _git(self.clone, "config", "user.name", "t")
        # origin advances on the same file
        with open(os.path.join(self.origin, "shared.txt"), "w") as f:
            f.write("v2-from-origin\n")
        _git(self.origin, "add", ".")
        _git(self.origin, "commit", "-q", "-m", "c2 incoming")
        # clone goes dirty on the same file (the #13215 trigger)
        with open(os.path.join(self.clone, "shared.txt"), "w") as f:
            f.write("dirty-local-uncommitted\n")
        _git(self.clone, "fetch", "-q", "origin")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_bare_pull_aborts_then_safe_pull_survives(self):
        # The bug: a bare merge-pull aborts on the dirty tree.
        bare = _git(self.clone, "pull", "--no-rebase", "--no-edit", "origin", "main")
        self.assertNotEqual(bare.returncode, 0)
        self.assertIn("overwritten by merge", (bare.stdout + bare.stderr).lower(),
                      "bare pull should abort on the dirty tree (bug reproduced)")

        # The fix: _safe_pull_in_clone survives.
        ok, detail = harness._safe_pull_in_clone(self.clone)
        self.assertTrue(ok, f"_safe_pull_in_clone must succeed; detail={detail}")

        clone_head = _git(self.clone, "rev-parse", "HEAD").stdout.strip()
        origin_head = _git(self.origin, "rev-parse", "HEAD").stdout.strip()
        self.assertEqual(clone_head, origin_head, "deploy-sync must land (HEADs equal)")
        self.assertFalse(os.path.exists(os.path.join(self.clone, ".git", "MERGE_HEAD")),
                         "clone must not be left in MERGING state")
        with open(os.path.join(self.clone, "shared.txt")) as f:
            self.assertEqual(f.read().strip(), "v2-from-origin",
                             "pulled (authoritative) content must be present")


if __name__ == "__main__":
    unittest.main()
