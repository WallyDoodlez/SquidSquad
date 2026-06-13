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

from _v2_test_helpers import v2_compose_for as _v2_compose_for  # noqa: E402

FRAGMENT = REPO / "references" / "sub-skills" / "common" / "pickup-comment-fidelity.md"
# #11503 rebind: role `dev` was renamed to `worker` in #6274; paths updated accordingly.
WORKER_TEMPLATE = REPO / "references" / "roles" / "worker" / "instructions.md"
# #11503 rebind: v2 (E6 #10685) merged includes.yml + includes-events.yml into a
# single unified includes.yml; includes-events.yml no longer exists.
WORKER_MANIFEST = REPO / "references" / "roles" / "worker" / "includes.yml"
IMPLEMENT_TASKS = REPO / "references" / "sub-skills" / "roles" / "worker" / "implement-tasks.md"
TRIAGE_ISSUES = REPO / "references" / "sub-skills" / "roles" / "worker" / "triage-issues.md"


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


def test_fragment_in_worker_manifest():
    """pickup-comment-fidelity must be in the unified worker manifest.

    #11503 rebind: role `dev` renamed to `worker` (#6274); split poll/event
    manifests merged into a single includes.yml in E6 (#10685).  Both the
    old polling-manifest and event-manifest guarantees are now covered by
    the single WORKER_MANIFEST check.
    """
    manifest = yaml.safe_load(WORKER_MANIFEST.read_text(encoding="utf-8"))
    assert "common/pickup-comment-fidelity" in manifest["includes"], (
        "common/pickup-comment-fidelity missing from worker unified manifest"
    )


def test_fragment_referenced_in_worker_template():
    """The worker instructions.md must wire the pickup-comment-fidelity step.

    #11503 rebind: role `dev` renamed to `worker` (#6274).  In v2 the
    instructions.md uses a runtime ``→ run sub-skill:`` marker at a named
    step anchor (step:cycle/pickup-comment-fidelity), not the v1-style
    ``{{include:}}`` compile-time directive.  Assert the runtime wiring
    exists and the step ID is present — the manifest entry alone is
    insufficient without the step anchor in the template.
    """
    template = WORKER_TEMPLATE.read_text(encoding="utf-8")
    assert "→ run sub-skill: pickup-comment-fidelity" in template, (
        "→ run sub-skill: pickup-comment-fidelity missing from worker instructions.md"
    )
    assert "step:cycle/pickup-comment-fidelity" in template, (
        "step:cycle/pickup-comment-fidelity step anchor missing from worker instructions.md"
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
def test_fragment_renders_in_composed_worker_variant_claude_md(role):
    """End-to-end: composing the worker (skill) variant CLAUDE.md must wire
    the pickup-comment-fidelity runtime marker and its step anchor.

    #11503 rebind: role `dev` renamed to `worker` (#6274).  In v2
    (post-E6 #10685) sub-skill bodies are NOT inlined at compose time —
    they are loaded at runtime via ``→ run sub-skill:`` markers.  The
    old assertions for ``<!-- sub-skill: pickup-comment-fidelity -->`` and
    body-text fragments (State-file filter, Test-result fidelity,
    Prior-cycle phantoms) no longer apply.

    The v2 invariant: the composed CLAUDE.md must contain both the
    step-anchor line (``step:cycle/pickup-comment-fidelity``) and the
    runtime ``→ run sub-skill: pickup-comment-fidelity`` marker — these
    confirm the fragment is wired into the agent's cycle, not merely listed
    in the manifest as dead weight.
    """
    composed = _v2_compose_for(role)
    assert "step:cycle/pickup-comment-fidelity" in composed, (
        f"step anchor step:cycle/pickup-comment-fidelity missing from composed {role}"
    )
    assert "→ run sub-skill: pickup-comment-fidelity" in composed, (
        f"runtime sub-skill marker for pickup-comment-fidelity missing from composed {role}"
    )
