"""Unit tests for tracker.py role-based transition authority (#320).

Verifies that `transition()` enforces role authority in addition to
state-machine legality, preventing cross-role transitions (e.g. skill-lead
shipping an issue that only DM should ship).
"""

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
        ("designer", "designer"),
        ("designer-lead", "designer"),
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

    # ---- QA verification flow ----
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

    def test_skill_cannot_approve_pending_test(self, stub_role_labels):
        ok, reason = tracker._check_authority(
            1, "status:pending-test", "status:pending-ship", "skill-lead"
        )
        assert not ok
        assert "qa" in reason

    def test_dm_cannot_approve_pending_test(self, stub_role_labels):
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
