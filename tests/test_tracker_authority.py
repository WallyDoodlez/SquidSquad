"""Unit tests for tracker.py role-based transition authority (#320).

Verifies that `transition()` enforces role authority in addition to
state-machine legality, preventing cross-role transitions (e.g. skill-lead
shipping an issue that only DM should ship).
"""

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))

import tracker  # noqa: E402


# ---------------------------------------------------------------------------
# Role canonicalization
# ---------------------------------------------------------------------------


class TestCanonicalizeRole:
    @pytest.mark.parametrize("inp,expected", [
        ("skill-lead", "skill"),
        ("fe-lead", "fe"),
        ("pm", "pm"),
        ("pm-lead", "pm"),
        ("qa", "qa"),
        ("qa-lead", "qa"),
        ("dm-lead", "dm"),
        ("qa", "qa"),
        ("qa-lead", "qa"),
        ("pm (pm)", "pm"),
        ("qa-lead (tester)", "qa"),
        ("skill-lead (wally)", "skill"),
    ])
    def test_canonicalization(self, inp, expected):
        assert tracker._canonicalize_role(inp) == expected

    def test_none(self):
        assert tracker._canonicalize_role(None) is None

    def test_empty(self):
        assert tracker._canonicalize_role("") == ""


# ---------------------------------------------------------------------------
# Authority table coverage
# ---------------------------------------------------------------------------


class TestAuthorityTable:
    def test_every_legal_transition_has_authority(self):
        """Every edge in LEGAL_TRANSITIONS must appear in ROLE_AUTHORITY.

        Missing entries would mean a legal transition with no authorized
        role — the script would reject it (fail-closed), which is a latent
        footgun. The tests catch this at dev time.
        """
        legal_edges = {
            (frm, to)
            for frm, tos in tracker.LEGAL_TRANSITIONS.items()
            for to in tos
        }
        auth_edges = set(tracker.ROLE_AUTHORITY.keys())
        missing = legal_edges - auth_edges
        assert not missing, f"Legal transitions without authority: {missing}"

    def test_no_authority_for_illegal_transitions(self):
        """ROLE_AUTHORITY must not contain edges that aren't legal."""
        legal_edges = {
            (frm, to)
            for frm, tos in tracker.LEGAL_TRANSITIONS.items()
            for to in tos
        }
        auth_edges = set(tracker.ROLE_AUTHORITY.keys())
        extra = auth_edges - legal_edges
        assert not extra, f"Authority entries for illegal transitions: {extra}"

    def test_terminal_shipped_has_no_authority(self):
        """Nothing can transition out of shipped — no authority entry either."""
        assert tracker.LEGAL_TRANSITIONS["status:shipped"] == set()
        from_shipped = [k for k in tracker.ROLE_AUTHORITY if k[0] == "status:shipped"]
        assert not from_shipped


# ---------------------------------------------------------------------------
# _check_authority — the heart of the fix
# ---------------------------------------------------------------------------


@pytest.fixture
def stub_role_labels(monkeypatch):
    """Stub _get_issue_role_labels so authority tests don't hit gh."""
    holder = {"labels": {"skill"}}

    def _fake(_number):
        return holder["labels"]

    monkeypatch.setattr(tracker, "_get_issue_role_labels", _fake)
    return holder


class TestCheckAuthority:
    # ---- The exact bug from #320 ----
    def test_skill_lead_cannot_ship(self, stub_role_labels):
        """Reproducer: skill-lead should NOT be able to ship (DM only).

        This is the specific scenario that motivated the bug.
        """
        ok, reason = tracker._check_authority(
            269, "status:pending-ship", "status:shipped", "skill-lead"
        )
        assert not ok
        assert "not authorized" in reason
        assert "dm" in reason

    def test_dm_lead_can_ship(self, stub_role_labels):
        ok, reason = tracker._check_authority(
            269, "status:pending-ship", "status:shipped", "dm-lead"
        )
        assert ok, reason

    def test_dm_short_form_can_ship(self, stub_role_labels):
        ok, _ = tracker._check_authority(
            269, "status:pending-ship", "status:shipped", "dm"
        )
        assert ok

    # ---- DM skip-QA flow (#6261) ----
    def test_dm_can_skip_qa_in_progress_to_pending_ship(self, stub_role_labels):
        """DM skips QA — goes directly from in-progress to pending-ship."""
        ok, reason = tracker._check_authority(
            269, "status:in-progress", "status:pending-ship", "dm-lead"
        )
        assert ok, reason

    def test_skill_cannot_skip_qa_in_progress_to_pending_ship(self, stub_role_labels):
        """Non-DM roles cannot skip QA."""
        ok, reason = tracker._check_authority(
            1, "status:in-progress", "status:pending-ship", "skill-lead"
        )
        assert not ok

    def test_dm_can_rollback_pending_ship_to_in_progress(self, stub_role_labels):
        """DM merge conflict rollback (#6261)."""
        ok, reason = tracker._check_authority(
            269, "status:pending-ship", "status:in-progress", "dm-lead"
        )
        assert ok, reason

    # ---- PM intake flow ----
    def test_pm_can_approve_pending(self, stub_role_labels):
        ok, _ = tracker._check_authority(
            1, "status:pending", "status:approved", "pm-lead"
        )
        assert ok

    def test_skill_cannot_approve_pending(self, stub_role_labels):
        ok, reason = tracker._check_authority(
            1, "status:pending", "status:approved", "skill-lead"
        )
        assert not ok
        assert "pm" in reason

    def test_pm_can_transition_planning_to_planned(self, stub_role_labels):
        ok, _ = tracker._check_authority(
            1, "status:planning", "status:planned", "pm"
        )
        assert ok

    # ---- QA/PM verification flow ----
    # Both QA and PM are authorized for verification transitions.
    # Fixed team architecture (#6261): PM + QA + DM always present.
    def test_qa_can_approve_pending_test(self, stub_role_labels):
        ok, _ = tracker._check_authority(
            1, "status:pending-test", "status:pending-ship", "qa-lead"
        )
        assert ok

    def test_qa_can_reject_pending_test(self, stub_role_labels):
        ok, _ = tracker._check_authority(
            1, "status:pending-test", "status:in-progress", "qa"
        )
        assert ok

    def test_pm_can_approve_pending_test(self, stub_role_labels):
        """PM verification authority — regression for #320 re-open."""
        ok, _ = tracker._check_authority(
            1, "status:pending-test", "status:pending-ship", "pm-lead"
        )
        assert ok

    def test_pm_can_reject_pending_test(self, stub_role_labels):
        """PM must be able to bounce back to in-progress when it finds gaps."""
        ok, _ = tracker._check_authority(
            1, "status:pending-test", "status:in-progress", "pm"
        )
        assert ok

    def test_skill_cannot_approve_pending_test(self, stub_role_labels):
        ok, reason = tracker._check_authority(
            1, "status:pending-test", "status:pending-ship", "skill-lead"
        )
        assert not ok
        # Error should mention the allowed roles (pm and qa)
        assert "pm" in reason and "qa" in reason

    def test_dm_cannot_approve_pending_test(self, stub_role_labels):
        """DM ships, never verifies."""
        ok, _ = tracker._check_authority(
            1, "status:pending-test", "status:pending-ship", "dm-lead"
        )
        assert not ok

    # ---- Dev pickup (assignee check) ----
    def test_assigned_dev_can_pick_up(self, stub_role_labels):
        stub_role_labels["labels"] = {"skill"}
        ok, _ = tracker._check_authority(
            1, "status:approved", "status:in-progress", "skill-lead"
        )
        assert ok

    def test_unassigned_dev_cannot_pick_up(self, stub_role_labels):
        """fe-lead cannot touch a role:skill issue — even though both are dev."""
        stub_role_labels["labels"] = {"skill"}
        ok, reason = tracker._check_authority(
            1, "status:approved", "status:in-progress", "fe-lead"
        )
        assert not ok
        assert "not assigned" in reason

    def test_multiple_role_labels(self, stub_role_labels):
        """If an issue has role:skill and role:dm, both may work on it."""
        stub_role_labels["labels"] = {"skill", "dm"}
        ok1, _ = tracker._check_authority(
            1, "status:open", "status:pending-test", "skill-lead"
        )
        ok2, _ = tracker._check_authority(
            1, "status:open", "status:pending-test", "dm-lead"
        )
        assert ok1 and ok2

    def test_assignee_transition_without_role_label(self, stub_role_labels):
        """Assignee-based transitions fail closed when issue has no role:* label."""
        stub_role_labels["labels"] = set()
        ok, reason = tracker._check_authority(
            1, "status:approved", "status:in-progress", "skill-lead"
        )
        assert not ok
        assert "no role:*" in reason

    # ---- DM bug triage (dev-style transition) ----
    def test_dm_can_triage_own_bug(self, stub_role_labels):
        """DM uses open → pending-test for their own bug triage."""
        stub_role_labels["labels"] = {"dm"}
        ok, _ = tracker._check_authority(
            1, "status:open", "status:pending-test", "dm-lead"
        )
        assert ok

    def test_skill_cannot_triage_dm_bug(self, stub_role_labels):
        stub_role_labels["labels"] = {"dm"}
        ok, _ = tracker._check_authority(
            1, "status:open", "status:pending-test", "skill-lead"
        )
        assert not ok

    # ---- Missing role ----
    def test_missing_role_rejected(self, stub_role_labels):
        ok, reason = tracker._check_authority(
            1, "status:approved", "status:in-progress", None
        )
        assert not ok
        assert "--role is required" in reason

    def test_empty_role_rejected(self, stub_role_labels):
        ok, reason = tracker._check_authority(
            1, "status:approved", "status:in-progress", ""
        )
        assert not ok
        assert "--role is required" in reason

    # ---- Short vs long form equivalence ----
    @pytest.mark.parametrize("role_form", ["pm", "pm-lead", "pm (alice)"])
    def test_pm_forms_all_accepted(self, stub_role_labels, role_form):
        ok, _ = tracker._check_authority(
            1, "status:pending", "status:approved", role_form
        )
        assert ok

    @pytest.mark.parametrize("role_form", ["dm", "dm-lead", "dm (wally)"])
    def test_dm_forms_all_accepted(self, stub_role_labels, role_form):
        ok, _ = tracker._check_authority(
            1, "status:pending-ship", "status:shipped", role_form
        )
        assert ok


# ---------------------------------------------------------------------------
# #328 Phase E — new pending-human-* transitions (Q-new4 / Q7 / Q-new11)
# ---------------------------------------------------------------------------


class TestPendingHumanApproval:
    """PM owns the new pending-human-approval intake edges."""

    def test_pm_can_move_to_planning(self, stub_role_labels):
        ok, _ = tracker._check_authority(
            1, "status:pending-human-approval", "status:planning", "pm-lead"
        )
        assert ok

    def test_pm_can_fast_track_to_approved(self, stub_role_labels):
        ok, _ = tracker._check_authority(
            1, "status:pending-human-approval", "status:approved", "pm"
        )
        assert ok

    def test_skill_cannot_approve_pending_human_approval(self, stub_role_labels):
        ok, reason = tracker._check_authority(
            1, "status:pending-human-approval", "status:approved", "skill-lead"
        )
        assert not ok
        assert "pm" in reason

    def test_dm_cannot_touch_intake(self, stub_role_labels):
        ok, _ = tracker._check_authority(
            1, "status:pending-human-approval", "status:planning", "dm-lead"
        )
        assert not ok


class TestPendingHumanReview:
    """HITL loop — the assigned worker drives pause + redirect + approve."""

    def test_assigned_worker_can_self_pause(self, stub_role_labels):
        stub_role_labels["labels"] = {"qa"}
        ok, _ = tracker._check_authority(
            1, "status:in-progress", "status:pending-human-review", "qa-lead"
        )
        assert ok

    def test_unassigned_worker_cannot_self_pause(self, stub_role_labels):
        stub_role_labels["labels"] = {"qa"}
        ok, reason = tracker._check_authority(
            1, "status:in-progress", "status:pending-human-review", "skill-lead"
        )
        assert not ok
        assert "not assigned" in reason

    def test_assigned_worker_can_handle_redirect(self, stub_role_labels):
        """QA detects a 'redirect' human comment and resumes iteration."""
        stub_role_labels["labels"] = {"qa"}
        ok, _ = tracker._check_authority(
            1, "status:pending-human-review", "status:in-progress", "qa-lead"
        )
        assert ok

    def test_assigned_worker_can_handle_approval(self, stub_role_labels):
        """QA detects a 'ship it' human comment and moves to pending-ship."""
        stub_role_labels["labels"] = {"qa"}
        ok, _ = tracker._check_authority(
            1, "status:pending-human-review", "status:pending-ship", "qa-lead"
        )
        assert ok

    def test_pm_can_approve_hitl_via_pr_flow(self, stub_role_labels):
        """PM can ship pending-human-review items (PR Flow merge path, #3493)."""
        stub_role_labels["labels"] = {"qa"}
        ok, _ = tracker._check_authority(
            1, "status:pending-human-review", "status:pending-ship", "pm-lead"
        )
        assert ok

    def test_pm_can_redirect_hitl_via_pr_flow(self, stub_role_labels):
        """PM can redirect pending-human-review back to in-progress (#3493)."""
        stub_role_labels["labels"] = {"qa"}
        ok, _ = tracker._check_authority(
            1, "status:pending-human-review", "status:in-progress", "pm-lead"
        )
        assert ok


class TestPendingHumanSetup:
    """Worker self-pauses for tool/env setup; PM completes setup and hands back."""

    def test_assigned_worker_can_self_pause_for_setup(self, stub_role_labels):
        stub_role_labels["labels"] = {"qa"}
        ok, _ = tracker._check_authority(
            1, "status:in-progress", "status:pending-human-setup", "qa-lead"
        )
        assert ok

    def test_other_worker_cannot_self_pause_for_setup(self, stub_role_labels):
        stub_role_labels["labels"] = {"qa"}
        ok, reason = tracker._check_authority(
            1, "status:in-progress", "status:pending-human-setup", "skill-lead"
        )
        assert not ok
        assert "not assigned" in reason

    def test_pm_completes_setup_and_hands_back(self, stub_role_labels):
        """PM owns the resume edge because tool config + composition is PM's job."""
        stub_role_labels["labels"] = {"qa"}
        ok, _ = tracker._check_authority(
            1, "status:pending-human-setup", "status:in-progress", "pm-lead"
        )
        assert ok

    def test_assigned_worker_cannot_resume_own_setup(self, stub_role_labels):
        """The worker that self-paused cannot resume itself — PM must do it.

        Rationale: if the worker could resume, it could shortcut the setup
        checklist. Requiring PM guarantees the infrastructure actually
        changed before the worker is allowed to continue.
        """
        stub_role_labels["labels"] = {"qa"}
        ok, reason = tracker._check_authority(
            1, "status:pending-human-setup", "status:in-progress", "qa-lead"
        )
        assert not ok
        assert "pm" in reason


class TestPhaseECoverage:
    """The coverage invariant must still hold after Phase E additions."""

    def test_every_legal_transition_has_authority_including_new_rows(self):
        legal_edges = {
            (frm, to)
            for frm, tos in tracker.LEGAL_TRANSITIONS.items()
            for to in tos
        }
        auth_edges = set(tracker.ROLE_AUTHORITY.keys())
        missing = legal_edges - auth_edges
        assert not missing, f"Legal transitions without authority: {missing}"

    def test_new_labels_are_in_status_labels_map(self):
        """Sanity — the short names are registered in STATUS_LABELS."""
        for short in (
            "pending-human-approval",
            "pending-human-review",
            "pending-human-setup",
        ):
            assert short in tracker.STATUS_LABELS
            assert tracker.STATUS_LABELS[short] == f"status:{short}"

    def test_old_pending_label_still_legal(self):
        """Additive phase — existing `pending` label must remain legal."""
        assert "status:pending" in tracker.LEGAL_TRANSITIONS
        assert "status:planning" in tracker.LEGAL_TRANSITIONS["status:pending"]
        assert ("status:pending", "status:planning") in tracker.ROLE_AUTHORITY


# ---------------------------------------------------------------------------
# end-to-end transition() behavior (without gh) — exit codes
# ---------------------------------------------------------------------------


class TestTransitionEnforcement:
    def test_unauthorized_transition_exits(self, monkeypatch, capsys):
        """transition() exits non-zero on authority failure, before any gh call."""
        # Ensure gh is never called
        def _fail(*a, **kw):
            raise AssertionError("gh should not be called on authority failure")

        monkeypatch.setattr(tracker, "_run_list", _fail)
        monkeypatch.setattr(tracker, "_get_issue_role_labels", lambda n: {"skill"})

        with pytest.raises(SystemExit) as excinfo:
            tracker.transition(269, "pending-ship", "shipped", role="skill-lead")
        assert excinfo.value.code == 1
        err = capsys.readouterr().err
        assert "Unauthorized" in err
        assert "not authorized" in err
        assert "--force" in err  # hint about override

    def test_force_bypasses_authority(self, monkeypatch):
        """--force skips authority check (human override)."""
        gh_calls = []

        class FakeResult:
            returncode = 0
            stdout = ""
            stderr = ""

        def _fake_run_list(cmd, **kw):
            gh_calls.append(cmd)
            return FakeResult()

        monkeypatch.setattr(tracker, "_run_list", _fake_run_list)
        # Authority would normally reject skill-lead here
        tracker.transition(269, "pending-ship", "shipped",
                           role="skill-lead", force=True)
        # gh was actually called
        assert any("edit" in c for c in gh_calls)

    def test_illegal_transition_rejected_even_with_force(self, monkeypatch, capsys):
        """--force does NOT bypass legality (can't jump pending -> shipped)."""
        def _fail(*a, **kw):
            raise AssertionError("gh should not be called on illegal transition")

        monkeypatch.setattr(tracker, "_run_list", _fail)
        with pytest.raises(SystemExit) as excinfo:
            tracker.transition(1, "pending", "shipped",
                               role="pm-lead", force=True)
        assert excinfo.value.code == 1
        err = capsys.readouterr().err
        assert "Illegal transition" in err

    def test_missing_role_rejected(self, monkeypatch, capsys):
        def _fail(*a, **kw):
            raise AssertionError("gh should not be called when role missing")

        monkeypatch.setattr(tracker, "_run_list", _fail)
        monkeypatch.setattr(tracker, "_get_issue_role_labels", lambda n: {"skill"})
        with pytest.raises(SystemExit) as excinfo:
            tracker.transition(1, "approved", "in-progress", role=None)
        assert excinfo.value.code == 1
        err = capsys.readouterr().err
        assert "--role is required" in err


class TestStatusTransitionEventEmission:
    """#5856: transition() emits status-transition event on every transition."""

    def test_emits_status_transition_event(self, monkeypatch):
        """Every transition emits a status-transition event with correct payload."""
        emitted = []

        class FakeResult:
            returncode = 0
            stdout = ""
            stderr = ""

        monkeypatch.setattr(tracker, "_run_list", lambda *a, **kw: FakeResult())
        monkeypatch.setattr(tracker, "_get_issue_role_labels", lambda n: {"skill"})

        # Mock event_bus.emit to capture calls
        import types
        fake_bus = types.ModuleType("event_bus")
        fake_bus.emit = lambda event_type, role, payload=None, cycle_number=None: emitted.append(
            {"event_type": event_type, "role": role, "payload": payload}
        )
        monkeypatch.setitem(sys.modules, "event_bus", fake_bus)

        tracker.transition(42, "approved", "in-progress", role="skill-lead")

        assert len(emitted) == 1
        assert emitted[0]["event_type"] == "status-transition"
        assert emitted[0]["role"] == "skill"
        assert emitted[0]["payload"]["issue_number"] == "42"
        assert emitted[0]["payload"]["from"] == "approved"
        assert emitted[0]["payload"]["to"] == "in-progress"

    def test_emits_on_all_transitions_not_just_in_progress(self, monkeypatch):
        """Emission happens for pending-test, pending-ship, shipped — not just in-progress."""
        emitted = []

        class FakeResult:
            returncode = 0
            stdout = ""
            stderr = ""

        monkeypatch.setattr(tracker, "_run_list", lambda *a, **kw: FakeResult())
        monkeypatch.setattr(tracker, "_get_issue_role_labels", lambda n: {"pm"})

        import types
        fake_bus = types.ModuleType("event_bus")
        fake_bus.emit = lambda event_type, role, payload=None, cycle_number=None: emitted.append(
            {"event_type": event_type, "payload": payload}
        )
        monkeypatch.setitem(sys.modules, "event_bus", fake_bus)

        tracker.transition(99, "pending-test", "pending-ship", role="pm-lead", force=True)

        assert len(emitted) == 1
        assert emitted[0]["event_type"] == "status-transition"
        assert emitted[0]["payload"]["from"] == "pending-test"
        assert emitted[0]["payload"]["to"] == "pending-ship"

    def test_no_dead_task_start_task_end_events(self, monkeypatch):
        """#5856: task-start and task-end event types must not be emitted."""
        emitted = []

        class FakeResult:
            returncode = 0
            stdout = ""
            stderr = ""

        monkeypatch.setattr(tracker, "_run_list", lambda *a, **kw: FakeResult())
        monkeypatch.setattr(tracker, "_get_issue_role_labels", lambda n: {"skill"})

        import types
        fake_bus = types.ModuleType("event_bus")
        fake_bus.emit = lambda event_type, role, payload=None, cycle_number=None: emitted.append(event_type)
        monkeypatch.setitem(sys.modules, "event_bus", fake_bus)

        tracker.transition(42, "approved", "in-progress", role="skill-lead")

        assert "task-start" not in emitted
        assert "task-end" not in emitted
        assert "status-transition" in emitted


class TestPendingShipBackwardTransition:
    """pending-ship→in-progress backward transition for merge conflicts (#1727)."""

    def test_pm_can_route_back(self, monkeypatch):
        """PM can transition pending-ship→in-progress."""
        class FakeResult:
            returncode = 0
            stdout = ""
            stderr = ""

        def _fake_run_list(cmd, **kw):
            return FakeResult()

        monkeypatch.setattr(tracker, "_run_list", _fake_run_list)
        monkeypatch.setattr(tracker, "_check_unread_feedback", lambda n, r: [])
        # Should not raise
        tracker.transition(42, "pending-ship", "in-progress", role="pm-lead")

    def test_qa_can_route_back(self, monkeypatch):
        """QA can transition pending-ship→in-progress."""
        class FakeResult:
            returncode = 0
            stdout = ""
            stderr = ""

        def _fake_run_list(cmd, **kw):
            return FakeResult()

        monkeypatch.setattr(tracker, "_run_list", _fake_run_list)
        monkeypatch.setattr(tracker, "_check_unread_feedback", lambda n, r: [])
        tracker.transition(42, "pending-ship", "in-progress", role="qa-lead")

    def test_dev_cannot_route_back(self, monkeypatch, capsys):
        """Dev agents cannot transition pending-ship→in-progress."""
        def _fail(*a, **kw):
            raise AssertionError("gh should not be called")

        monkeypatch.setattr(tracker, "_run_list", _fail)
        monkeypatch.setattr(tracker, "_get_issue_role_labels", lambda n: {"skill"})

        with pytest.raises(SystemExit) as excinfo:
            tracker.transition(42, "pending-ship", "in-progress", role="skill-lead")
        assert excinfo.value.code == 1
        err = capsys.readouterr().err
        assert "Unauthorized" in err


# ---------------------------------------------------------------------------
# shipped PR guard (#1676)
# ---------------------------------------------------------------------------


class TestShippedPRGuard:
    """Transition to shipped must block if unmerged PR exists (#1676)."""

    def test_blocks_when_unmerged_pr_exists(self, monkeypatch, capsys):
        """shipped transition blocked when an open PR matches the issue number."""
        call_count = [0]

        class FakeResult:
            returncode = 0
            stdout = ""
            stderr = ""

        def _fake_run_list(cmd, **kw):
            call_count[0] += 1
            # PR list returns an open PR matching the issue
            if "pr" in cmd and "list" in cmd:
                r = FakeResult()
                r.stdout = json.dumps([
                    {"number": 99, "headRefName": "squidsquad/skill/42", "url": "http://pr/99"}
                ])
                return r
            return FakeResult()

        monkeypatch.setattr(tracker, "_run_list", _fake_run_list)

        with pytest.raises(SystemExit) as excinfo:
            tracker.transition(42, "pending-ship", "shipped", role="dm-lead")
        assert excinfo.value.code == 1
        err = capsys.readouterr().err
        assert "BLOCKED" in err
        assert "unmerged" in err.lower()
        assert "#99" in err

    def test_allows_when_no_pr(self, monkeypatch):
        """shipped transition proceeds when no matching PR exists."""
        class FakeResult:
            returncode = 0
            stdout = ""
            stderr = ""

        def _fake_run_list(cmd, **kw):
            if "pr" in cmd and "list" in cmd:
                r = FakeResult()
                r.stdout = "[]"
                return r
            return FakeResult()

        monkeypatch.setattr(tracker, "_run_list", _fake_run_list)
        # Should not raise — no unmerged PR
        tracker.transition(42, "pending-ship", "shipped", role="dm-lead")

    def test_force_does_not_bypass_pr_check(self, monkeypatch, capsys):
        """--force does NOT bypass the PR merge check (always enforced)."""
        class FakeResult:
            returncode = 0
            stdout = ""
            stderr = ""

        def _fake_run_list(cmd, **kw):
            if "pr" in cmd and "list" in cmd:
                r = FakeResult()
                r.stdout = json.dumps([
                    {"number": 99, "headRefName": "squidsquad/skill/42", "url": "http://pr/99"}
                ])
                return r
            return FakeResult()

        monkeypatch.setattr(tracker, "_run_list", _fake_run_list)
        # Force should NOT bypass the PR merge check
        with pytest.raises(SystemExit) as excinfo:
            tracker.transition(42, "pending-ship", "shipped", role="dm-lead", force=True)
        assert excinfo.value.code == 1
        err = capsys.readouterr().err
        assert "BLOCKED" in err
        assert "unmerged" in err.lower()



# ---------------------------------------------------------------------------
# shipped branch guard (#2110)
# ---------------------------------------------------------------------------


class TestShippedBranchGuard:
    """Transition to shipped must block if unmerged feature branch exists (#2110)."""

    def test_blocks_when_unmerged_branch_exists(self, monkeypatch, capsys):
        """shipped transition blocked when feature branch has unmerged commits."""

        class FakeResult:
            returncode = 0
            stdout = ""
            stderr = ""

        def _fake_run_list(cmd, **kw):
            # PR check: no open PRs
            if "pr" in cmd and "list" in cmd:
                r = FakeResult()
                r.stdout = "[]"
                return r
            # git branch -a --list: return a matching branch
            if "branch" in cmd and "--list" in cmd:
                r = FakeResult()
                r.stdout = "  squidsquad/skill/42\n"
                return r
            # git rev-list --count: 3 unmerged commits
            if "rev-list" in cmd and "--count" in cmd:
                r = FakeResult()
                r.stdout = "3"
                return r
            return FakeResult()

        monkeypatch.setattr(tracker, "_run_list", _fake_run_list)

        with pytest.raises(SystemExit) as excinfo:
            tracker.transition(42, "pending-ship", "shipped", role="dm-lead")
        assert excinfo.value.code == 1
        err = capsys.readouterr().err
        assert "BLOCKED" in err
        assert "squidsquad/skill/42" in err
        assert "3 commit(s)" in err

    def test_allows_when_branch_fully_merged(self, monkeypatch):
        """shipped transition proceeds when feature branch is fully merged."""

        class FakeResult:
            returncode = 0
            stdout = ""
            stderr = ""

        def _fake_run_list(cmd, **kw):
            if "pr" in cmd and "list" in cmd:
                r = FakeResult()
                r.stdout = "[]"
                return r
            if "branch" in cmd and "--list" in cmd:
                r = FakeResult()
                r.stdout = "  squidsquad/skill/42\n"
                return r
            # 0 unmerged commits — fully merged
            if "rev-list" in cmd and "--count" in cmd:
                r = FakeResult()
                r.stdout = "0"
                return r
            return FakeResult()

        monkeypatch.setattr(tracker, "_run_list", _fake_run_list)
        # Should not raise — branch is merged
        tracker.transition(42, "pending-ship", "shipped", role="dm-lead")

    def test_allows_when_no_feature_branch(self, monkeypatch):
        """shipped transition proceeds when no feature branch exists."""

        class FakeResult:
            returncode = 0
            stdout = ""
            stderr = ""

        def _fake_run_list(cmd, **kw):
            if "pr" in cmd and "list" in cmd:
                r = FakeResult()
                r.stdout = "[]"
                return r
            # No branches found
            if "branch" in cmd and "--list" in cmd:
                r = FakeResult()
                r.stdout = ""
                return r
            return FakeResult()

        monkeypatch.setattr(tracker, "_run_list", _fake_run_list)
        tracker.transition(42, "pending-ship", "shipped", role="dm-lead")

    def test_force_does_not_bypass_branch_check(self, monkeypatch, capsys):
        """--force does NOT bypass the branch merge check."""

        class FakeResult:
            returncode = 0
            stdout = ""
            stderr = ""

        def _fake_run_list(cmd, **kw):
            if "pr" in cmd and "list" in cmd:
                r = FakeResult()
                r.stdout = "[]"
                return r
            if "branch" in cmd and "--list" in cmd:
                r = FakeResult()
                r.stdout = "  squidsquad/skill/42\n"
                return r
            if "rev-list" in cmd and "--count" in cmd:
                r = FakeResult()
                r.stdout = "2"
                return r
            return FakeResult()

        monkeypatch.setattr(tracker, "_run_list", _fake_run_list)

        with pytest.raises(SystemExit) as excinfo:
            tracker.transition(42, "pending-ship", "shipped", role="dm-lead", force=True)
        assert excinfo.value.code == 1
        err = capsys.readouterr().err
        assert "BLOCKED" in err

    def test_ignores_branch_with_wrong_issue_number(self, monkeypatch):
        """Branch for a different issue number does not block shipping."""

        class FakeResult:
            returncode = 0
            stdout = ""
            stderr = ""

        def _fake_run_list(cmd, **kw):
            if "pr" in cmd and "list" in cmd:
                r = FakeResult()
                r.stdout = "[]"
                return r
            if "branch" in cmd and "--list" in cmd:
                r = FakeResult()
                # Branch for issue 421, not 42
                r.stdout = "  squidsquad/skill/421\n"
                return r
            return FakeResult()

        monkeypatch.setattr(tracker, "_run_list", _fake_run_list)
        # Should not raise — branch is for a different issue
        tracker.transition(42, "pending-ship", "shipped", role="dm-lead")


class TestDraftPRConversion:
    """Auto-convert draft PRs to ready on pending-test and pending-ship transitions (#1696, #4084)."""

    def test_converts_draft_to_ready(self, monkeypatch):
        """pending-ship transition calls gh pr ready on matching draft PR."""
        gh_calls = []

        class FakeResult:
            returncode = 0
            stdout = ""
            stderr = ""

        def _fake_run_list(cmd, **kw):
            gh_calls.append(cmd)
            if "pr" in cmd and "list" in cmd:
                r = FakeResult()
                r.stdout = json.dumps([
                    {"number": 88, "headRefName": "squidsquad/skill/42",
                     "isDraft": True, "url": "http://pr/88"}
                ])
                return r
            return FakeResult()

        monkeypatch.setattr(tracker, "_run_list", _fake_run_list)
        monkeypatch.setattr(tracker, "_get_issue_role_labels", lambda n: {"skill"})
        monkeypatch.setattr(tracker, "_check_unread_feedback", lambda n, r: [])

        tracker.transition(42, "pending-test", "pending-ship", role="qa-lead")

        # Should have called gh pr ready
        ready_calls = [c for c in gh_calls if "ready" in c]
        assert len(ready_calls) == 1
        assert "88" in str(ready_calls[0])

    def test_skips_non_draft_pr(self, monkeypatch):
        """pending-ship does not call gh pr ready if PR is not a draft."""
        gh_calls = []

        class FakeResult:
            returncode = 0
            stdout = ""
            stderr = ""

        def _fake_run_list(cmd, **kw):
            gh_calls.append(cmd)
            if "pr" in cmd and "list" in cmd:
                r = FakeResult()
                r.stdout = json.dumps([
                    {"number": 88, "headRefName": "squidsquad/skill/42",
                     "isDraft": False}
                ])
                return r
            return FakeResult()

        monkeypatch.setattr(tracker, "_run_list", _fake_run_list)
        monkeypatch.setattr(tracker, "_get_issue_role_labels", lambda n: {"skill"})
        monkeypatch.setattr(tracker, "_check_unread_feedback", lambda n, r: [])

        tracker.transition(42, "pending-test", "pending-ship", role="qa-lead")

        ready_calls = [c for c in gh_calls if "ready" in c]
        assert len(ready_calls) == 0

    def test_pending_test_converts_draft_to_ready(self, monkeypatch):
        """#4084: pending-test transition also converts draft PR to ready."""
        gh_calls = []

        class FakeResult:
            returncode = 0
            stdout = ""
            stderr = ""

        def _fake_run_list(cmd, **kw):
            gh_calls.append(cmd)
            if "pr" in cmd and "list" in cmd:
                r = FakeResult()
                r.stdout = json.dumps([
                    {"number": 99, "headRefName": "squidsquad/skill/55",
                     "isDraft": True, "url": "http://pr/99"}
                ])
                return r
            return FakeResult()

        monkeypatch.setattr(tracker, "_run_list", _fake_run_list)
        monkeypatch.setattr(tracker, "_get_issue_role_labels", lambda n: {"skill"})
        monkeypatch.setattr(tracker, "_check_unread_feedback", lambda n, r: [])

        tracker.transition(55, "in-progress", "pending-test", role="skill-lead")

        ready_calls = [c for c in gh_calls if "ready" in c and "--undo" not in c]
        assert len(ready_calls) == 1
        assert "99" in str(ready_calls[0])

    def test_no_pr_is_silent_noop(self, monkeypatch):
        """pending-ship with no matching PR is a silent no-op."""
        class FakeResult:
            returncode = 0
            stdout = ""
            stderr = ""

        def _fake_run_list(cmd, **kw):
            if "pr" in cmd and "list" in cmd:
                r = FakeResult()
                r.stdout = "[]"
                return r
            return FakeResult()

        monkeypatch.setattr(tracker, "_run_list", _fake_run_list)
        monkeypatch.setattr(tracker, "_get_issue_role_labels", lambda n: {"skill"})
        monkeypatch.setattr(tracker, "_check_unread_feedback", lambda n, r: [])

        # Should not raise
        tracker.transition(42, "pending-test", "pending-ship", role="qa-lead")


class TestForgejoAdapterDraftConversion:
    """Regression #4991 GAP-3: Forgejo adapter must call pr_ready(), not pass."""

    def test_forgejo_adapter_calls_pr_ready(self, monkeypatch):
        """When forge adapter is available, _convert_draft_pr_to_ready uses it."""
        from unittest.mock import MagicMock
        mock_adapter = MagicMock()
        mock_adapter.list_prs.return_value = [
            {"number": 77, "headRefName": "squidsquad/skill/42", "isDraft": True}
        ]

        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: mock_adapter)

        tracker._convert_draft_pr_to_ready(42)

        mock_adapter.pr_ready.assert_called_once_with(77)

    def test_forgejo_adapter_skips_non_draft(self, monkeypatch):
        """Forgejo adapter skips non-draft PRs."""
        from unittest.mock import MagicMock
        mock_adapter = MagicMock()
        mock_adapter.list_prs.return_value = [
            {"number": 77, "headRefName": "squidsquad/skill/42", "isDraft": False}
        ]

        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: mock_adapter)

        tracker._convert_draft_pr_to_ready(42)

        mock_adapter.pr_ready.assert_not_called()

    def test_forgejo_adapter_no_matching_pr(self, monkeypatch):
        """Forgejo adapter handles no matching PR gracefully."""
        from unittest.mock import MagicMock
        mock_adapter = MagicMock()
        mock_adapter.list_prs.return_value = [
            {"number": 77, "headRefName": "squidsquad/pm/99", "isDraft": True}
        ]

        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: mock_adapter)

        tracker._convert_draft_pr_to_ready(42)

        mock_adapter.pr_ready.assert_not_called()


# ---------------------------------------------------------------------------
# list_issues — label construction and status filtering (#471)
# ---------------------------------------------------------------------------


class TestListIssuesLabelConstruction:
    """Verify list_issues builds correct label queries, especially --status."""

    def _capture_labels(self, monkeypatch):
        """Mock _run_list to capture the labels argument passed to gh."""
        captured = {}

        class FakeResult:
            returncode = 0
            stdout = "[]"
            stderr = ""

        def fake_run(cmd, check=True):
            # Find --label arg
            for i, a in enumerate(cmd):
                if a == "--label" and i + 1 < len(cmd):
                    captured["labels"] = cmd[i + 1]
            return FakeResult()

        monkeypatch.setattr(tracker, "_run_list", fake_run)
        return captured

    def test_no_status_filter(self, monkeypatch):
        captured = self._capture_labels(monkeypatch)
        tracker.list_issues("skill", "issue")
        assert "status:" not in captured["labels"]
        assert "type:issue" in captured["labels"]
        assert "role:skill" in captured["labels"]

    def test_status_open_filter(self, monkeypatch):
        captured = self._capture_labels(monkeypatch)
        tracker.list_issues("skill", "issue", status="open")
        assert "status:open" in captured["labels"]
        assert "type:issue" in captured["labels"]

    def test_status_pending_filter(self, monkeypatch):
        captured = self._capture_labels(monkeypatch)
        tracker.list_issues("skill", "issue", status="pending")
        assert "status:pending" in captured["labels"]

    def test_task_type(self, monkeypatch):
        captured = self._capture_labels(monkeypatch)
        tracker.list_issues("skill", "task", status="approved")
        assert "type:task" in captured["labels"]
        assert "status:approved" in captured["labels"]

    def test_backward_compat_bug_alias(self, monkeypatch):
        """'bug' type maps to type:issue via backward-compat alias."""
        captured = self._capture_labels(monkeypatch)
        tracker.list_issues("skill", "bug")
        assert "type:issue" in captured["labels"]

    def test_backward_compat_feature_alias(self, monkeypatch):
        """'feature' type maps to type:task via backward-compat alias."""
        captured = self._capture_labels(monkeypatch)
        tracker.list_issues("skill", "feature", status="approved")
        assert "type:task" in captured["labels"]
