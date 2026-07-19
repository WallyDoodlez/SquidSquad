"""Regression test for #13691 — #13654's `_neutralize_pr_body_before_merge`
patches closing keywords out of the PR *body* right before merge, but does
not touch the underlying git commit objects. For a single-commit PR,
GitHub's squash-merge defaults the squash commit's message to that ONE
commit's own message (not the PR body) when `gh pr merge --squash` is
called with no explicit subject/body — so a `Closes #N` sitting in the
commit message (not the PR body) still reaches `main` verbatim and still
auto-closes the issue, bypassing the #13654 guard entirely.

Live evidence: shipping #13683, the issue auto-closed despite PR #13689's
body correctly reading "Addresses #13683" — the actual squash commit on
main carried "Closes #13683" sourced from the PR's sole commit message.

Fix: `_neutralize_pr_body_before_merge` now returns `(title,
neutralized_body)`; `pr_merge`'s squash call passes them EXPLICITLY via
`--subject`/`--body`, so GitHub's implicit default-selection (PR body for
multi-commit PRs, sole commit message for single-commit PRs) is never
reached — closing the gap regardless of commit count.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import git_ops


def _mk(rc=0, stdout="", stderr=""):
    m = MagicMock()
    m.returncode = rc
    m.stdout = stdout
    m.stderr = stderr
    return m


class TestNeutralizeReturnsTitleAndBody13691:
    @patch("git_ops._run_list")
    def test_returns_title_and_neutralized_body_on_success(self, mock_rl):
        def side_effect(cmd, check=False):
            if cmd[:3] == ["gh", "pr", "view"]:
                return _mk(0, json.dumps(
                    {"title": "Fix the thing (#13531)", "body": "Summary.\nFixes #13531"}))
            return _mk(0)
        mock_rl.side_effect = side_effect

        title, body = git_ops._neutralize_pr_body_before_merge(13624)
        assert title == "Fix the thing (#13531)"
        assert "Fixes #13531" not in body
        assert "Addresses #13531" in body

    @patch("git_ops._run_list")
    def test_returns_title_and_body_unchanged_when_already_clean(self, mock_rl):
        mock_rl.side_effect = lambda cmd, check=False: _mk(
            0, json.dumps({"title": "Clean PR", "body": "Addresses #1"}))
        title, body = git_ops._neutralize_pr_body_before_merge(13624)
        assert title == "Clean PR"
        assert body == "Addresses #1"

    @patch("git_ops._run_list")
    def test_view_failure_returns_none_none(self, mock_rl):
        mock_rl.return_value = _mk(1, stderr="not found")
        title, body = git_ops._neutralize_pr_body_before_merge(13624)
        assert (title, body) == (None, None)

    @patch("git_ops._run_list")
    def test_malformed_json_returns_none_none(self, mock_rl):
        mock_rl.side_effect = lambda cmd, check=False: (
            _mk(0, "not json") if cmd[:3] == ["gh", "pr", "view"] else _mk(1)
        )
        title, body = git_ops._neutralize_pr_body_before_merge(13624)
        assert (title, body) == (None, None)

    @patch("git_ops._run_list")
    def test_requests_title_field_alongside_body(self, mock_rl):
        """#13691: the view call must request title too, so pr_merge can
        build an explicit --subject without a second gh round-trip."""
        mock_rl.side_effect = lambda cmd, check=False: _mk(
            0, json.dumps({"title": "T", "body": "B"}))
        git_ops._neutralize_pr_body_before_merge(13624)
        view_call = mock_rl.call_args_list[0].args[0]
        json_idx = view_call.index("--json")
        fields = view_call[json_idx + 1].split(",")
        assert "title" in fields
        assert "body" in fields


class TestSquashMergePassesExplicitSubjectBody13691:
    @pytest.fixture(autouse=True)
    def _safe_guards(self):
        with patch("git_ops._pr_behind_by", return_value=0), \
                patch("git_ops._pr_state_scope_violations", return_value=[]), \
                patch("git_ops._post_merge_scope_audit"), \
                patch("git_ops._revert_composed_state_contamination"), \
                patch("git_ops._checkout_and_ff_working_after_merge"):
            yield

    def _run_merge(self, mock_rl, neutralize_return, strategy="squash"):
        def side_effect(cmd, check=False):
            if cmd[:3] == ["gh", "pr", "view"] and "state,isDraft" in cmd:
                return _mk(0, json.dumps({"state": "OPEN", "isDraft": False}))
            if cmd[:3] == ["gh", "pr", "merge"]:
                return _mk(0)
            return _mk(0, json.dumps({"headRefName": "squidsquad/skill/13691"}))
        mock_rl.side_effect = side_effect
        with patch("git_ops._neutralize_pr_body_before_merge",
                    return_value=neutralize_return):
            success, msg = git_ops.pr_merge(13691, strategy)
        assert success is True
        merge_calls = [c.args[0] for c in mock_rl.call_args_list
                        if c.args[0][:3] == ["gh", "pr", "merge"]]
        assert len(merge_calls) == 1
        return merge_calls[0]

    @patch("git_ops._run_list")
    def test_squash_call_carries_explicit_subject_and_body(self, mock_rl):
        merge_call = self._run_merge(
            mock_rl, ("My Fix Title", "Addresses #13531"))
        assert "--subject" in merge_call
        assert merge_call[merge_call.index("--subject") + 1] == "My Fix Title (#13691)"
        assert "--body" in merge_call
        assert merge_call[merge_call.index("--body") + 1] == "Addresses #13531"

    @patch("git_ops._run_list")
    def test_squash_call_omits_subject_body_on_fetch_failure(self, mock_rl):
        """Fail-open: a gh hiccup on the pre-merge fetch must not block the
        merge — falls through to the prior implicit-default behavior."""
        merge_call = self._run_merge(mock_rl, (None, None))
        assert "--subject" not in merge_call
        assert "--body" not in merge_call

    @patch("git_ops._run_list")
    def test_merge_strategy_never_gets_explicit_subject_body(self, mock_rl):
        """Scoped to squash only — a real merge commit doesn't inherit
        closing keywords from a single commit message the same way."""
        merge_call = self._run_merge(
            mock_rl, ("Title", "Body"), strategy="merge")
        assert "--subject" not in merge_call
        assert "--body" not in merge_call

    @patch("git_ops._run_list")
    def test_explicit_body_is_the_neutralized_one_not_raw(self, mock_rl):
        """The whole point: whatever reaches --body must already be
        keyword-neutralized, so it can never re-introduce a closing
        keyword GitHub would act on."""
        merge_call = self._run_merge(
            mock_rl, ("Fix", "Summary.\nAddresses #999"))
        body_arg = merge_call[merge_call.index("--body") + 1]
        assert "Closes" not in body_arg
        assert "Fixes" not in body_arg
        assert "Addresses #999" in body_arg
