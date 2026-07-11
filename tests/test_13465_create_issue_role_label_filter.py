"""Regression tests for #13465 — tracker.py create-issue must not stamp a
role:* label the repo taxonomy does not define.

The #6274 dual-aware mapping emitted `role:qa,role:verifier` for `--role qa`, but
the repo has no `role:verifier` label, so `gh issue create` rejected the unknown
label and `create-issue --role qa` failed non-zero (blocking qa-lane filing via
the canonical tool). `_filter_role_labels_to_existing` drops the unknown alias
while always keeping the primary role label; `create_issue`/`create_task` apply
it before the gh call.
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import tracker


class TestFilterRoleLabelsToExisting:
    @patch("tracker._repo_labels", return_value={"role:qa", "role:skill", "role:dm", "role:pm"})
    def test_qa_drops_nonexistent_verifier_alias(self, _m):
        # The bug: role:qa,role:verifier -> role:qa (verifier label absent).
        assert tracker._filter_role_labels_to_existing(
            "role:qa,role:verifier", "qa") == "role:qa"

    @patch("tracker._repo_labels", return_value={"role:qa", "role:verifier"})
    def test_qa_keeps_verifier_alias_when_it_exists(self, _m):
        # Post-#6274.3: both labels exist -> dual emit resumes automatically.
        assert tracker._filter_role_labels_to_existing(
            "role:qa,role:verifier", "qa") == "role:qa,role:verifier"

    @patch("tracker._repo_labels", return_value={"role:skill"})
    def test_non_dual_role_unchanged(self, _m):
        assert tracker._filter_role_labels_to_existing("role:skill", "skill") == "role:skill"

    @patch("tracker._repo_labels", return_value=set())
    def test_gh_failure_falls_closed_to_primary(self, _m):
        # Empty existence set (gh label list failed/unavailable) -> primary only.
        assert tracker._filter_role_labels_to_existing(
            "role:qa,role:verifier", "qa") == "role:qa"

    @patch("tracker._repo_labels", return_value={"role:qa"})
    def test_primary_always_kept_even_if_absent(self, _m):
        # A create must never lose its assignee: the primary is never dropped,
        # and unknown aliases are still filtered out.
        out = tracker._filter_role_labels_to_existing("role:foo,role:bar", "foo")
        assert out.split(",")[0] == "role:foo"
        assert "role:bar" not in out


class TestRepoLabelsCaching:
    def test_parses_and_caches_label_names(self):
        tracker._REPO_LABELS_CACHE = None
        fake = MagicMock()
        fake.returncode = 0
        fake.stdout = '[{"name":"role:qa"},{"name":"role:skill"}]'
        with patch("tracker._run_list", return_value=fake) as m:
            first = tracker._repo_labels()
            second = tracker._repo_labels()  # cached: no 2nd gh call
        assert first == {"role:qa", "role:skill"}
        assert second == first
        assert m.call_count == 1
        tracker._REPO_LABELS_CACHE = None

    def test_failure_returns_empty_set(self):
        tracker._REPO_LABELS_CACHE = None
        fake = MagicMock()
        fake.returncode = 1
        fake.stdout = ""
        with patch("tracker._run_list", return_value=fake):
            assert tracker._repo_labels() == set()
        tracker._REPO_LABELS_CACHE = None


class TestCreateIssueExcludesUnknownRoleLabel:
    def test_create_issue_label_arg_omits_nonexistent_verifier(self):
        tracker._REPO_LABELS_CACHE = None
        captured = {}

        def fake_run_list(cmd, check=True, timeout=None):
            r = MagicMock()
            if "label" in cmd and "list" in cmd:
                r.returncode = 0
                r.stdout = ('[{"name":"role:qa"},{"name":"type:issue"},'
                            '{"name":"severity:low"},{"name":"squidsquad"},'
                            '{"name":"status:open"}]')
                return r
            if "issue" in cmd and "create" in cmd:
                captured["label"] = cmd[cmd.index("--label") + 1]
                r.returncode = 0
                r.stdout = "https://github.com/o/r/issues/999"
                return r
            r.returncode = 0
            r.stdout = ""
            return r

        with patch("tracker._get_forge_adapter", return_value=None), \
             patch("tracker._run_list", side_effect=fake_run_list):
            num = tracker.create_issue("x", "y", "qa", "low", reporter="dm-lead")
        assert num == 999
        assert "role:qa" in captured["label"]
        assert "role:verifier" not in captured["label"]
        tracker._REPO_LABELS_CACHE = None
