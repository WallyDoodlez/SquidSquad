"""#12451 S2 — write-on-transition idle-marker discipline in the event-mode
boot fragment.

`event-mode-contract.md` is a high-blast-radius fragment every event-mode agent
Reads at boot (runtime-loaded by boot-bootstrap). S2 adds the write-on-transition
idle-marker discipline (AC8): on a task close / hand-off / change the agent writes
the `current-state` idle marker so the just-closed task is no longer named as
*current* activity — the write-side half of the #12854 lingering-stale-content
fix (the reader-side half is health_check's `current_state_stale` flag, PR #13131).

These are presence locks on the load-bearing tokens (not brittle prose anchors):
they ensure the discipline cannot be silently dropped from the boot fragment.
The behavioral check (WHEN to write it, and the no-stale-content invariant) is the
verifier-authored comprehension spec per AC8 / the #9184 workflow.
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FRAGMENT = REPO_ROOT / "references" / "sub-skills" / "common-events" / "event-mode-contract.md"


@pytest.fixture
def fragment_text():
    assert FRAGMENT.exists(), f"event-mode-contract fragment missing: {FRAGMENT}"
    return FRAGMENT.read_text(encoding="utf-8")


def _case_c(text):
    """Return the Case C section body (where the idle-marker discipline lives)."""
    start = text.index("### Case C")
    # Case C ends at the next '### Case' heading.
    nxt = text.index("### Case D", start)
    return text[start:nxt]


def test_idle_marker_command_present(fragment_text):
    """The fragment names the concrete idle-marker write command."""
    assert "status-bar-self idle" in fragment_text


def test_idle_marker_lives_in_case_c(fragment_text):
    """The write-on-transition discipline is anchored in Case C (after work)."""
    case_c = _case_c(fragment_text)
    assert "status-bar-self idle" in case_c


def test_idle_marker_references_12854_defect(fragment_text):
    """The discipline is tied to the lingering-stale-content defect it fixes."""
    case_c = _case_c(fragment_text)
    assert "#12854" in case_c


def test_write_on_transition_not_cadence(fragment_text):
    """The trigger is the transition, explicitly NOT a file-age cadence."""
    case_c = _case_c(fragment_text).lower()
    assert "cadence" in case_c  # the fragment contrasts transition-driven vs cadence
    # the new-task marker is written on pickup, too (write-on-transition both ways)
    assert "status-bar-self <phase>" in _case_c(fragment_text)


def test_idle_marker_distinct_from_inline(fragment_text):
    """AC8c boundary: the idle marker is not conflated with the inline marker."""
    case_c = _case_c(fragment_text)
    assert "inline" in case_c
