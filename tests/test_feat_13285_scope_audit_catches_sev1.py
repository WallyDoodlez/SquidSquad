"""QA independent verification for #13285 — the post-merge scope-audit must catch
the #13269 SEV-1 incident's mass-revert signature, with no false positives.

Independent angle vs skill's unit tests: replays the ACTUAL #13269 incident shape
(a PR that declared only the TUI additions, whose stale-tree squash deleted ~194
out-of-scope fleet files — config.md, all composed CLAUDE.md, vault, QA-RESULTS)
and asserts the audit flags exactly the out-of-scope deletions; plus the two
false-positive guards (clean +additions merge, a PR's own in-scope deletion) and
the fail-safe (undeterminable declared-set → None, never auto-revert). Authored by
verifier (qa — the SEV-1's originator). Preserved permanently.
"""
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "references", "scripts"))

import git_ops  # noqa: E402


class TestScopeAuditCatchesSev1_13285(unittest.TestCase):
    def test_would_catch_the_13269_incident(self):
        declared = {"references/tui/app.py", "references/tui/harness_client.py",
                    "references/scripts/harness.py", "docs/HARNESS-ARCH.md",
                    "tests/test_feat_12801_reboot_action_bar.py"}
        deleted = {".squidsquad/config.md", ".claude/settings.json",
                   ".squidsquad/pm/CLAUDE.md", ".squidsquad/qa/CLAUDE.md",
                   ".squidsquad/vault/galaxy/learning-x.md",
                   ".squidsquad/qa/planning/QA-RESULTS-13170.md"}
        with patch.object(git_ops, "_pr_declared_files", return_value=declared), \
             patch.object(git_ops, "_merge_deleted_files", return_value=deleted):
            v = git_ops._scope_audit_violations(13269, "f36155a60")
        self.assertEqual(v, sorted(deleted), "all out-of-scope deletions must be flagged")
        self.assertIn(".squidsquad/config.md", v)
        self.assertIn(".squidsquad/qa/CLAUDE.md", v)

    def test_clean_additions_merge_no_false_positive(self):
        with patch.object(git_ops, "_pr_declared_files", return_value={"a.py", "b.py"}), \
             patch.object(git_ops, "_merge_deleted_files", return_value=set()):
            self.assertEqual(git_ops._scope_audit_violations(1, "x"), [])

    def test_in_scope_deletion_no_false_positive(self):
        # A PR that legitimately deletes its OWN declared file is not a violation.
        with patch.object(git_ops, "_pr_declared_files", return_value={"old.py", "new.py"}), \
             patch.object(git_ops, "_merge_deleted_files", return_value={"old.py"}):
            self.assertEqual(git_ops._scope_audit_violations(1, "x"), [])

    def test_fail_safe_on_undeterminable_declared(self):
        with patch.object(git_ops, "_pr_declared_files", return_value=None):
            self.assertIsNone(git_ops._scope_audit_violations(1, "x"))


if __name__ == "__main__":
    unittest.main()
