"""Independent verifier tests for #13465 — tracker.py create-issue --role qa role-label filter.

Derived from TEST-PLAN-13465.md (AC list), NOT the worker's test file.
Hermetic: stubs the repo-label taxonomy (tracker._REPO_LABELS_CACHE) so the
filter logic is exercised deterministically without hitting the live forge.
(The definitive live E2E — real `create-issue --role qa` succeeding, #13475 —
was run once during verification and recorded in QA-RESULTS-13465.md.)
"""
import sys
from pathlib import Path

import pytest


def _find_repo_root(start):
    for p in [start, *start.parents]:
        if (p / "references" / "scripts" / "tracker.py").exists():
            return p
    raise RuntimeError("could not locate repo root (references/scripts/tracker.py)")


REPO_ROOT = _find_repo_root(Path(__file__).resolve())
SCRIPTS = REPO_ROOT / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import tracker  # noqa: E402

# Mirror the real repo taxonomy (verified live: role:{designer,dm,pm,qa,skill}; no role:verifier).
REAL_TAXONOMY = {"role:designer", "role:dm", "role:pm", "role:qa", "role:skill",
                 "type:issue", "squidsquad", "status:open", "severity:low"}


@pytest.fixture
def stub_taxonomy(monkeypatch):
    def _set(labels):
        monkeypatch.setattr(tracker, "_REPO_LABELS_CACHE", set(labels))
    return _set


def _filter_for(role):
    return tracker._filter_role_labels_to_existing(
        tracker._build_dual_role_labels_6274(role), role)


def test_tc_03_qa_dual_filtered_to_role_qa(stub_taxonomy):
    """AC1: --role qa emits role:qa, drops non-existent role:verifier."""
    stub_taxonomy(REAL_TAXONOMY)
    out = _filter_for("qa")
    assert out == "role:qa", out
    assert "role:verifier" not in out


def test_tc_04_verifier_dual_keeps_role_qa_not_primary(stub_taxonomy):
    """AC2: --role verifier drops non-existent primary role:verifier, keeps role:qa
    (Finding-1: primary is NOT force-kept)."""
    stub_taxonomy(REAL_TAXONOMY)
    out = _filter_for("verifier")
    assert out == "role:qa", out
    assert "role:verifier" not in out


def test_tc_05_non_dual_roles_unchanged(stub_taxonomy):
    """AC3: skill/pm/dm/designer emit exactly role:<role>."""
    stub_taxonomy(REAL_TAXONOMY)
    for r in ("skill", "pm", "dm", "designer"):
        assert _filter_for(r) == f"role:{r}", r


def test_tc_06_degraded_taxonomy_falls_back_to_primary(stub_taxonomy):
    """AC4: empty/unavailable taxonomy -> fall back to primary role:<role>."""
    stub_taxonomy(set())  # simulate degraded `gh label list`
    assert _filter_for("qa") == "role:qa"
    assert _filter_for("skill") == "role:skill"


def test_tc_06b_dual_resumes_when_new_label_exists(stub_taxonomy):
    """AC-forward: when #6274.3 creates role:verifier, dual-emit resumes automatically."""
    stub_taxonomy(REAL_TAXONOMY | {"role:verifier"})
    out = _filter_for("qa")
    assert "role:qa" in out and "role:verifier" in out


def test_tc_07_regression_test_present():
    """AC5: worker ships a regression test for the filter."""
    wt = REPO_ROOT / "tests" / "test_13465_create_issue_role_label_filter.py"
    assert wt.exists(), "worker regression test missing"
    txt = wt.read_text().lower()
    assert "role:verifier" in txt or "verifier" in txt
