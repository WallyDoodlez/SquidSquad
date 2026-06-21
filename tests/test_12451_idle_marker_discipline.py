"""#12451 S2 — write-on-transition idle-marker discipline in the event-mode
boot fragment.

`event-mode-contract.md` is a high-blast-radius fragment every event-mode agent
Reads at boot (runtime-loaded by boot-bootstrap). S2 adds the write-on-transition
idle-marker discipline (AC8): the agent keeps `current-state` honest — writing the
task marker when it starts an item and the `idle` marker when it goes idle or a
held task is closed/handed-off/reassigned — so a just-closed task is never named
as *current* activity. This is the write-side half of the #12854 lingering-stale-
content fix (the reader-side half is health_check's `current_state_stale` flag,
PR #13131).

Per the DS review (CODE-REVIEW-12451-S2), the discipline is a single Always-On
Rule covering ALL pickup/idle paths (boot, Case B, Case C, idle-cooldown-loop),
not a Case-C-only instruction — otherwise non-Case-C pickups leave a false-idle
`current-state`. These are presence locks on the load-bearing tokens (not brittle
prose anchors); the behavioral WHEN/invariant is the verifier-authored
comprehension spec per AC8 / the #9184 workflow.
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FRAGMENT = REPO_ROOT / "references" / "sub-skills" / "common-events" / "event-mode-contract.md"


@pytest.fixture
def fragment_text():
    assert FRAGMENT.exists(), f"event-mode-contract fragment missing: {FRAGMENT}"
    return FRAGMENT.read_text(encoding="utf-8")


def _section(text, start_anchor, end_anchor):
    start = text.index(start_anchor)
    end = text.index(end_anchor, start + len(start_anchor))
    return text[start:end]


def _always_on(text):
    return _section(text, "### Always-On Rules", "### Harness-Loss Recovery")


def _case_c(text):
    return _section(text, "### Case C", "### Case D")


def test_honest_current_state_rule_present(fragment_text):
    """A general Always-On rule governs current-state honesty (all pickup paths)."""
    rule = _always_on(fragment_text)
    assert "Keep `current-state` honest" in rule
    assert "status-bar-self idle" in rule


def test_rule_covers_all_pickup_paths(fragment_text):
    """The rule is explicitly cross-path (not Case-C-only) — DS Finding 1."""
    rule = _always_on(fragment_text)
    assert "status-bar-self <phase>" in rule  # task marker written on start
    # transition-driven, not a file-age cadence
    assert "cadence" in rule.lower()


def test_rule_ties_to_12854_defect(fragment_text):
    """The discipline names the lingering-stale-content defect it fixes."""
    assert "#12854" in _always_on(fragment_text)


def test_rule_covers_external_reassignment(fragment_text):
    """DS Finding 2: a held task handed off / reassigned away also clears the marker."""
    rule = _always_on(fragment_text).lower()
    assert "reassigned" in rule or "handed off" in rule


def test_inline_marker_self_contained(fragment_text):
    """DS Finding 3: the inline marker is DEFINED here, not just referenced."""
    rule = _always_on(fragment_text)
    assert 'status-bar-self inline ""' in rule


def test_case_c_instantiates_idle_write(fragment_text):
    """Case C (after-work) writes the idle marker, tying to the general rule + #12854."""
    case_c = _case_c(fragment_text)
    assert "status-bar-self idle" in case_c
    assert "#12854" in case_c
