"""QA independent verification for #13267 — git_ops.pull must pin BOTH the first
and the retry pull to `git pull --no-rebase`, so no bare `git pull` (which could
rebase under pull.rebase=true) survives anywhere in the flow.

Independent angle vs skill's test_first_pull_is_no_rebase (which checks only the
first pull): exercises the stash→retry path and asserts EVERY `git pull` invocation
is `--no-rebase`. Authored by verifier (qa); preserved permanently.
"""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "references", "scripts"))

import git_ops  # noqa: E402


def _mk(rc=0, out="", err=""):
    m = MagicMock()
    m.returncode = rc
    m.stdout = out
    m.stderr = err
    return m


class TestPullBothNoRebase13267(unittest.TestCase):
    def test_both_pulls_are_no_rebase(self):
        calls = []

        def fake_run(cmd, check=False):
            calls.append(cmd)
            if cmd == "git pull --no-rebase":
                n = sum(1 for c in calls if c == "git pull --no-rebase")
                return _mk(1, err="dirty") if n == 1 else _mk(0, out="Updated")
            if cmd.startswith("git rev-parse"):
                n = sum(1 for c in calls if c.startswith("git rev-parse"))
                return _mk(1, "") if n == 1 else _mk(0, "abc")
            return _mk(0)

        with patch.object(git_ops, "_run", side_effect=fake_run), \
             patch.object(git_ops, "_emit"), \
             patch.object(git_ops, "_restore_merge_dropped_state",
                          return_value=[]):
            # #13556: pull() now invokes the restore guard (via _run_list, not
            # the mocked _run) — neutralize it so no real git runs mid-test.
            git_ops.pull()

        pulls = [c for c in calls if c.startswith("git pull")]
        self.assertGreaterEqual(len(pulls), 2, "stash→retry path must fire both pulls")
        self.assertTrue(all(c == "git pull --no-rebase" for c in pulls),
                        f"every pull must be --no-rebase; got {pulls}")
        self.assertEqual([c for c in pulls if c == "git pull"], [],
                         "no bare 'git pull' may survive (#13267)")


if __name__ == "__main__":
    unittest.main()
