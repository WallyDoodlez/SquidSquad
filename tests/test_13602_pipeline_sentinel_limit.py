"""Tests for #13602 — pipeline-sentinel.md's two `gh issue list --limit 50`
calls share the #13555 silent-truncation class (harness.py's own issue
poller hit the identical bug against the same growing open-issue set).

These are comprehension tests verifying the sub-skill markdown content, not
a Python script — pipeline-sentinel.md is PM's runtime-loaded instructions.
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SENTINEL_FILE = (
    REPO_ROOT / "references" / "sub-skills" / "roles" / "pm" / "pipeline-sentinel.md"
)

HALT_QUERY_OLD = (
    "gh issue list --label squidsquad --state open "
    "--json number,title,labels,updatedAt --limit 50"
)
HALT_QUERY_NEW = (
    "gh issue list --label squidsquad --state open "
    "--json number,title,labels,updatedAt --limit 500"
)
DOUBLE_PICKUP_QUERY_OLD = (
    "gh issue list --label squidsquad --label status:in-progress --state open "
    "--json number,title,labels --limit 50"
)
DOUBLE_PICKUP_QUERY_NEW = (
    "gh issue list --label squidsquad --label status:in-progress --state open "
    "--json number,title,labels --limit 500"
)


@pytest.fixture
def sentinel_text():
    assert SENTINEL_FILE.exists(), f"Pipeline sentinel file missing: {SENTINEL_FILE}"
    return SENTINEL_FILE.read_text(encoding="utf-8")


class TestHaltDetectionQueryLimit:
    """2.1's halt-detection sweep queries ALL open squidsquad issues
    (~165+ currently) — the more urgent of the two per #13602's report."""

    def test_limit_raised_to_500(self, sentinel_text):
        assert HALT_QUERY_NEW in sentinel_text, (
            "halt-detection query must use --limit 500, matching #13555's "
            "precedent for the identical truncation class"
        )

    def test_old_limit_50_query_gone(self, sentinel_text):
        # "--limit 50" is a substring of "--limit 500" — anchor on the line
        # ending right after the old value so the new (fixed) query doesn't
        # false-fail this check.
        assert (HALT_QUERY_OLD + "\n") not in sentinel_text

    def test_warn_at_cap_note_present(self, sentinel_text):
        idx = sentinel_text.index(HALT_QUERY_NEW)
        tail = sentinel_text[idx:idx + 600]
        assert "#13602" in tail
        assert "500" in tail
        assert "invisible" in tail.lower() or "truncat" in tail.lower()


class TestDoublePickupQueryLimit:
    """4g's double-pickup anomaly check (#13515) queries open +
    status:in-progress items — the anomaly detector must not silently miss
    the very anomaly it exists to find."""

    def test_limit_raised_to_500(self, sentinel_text):
        assert DOUBLE_PICKUP_QUERY_NEW in sentinel_text, (
            "double-pickup query must use --limit 500, matching #13555's "
            "precedent for the identical truncation class"
        )

    def test_old_limit_50_query_gone(self, sentinel_text):
        assert (DOUBLE_PICKUP_QUERY_OLD + "\n") not in sentinel_text

    def test_warn_at_cap_note_present(self, sentinel_text):
        idx = sentinel_text.index(DOUBLE_PICKUP_QUERY_NEW)
        tail = sentinel_text[idx:idx + 600]
        assert "#13602" in tail
        assert "500" in tail
        assert "invisible" in tail.lower() or "truncat" in tail.lower()


class TestUnrelatedLimitsUntouched:
    """Only the two #13555-class queries change — the unrelated PR-conflict
    `gh pr list ... --limit 20` (a different query, different bug class) must
    be left alone."""

    def test_pr_conflict_query_limit_unchanged(self, sentinel_text):
        assert (
            'gh pr list --search "squidsquad/" --state open '
            "--json number,title,headRefName,mergeable --limit 20"
        ) in sentinel_text
