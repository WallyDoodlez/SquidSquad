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
    # Default live status labels to empty so the forced-swap helper falls back
    # to from_label unless a test injects a specific live state.
    monkeypatch.setattr(tracker, "_get_issue_status_labels", lambda _n: set())
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
    def test_force_permits_arbitrary_status_change(self, monkeypatch, stub_forge, frm, to):
        """--force permits ANY from->to (none of these touch a ship gate).

        Exercises the REAL forced path: the live status label equals `frm`, so
        the forced swap removes the live label (== from) and adds `to`. (Not the
        empty-live-set fallback — that is covered separately.)"""
        monkeypatch.setattr(
            tracker, "_get_issue_status_labels", lambda _n: {f"status:{frm}"}
        )
        result = tracker.transition(999, frm, to, role="pm-lead", force=True)
        assert result is True
        stub_forge.edit_labels.assert_called_once_with(
            999, add=[f"status:{to}"], remove=[f"status:{frm}"]
        )

    def test_force_arbitrary_change_falls_back_to_from_on_api_failure(self, stub_forge):
        """When the live-label query fails (empty set), the forced swap falls
        back to removing the caller-supplied from_label (best effort)."""
        # stub_forge defaults _get_issue_status_labels to empty (API-failure sim).
        result = tracker.transition(999, "approved", "pending", role="pm-lead", force=True)
        assert result is True
        stub_forge.edit_labels.assert_called_once_with(
            999, add=["status:pending"], remove=["status:approved"]
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

    def test_force_on_LEGAL_ship_still_blocked_by_unmerged_pr(self, monkeypatch, stub_forge):
        """Regression guard (DS-12475 F12): the ship gate keys on to_label, so
        even a LEGAL forced pending-ship -> shipped must block on an open PR —
        catches a future `if not force` accidentally added to step 5."""
        monkeypatch.setattr(tracker, "_check_unmerged_pr", lambda _n: (778, "http://pr/778"))
        with pytest.raises(SystemExit) as exc:
            tracker.transition(999, "pending-ship", "shipped", role="dm-lead", force=True)
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

    def test_force_tc_gate_blocks_on_failing_coverage(self, monkeypatch, stub_forge):
        """Step 4 also blocks (under force) when QA-RESULTS exists but coverage
        fails — the check_coverage != 0 branch (DS-12475 F15)."""
        fake_tc = MagicMock()
        fake_tc._discover_files.return_value = (Path("TEST-PLAN-999.md"), Path("QA-RESULTS-999.md"))
        fake_tc.check_coverage.return_value = 1  # coverage fails
        monkeypatch.setitem(sys.modules, "tc_coverage", fake_tc)
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

    def test_forced_swap_strips_live_status_label_not_claimed_from(self, monkeypatch, stub_forge):
        """DS-12475 F2/F14: a wrong from_status under force must NOT leave two
        status labels. The swap removes the ACTUAL live status label(s), not the
        caller's claimed from. Here the issue is really in-progress but the
        caller wrongly passes from=approved; the remove must target the live
        label so the issue ends with exactly status:planning."""
        monkeypatch.setattr(
            tracker, "_get_issue_status_labels", lambda _n: {"status:in-progress"}
        )
        result = tracker.transition(999, "approved", "planning", role="pm-lead", force=True)
        assert result is True
        stub_forge.edit_labels.assert_called_once_with(
            999, add=["status:planning"], remove=["status:in-progress"]
        )

    def test_forced_swap_strips_multiple_stale_status_labels(self, monkeypatch, stub_forge):
        """If the issue is already corrupted with two status labels, a forced
        transition cleans BOTH and lands exactly the target."""
        monkeypatch.setattr(
            tracker, "_get_issue_status_labels",
            lambda _n: {"status:approved", "status:in-progress"},
        )
        result = tracker.transition(999, "approved", "planning", role="pm-lead", force=True)
        assert result is True
        args, kwargs = stub_forge.edit_labels.call_args
        assert kwargs["add"] == ["status:planning"]
        assert sorted(kwargs["remove"]) == ["status:approved", "status:in-progress"]

    def test_nonforced_swap_does_not_query_live_labels(self, monkeypatch, stub_forge):
        """The hot non-forced path must NOT add a gh round-trip — it trusts
        from_label (legality guarantees it is the real predecessor)."""
        called = {"n": 0}

        def _spy(_n):
            called["n"] += 1
            return {"status:in-progress"}

        monkeypatch.setattr(tracker, "_get_issue_status_labels", _spy)
        # in-progress -> approved is a legal edge for the assigned worker.
        monkeypatch.setattr(tracker, "_get_issue_role_labels", lambda _n: {"skill"})
        tracker.transition(999, "in-progress", "approved", role="skill-lead", force=False)
        assert called["n"] == 0
        stub_forge.edit_labels.assert_called_once_with(
            999, add=["status:approved"], remove=["status:in-progress"]
        )

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
        assert emitted["payload"]["issue_number"] == "999"
        assert emitted["role"] == "pm"  # "pm-lead" -> bare alias
