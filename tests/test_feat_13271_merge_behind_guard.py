"""QA independent verification for #13271 — the behind-count squash-merge guard
(SEV-1 stale-tree mass-revert prevention).

Independent angle vs skill's TestPrMerge guard tests (which check 154 and 3):
covers the exact threshold boundary (the guard is `> max_behind`, so == proceeds
and +1 refuses) and proves a refusal fires BEFORE any `gh pr merge` subprocess —
main is never mutated on the fail-safe path. Authored by verifier (qa); preserved
permanently.
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


class TestMergeBehindGuard13271(unittest.TestCase):
    def _run_with_behind(self, behind, strategy="squash"):
        calls = []

        def fake_runlist(args, check=False):
            calls.append(args)
            if "view" in args and "state" in args:
                return _mk(0, out='{"state":"OPEN"}')
            if "merge" in args:
                return _mk(0, out="merged")
            return _mk(0, out="")

        with patch.object(git_ops, "_run_list", side_effect=fake_runlist), \
             patch.object(git_ops, "_pr_behind_by", return_value=behind), \
             patch.object(git_ops, "_merge_max_behind", return_value=50):
            ok, msg = git_ops.pr_merge(999, strategy=strategy)
        merge_called = any("merge" in a for a in calls)
        return ok, msg, merge_called

    def test_at_threshold_proceeds(self):
        ok, _, merged = self._run_with_behind(50)  # == threshold
        self.assertTrue(merged, "behind == max_behind must PROCEED (guard is strictly >)")

    def test_one_over_threshold_refused(self):
        ok, msg, merged = self._run_with_behind(51)
        self.assertFalse(ok)
        self.assertFalse(merged)
        self.assertIn("behind", (msg or "").lower())

    def test_merge_strategy_not_guarded(self):
        _, _, merged = self._run_with_behind(51, strategy="merge")
        self.assertTrue(merged, "non-squash strategy must not be behind-guarded")

    def test_sev1_154_refused_before_merge_subprocess(self):
        ok, _, merged = self._run_with_behind(154)  # the actual SEV-1 number
        self.assertFalse(ok)
        self.assertFalse(merged, "fail-safe: no merge subprocess on refusal (main not mutated)")


if __name__ == "__main__":
    unittest.main()
