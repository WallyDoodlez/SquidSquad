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
    def test_unknown_role_falls_back_to_primary(self, _m):
        # When NONE of the emitted role labels exist (unknown role), fall back to
        # the primary so the issue is never left without a role label.
        out = tracker._filter_role_labels_to_existing("role:foo,role:bar", "foo")
        assert out == "role:foo"
        assert "role:bar" not in out

    @patch("tracker._repo_labels", return_value={"role:qa", "role:skill", "role:dm"})
    def test_verifier_new_form_primary_dropped_keeps_existing_qa(self, _m):
        # #13465 Finding 1: NEW-form input (--role verifier) makes role:verifier
        # the PRIMARY, which does NOT exist pre-#6274.3. The filter must drop the
        # non-existent primary and keep the existing alias role:qa — the same
        # failure mode as --role qa but from the opposite direction.
        out = tracker._filter_role_labels_to_existing("role:verifier,role:qa", "verifier")
        assert out == "role:qa"
        assert "role:verifier" not in out


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
    def _run_create_capturing_label(self, role, label_list_json, issue_url):
        """Drive create_issue with _repo_labels' `gh label list` mocked on
        _run_list and the create routed through _run_gh_with_body (#13370, stdin
        body). Returns (issue_number, captured_label_arg)."""
        captured = {}

        def fake_run_list(cmd, check=True, timeout=None):
            r = MagicMock()
            r.returncode = 0
            r.stdout = label_list_json if ("label" in cmd and "list" in cmd) else ""
            return r

        def fake_gwb(cmd, body, check=True):
            captured["label"] = cmd[cmd.index("--label") + 1]
            r = MagicMock()
            r.returncode = 0
            r.stdout = issue_url
            return r

        tracker._REPO_LABELS_CACHE = None
        with patch("tracker._get_forge_adapter", return_value=None), \
             patch("tracker._run_list", side_effect=fake_run_list), \
             patch("tracker._run_gh_with_body", side_effect=fake_gwb):
            num = tracker.create_issue("x", "y", role, "low", reporter="dm-lead")
        tracker._REPO_LABELS_CACHE = None
        return num, captured["label"]

    def test_create_issue_label_arg_omits_nonexistent_verifier(self):
        num, label = self._run_create_capturing_label(
            "qa",
            '[{"name":"role:qa"},{"name":"type:issue"},{"name":"severity:low"},'
            '{"name":"squidsquad"},{"name":"status:open"}]',
            "https://github.com/o/r/issues/999")
        assert num == 999
        assert "role:qa" in label
        assert "role:verifier" not in label

    def test_create_issue_new_form_role_verifier_also_omits_unknown_label(self):
        # #13465 Finding 1: create_issue with the NEW-form --role verifier must
        # still emit only the existing role:qa label, never the non-existent
        # role:verifier (which would fail the gh create the same way).
        num, label = self._run_create_capturing_label(
            "verifier", '[{"name":"role:qa"}]',
            "https://github.com/o/r/issues/1000")
        assert num == 1000
        assert "role:qa" in label
        assert "role:verifier" not in label
