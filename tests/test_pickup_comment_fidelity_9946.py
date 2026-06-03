"""#9946 regression tests — pickup-comment-fidelity sub-skill wiring.

The bug: skill agents posted pending-test comments that claimed work not
present in the feature PR diff. Two consecutive instances (#9925 and
#9926) — root cause was a mix of state-file edits filtered by
`commit_code` and fabricated test-result counts. Fix: introduce a
`common/pickup-comment-fidelity` sub-skill, wire it into dev's manifests
and template, and reference it from both implement-tasks (Step 8b-bis)
and triage-issues (Step 7b-bis).

These tests freeze the wiring so future refactors don't silently strand
the fragment.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import compose  # noqa: E402
import v2_link_stage  # noqa: E402


def _v2_compose_for(role: str) -> str:
    """Hermetic v2 compose for product-invariant tests.

    Returns the v2 link-stage output (linked composite, pre-assemble)
    with deterministic placeholder substitution applied. Sufficient
    for "is this sub-skill marker present" invariants — skips both
    the LLM assemble step (would prose-rewrite markers) and any L4
    project-local ops (would couple the test to this repo's own
    ``.squidsquad/project/<role>.md`` file).

    Replaces the E6-retired ``compose.compose_role(role)`` call.
    """
    resolved = compose._resolve_variant(role)
    if resolved:
        role_class, l3_domain = resolved
    else:
        role_class = compose._get_entry_file_for_role(role)
        l3_domain = None
    body = v2_link_stage.emit_v2_linked(
        role_class, l3_domain,
        l4_path=REPO / "tests" / "_nonexistent_l4_for_hermetic_v2_compose.md",
    )
    return compose._substitute_placeholders(body, role, role_class)

FRAGMENT = REPO / "references" / "sub-skills" / "common" / "pickup-comment-fidelity.md"
DEV_TEMPLATE = REPO / "references" / "roles" / "dev" / "instructions.md"
DEV_POLL_MANIFEST = REPO / "references" / "roles" / "dev" / "includes.yml"
DEV_EVENT_MANIFEST = REPO / "references" / "roles" / "dev" / "includes-events.yml"
IMPLEMENT_TASKS = REPO / "references" / "sub-skills" / "roles" / "dev" / "implement-tasks.md"
TRIAGE_ISSUES = REPO / "references" / "sub-skills" / "roles" / "dev" / "triage-issues.md"


def test_fragment_file_exists():
    assert FRAGMENT.exists(), (
        f"pickup-comment-fidelity sub-skill missing at {FRAGMENT}"
    )


def test_fragment_covers_both_failure_modes():
    """The fragment must call out the state-file filter and test-result
    fabrication explicitly — these were the two #9946 root mechanisms."""
    content = FRAGMENT.read_text(encoding="utf-8")
    assert "commit_code" in content, "must reference commit_code by name"
    assert ".squidsquad/" in content, "must call out .squidsquad/ filter prefix"
    assert ".claude/" in content, "must call out .claude/ filter prefix"
    assert "Test-result fidelity" in content, (
        "must include the test-result fidelity sub-section"
    )
    assert "git diff origin/main...HEAD" in content, (
        "must give the mechanical diff command"
    )


def test_fragment_in_dev_polling_manifest():
    manifest = yaml.safe_load(DEV_POLL_MANIFEST.read_text(encoding="utf-8"))
    assert "common/pickup-comment-fidelity" in manifest["includes"], (
        "common/pickup-comment-fidelity missing from dev polling manifest"
    )


def test_fragment_in_dev_events_manifest():
    manifest = yaml.safe_load(DEV_EVENT_MANIFEST.read_text(encoding="utf-8"))
    assert "common/pickup-comment-fidelity" in manifest["includes"], (
        "common/pickup-comment-fidelity missing from dev events manifest"
    )


def test_fragment_referenced_in_dev_template():
    """The dev instructions.md template must have the include directive — without it,
    the manifest entry is dead weight (compose only inlines what the template requests)."""
    template = DEV_TEMPLATE.read_text(encoding="utf-8")
    assert "{{include: common/pickup-comment-fidelity}}" in template, (
        "{{include: common/pickup-comment-fidelity}} missing from dev template"
    )


def test_implement_tasks_has_8b_bis_step():
    content = IMPLEMENT_TASKS.read_text(encoding="utf-8")
    assert "8b-bis" in content, (
        "implement-tasks must add a 8b-bis pickup-comment fidelity step"
    )
    assert "#9946" in content, (
        "implement-tasks 8b-bis must reference the issue number for traceability"
    )


def test_triage_issues_has_7b_bis_step():
    content = TRIAGE_ISSUES.read_text(encoding="utf-8")
    assert "7b-bis" in content, (
        "triage-issues must add a 7b-bis pickup-comment fidelity step"
    )
    assert "#9946" in content, (
        "triage-issues 7b-bis must reference the issue number for traceability"
    )


def test_triage_issues_crossref_to_implement_tasks_not_off_by_one():
    """Pre-9946, triage-issues referenced 'Step 9b/9c in implement-tasks' but
    implement-tasks uses 8b/8c. Lock this in so the next drift gets caught."""
    content = TRIAGE_ISSUES.read_text(encoding="utf-8")
    assert "Step 8b in implement-tasks" in content, (
        "triage-issues should cross-reference Step 8b (was 9b before #9946 fix)"
    )
    assert "Step 8c in implement-tasks" in content, (
        "triage-issues should cross-reference Step 8c (was 9c before #9946 fix)"
    )


@pytest.mark.parametrize("role", ["skill"])
def test_fragment_wired_in_v2_link_stage_for_dev_variant(role):
    """End-to-end: the v2 link-stage output for the worker/skill variant
    must wire ``common/pickup-comment-fidelity`` via an ``{{include:}}``
    directive — assemble (LLM polish) then expands the directive into
    the full fragment body in the deployed ``CLAUDE.md``.

    Pre-E6 this test asserted the resolved ``<!-- sub-skill: X -->``
    marker + body content from v1's ``compose_role`` (which inlined
    includes deterministically). Post-E6 (#10685) the link stage leaves
    ``{{include:}}`` directives raw — the same include is still there,
    just not yet expanded. The body-content assertions retire with the
    v1 compose path; the wiring invariant survives as the directive check
    here.
    """
    composed = _v2_compose_for(role)
    assert "{{include: common/pickup-comment-fidelity}}" in composed, (
        f"v2 link-stage output for {role} is missing the "
        f"common/pickup-comment-fidelity include directive — either the "
        f"L2 source dropped the directive or the manifest no longer "
        f"routes the fragment through the worker template."
    )
