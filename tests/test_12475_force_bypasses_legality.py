"""Regression tests for #12475 — `tracker.py transition --force` must bypass
the legal-transition matrix (the human override that lets a human/PM correct a
mis-transition), while STILL enforcing the two ship-integrity gates.

Before #12475, `--force` only bypassed the authority + unread-feedback guards;
the legality matrix (step 1 of `transition()`) was unconditional, so a task
over-approved in an 'approve all' batch could not be walked back
`approved -> planning` — the reproducer below.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))

import tracker  # noqa: E402


@pytest.fixture
def stub_forge(monkeypatch):
    """Stub the forge so transition() side-effects (label swap, close, event)
    don't touch gh / the network. Returns the MagicMock adapter for asserts."""
    adapter = MagicMock()
    monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: adapter)
    # Default ship-integrity probes to "clean" so they don't block unless a
    # test overrides them; harmless for non-shipped targets (never called).
    monkeypatch.setattr(tracker, "_check_unmerged_pr", lambda _n: None)
    monkeypatch.setattr(tracker, "_check_unmerged_branch", lambda _n: None)
    return adapter


# ---------------------------------------------------------------------------
# The reproducer: approved -> planning is illegal, but --force must allow it.
# ---------------------------------------------------------------------------


class TestForceBypassesLegality:
    def test_repro_approved_to_planning_forced_succeeds(self, stub_forge):
        """#12475 exact repro: walk an over-approved task back to planning."""
        result = tracker.transition(
            12451, "approved", "planning", role="pm-lead", force=True
        )
        assert result is True
        stub_forge.edit_labels.assert_called_once_with(
            12451, add=["status:planning"], remove=["status:approved"]
        )

    def test_same_transition_without_force_is_rejected(self, stub_forge):
        """Regression guard: the legality matrix still blocks when NOT forced.

        approved's only legal target is in-progress; planning must be rejected.
        """
        with pytest.raises(SystemExit) as exc:
            tracker.transition(12451, "approved", "planning", role="pm-lead", force=False)
        assert exc.value.code == 1
        stub_forge.edit_labels.assert_not_called()

    @pytest.mark.parametrize("frm,to", [
        ("approved", "pending"),
        ("in-progress", "approved"),   # legal, sanity (force is a no-op on legal)
        ("pending-test", "planning"),
        ("shipped", "in-progress"),    # out of a terminal state
    ])
    def test_force_permits_arbitrary_status_change(self, stub_forge, frm, to):
        """--force permits ANY from->to (none of these touch a ship gate)."""
        result = tracker.transition(999, frm, to, role="pm-lead", force=True)
        assert result is True
        stub_forge.edit_labels.assert_called_once_with(
            999, add=[f"status:{to}"], remove=[f"status:{frm}"]
        )


# ---------------------------------------------------------------------------
# Ship-integrity gates remain hard invariants EVEN under --force.
# ---------------------------------------------------------------------------


class TestForceDoesNotBypassShipIntegrity:
    def test_force_to_shipped_still_blocked_by_unmerged_pr(self, monkeypatch, stub_forge):
        """Forcing ->shipped with an open PR must still block (step 5)."""
        monkeypatch.setattr(tracker, "_check_unmerged_pr", lambda _n: (777, "http://pr/777"))
        # approved -> shipped is illegal; --force bypasses legality and reaches
        # the unmerged-PR gate, which must still fire.
        with pytest.raises(SystemExit) as exc:
            tracker.transition(999, "approved", "shipped", role="pm-lead", force=True)
        assert exc.value.code == 1
        stub_forge.edit_labels.assert_not_called()

    def test_force_to_shipped_still_blocked_by_unmerged_branch(self, monkeypatch, stub_forge):
        """Forcing ->shipped with an unmerged branch (and no merged PR) blocks."""
        monkeypatch.setattr(tracker, "_check_unmerged_branch", lambda _n: ("squidsquad/task/999", 3))
        monkeypatch.setattr(tracker, "_check_merged_pr", lambda _n: None)
        with pytest.raises(SystemExit) as exc:
            tracker.transition(999, "approved", "shipped", role="pm-lead", force=True)
        assert exc.value.code == 1
        stub_forge.edit_labels.assert_not_called()

    def test_force_pending_test_to_pending_ship_still_hits_tc_gate(self, monkeypatch, stub_forge):
        """Forcing pending-test->pending-ship still enforces TC coverage (step 4)."""
        fake_tc = MagicMock()
        fake_tc._discover_files.return_value = (Path("TEST-PLAN-999.md"), None)  # plan, no QA-RESULTS
        monkeypatch.setitem(sys.modules, "tc_coverage", fake_tc)
        # pending-test -> pending-ship IS legal, but force or not the TC gate
        # must block when a test plan exists with no QA-RESULTS.
        with pytest.raises(SystemExit) as exc:
            tracker.transition(999, "pending-test", "pending-ship", role="pm-lead", force=True)
        assert exc.value.code == 1
        stub_forge.edit_labels.assert_not_called()


# ---------------------------------------------------------------------------
# Side-effects of a forced arbitrary transition run coherently (no stranding).
# ---------------------------------------------------------------------------


class TestForcedTransitionSideEffects:
    def test_forced_to_shipped_auto_closes_when_clean(self, stub_forge):
        """A forced ->shipped with clean ship gates still auto-closes the issue."""
        # stub_forge defaults _check_unmerged_pr/_branch to None (clean).
        result = tracker.transition(999, "approved", "shipped", role="pm-lead", force=True)
        assert result is True
        stub_forge.edit_labels.assert_called_once_with(
            999, add=["status:shipped"], remove=["status:approved"]
        )
        stub_forge.close_issue.assert_called_once_with(999)

    def test_forced_transition_emits_status_event(self, monkeypatch, stub_forge):
        """The status-transition event still emits for a forced illegal edge."""
        emitted = {}

        def _fake_emit(event_type, role, payload=None):
            emitted["type"] = event_type
            emitted["role"] = role
            emitted["payload"] = payload

        fake_bus = MagicMock()
        fake_bus.emit = _fake_emit
        monkeypatch.setitem(sys.modules, "event_bus", fake_bus)
        tracker.transition(999, "approved", "planning", role="pm-lead", force=True)
        assert emitted["type"] == "status-transition"
        assert emitted["payload"]["from"] == "approved"
        assert emitted["payload"]["to"] == "planning"
