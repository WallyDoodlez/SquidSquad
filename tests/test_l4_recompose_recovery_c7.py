"""Tests for references/scripts/l4_recompose_recovery.py (#10656, PRD-C C7).

AC5 mandates at least three paths:
  (a) recompose succeeds → no revert, log success
  (b) recompose fails → revert lands + alert
  (c) recompose times out → same treatment as failure

Plus defensive coverage: revert-itself-fails, push-of-revert-fails,
check_recompose_fn raises, skip path when no check_recompose_fn is
wired, and the iteration-log formatter.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import l4_recompose_recovery as rr  # noqa: E402


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


def _make_check(*responses):
    """Build a check_recompose_fn that returns canned ``responses`` in order.

    Each ``responses`` entry is a ``(status, diagnostic)`` tuple. After
    exhausting responses, returns the last one indefinitely (so a
    test setting up "pending three times then success" can give exactly
    those four).
    """
    state = {"i": 0}

    def check(commit_sha):
        i = min(state["i"], len(responses) - 1)
        state["i"] += 1
        return responses[i]

    return check


def _make_runner(*, fail_command_prefix=None, head_sha="revertsha1234567890"):
    """Build a stub git runner mirroring C6's test fixture shape."""
    calls = []

    def run(argv, *, cwd=None, capture_output=True, text=True, **kwargs):
        calls.append({"argv": list(argv), "cwd": cwd})
        if argv[:2] == ["git", "rev-parse"]:
            return SimpleNamespace(returncode=0, stdout=head_sha + "\n", stderr="")
        if fail_command_prefix is not None:
            if tuple(argv[:len(fail_command_prefix)]) == tuple(fail_command_prefix):
                return SimpleNamespace(returncode=1, stdout="", stderr="simulated failure")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    return run, calls


def _instant_sleep(_):
    pass


_FAKE_CLOCK_TICK = {"t": 0.0}


def _stepped_clock():
    """Returns a clock function that advances by 1.0s each call."""
    state = {"t": 0.0}

    def clock():
        v = state["t"]
        state["t"] += 1.0
        return v

    return clock


# ---------------------------------------------------------------------------
# wait_for_recompose — pending → success
# ---------------------------------------------------------------------------


class TestWaitForRecomposeSuccess:
    def test_immediate_success_no_polling(self):
        check = _make_check(("success", "compose returned 0"))
        outcome = rr.wait_for_recompose(
            commit_sha="abc123",
            check_recompose_fn=check,
            sleep_fn=_instant_sleep,
            clock_fn=_stepped_clock(),
        )
        assert outcome.status == "success"
        assert outcome.succeeded is True
        assert outcome.diagnostic == "compose returned 0"

    def test_pending_then_success(self):
        check = _make_check(
            ("pending", ""), ("pending", ""), ("success", "deployed"),
        )
        outcome = rr.wait_for_recompose(
            commit_sha="abc",
            check_recompose_fn=check,
            sleep_fn=_instant_sleep,
            clock_fn=_stepped_clock(),
            timeout_seconds=60,
            poll_interval_seconds=2,
        )
        assert outcome.status == "success"


# ---------------------------------------------------------------------------
# wait_for_recompose — failure short-circuit
# ---------------------------------------------------------------------------


class TestWaitForRecomposeFailure:
    def test_failure_short_circuits_polling(self):
        """A failure status should NOT keep polling — once the harness
        reports failure, we know the answer.
        """
        check = _make_check(("failure", "compose exited with code 5"))
        outcome = rr.wait_for_recompose(
            commit_sha="abc",
            check_recompose_fn=check,
            sleep_fn=_instant_sleep,
            clock_fn=_stepped_clock(),
        )
        assert outcome.status == "failure"
        assert "exited with code 5" in outcome.diagnostic

    def test_check_fn_raise_becomes_failure_outcome(self):
        """A polling-fn exception is captured as a `"failure"` outcome
        with the exception text — the orchestrator never sees the raise.
        """
        def boom(commit_sha):
            raise RuntimeError("harness unreachable")

        outcome = rr.wait_for_recompose(
            commit_sha="abc",
            check_recompose_fn=boom,
            sleep_fn=_instant_sleep,
            clock_fn=_stepped_clock(),
        )
        assert outcome.status == "failure"
        assert "harness unreachable" in outcome.diagnostic


# ---------------------------------------------------------------------------
# wait_for_recompose — timeout
# ---------------------------------------------------------------------------


class TestWaitForRecomposeTimeout:
    def test_pending_until_timeout_returns_timeout(self):
        """Permanent pending → timeout outcome with the deadline named."""
        check = _make_check(("pending", "still working"))
        clock = _stepped_clock()
        outcome = rr.wait_for_recompose(
            commit_sha="abc",
            check_recompose_fn=check,
            sleep_fn=_instant_sleep,
            clock_fn=clock,
            timeout_seconds=3,
            poll_interval_seconds=1,
        )
        assert outcome.status == "timeout"
        assert "3s" in outcome.diagnostic
        # Last polled diagnostic is preserved
        assert "still working" in outcome.diagnostic


# ---------------------------------------------------------------------------
# wait_for_recompose — defaults when no check_fn wired
# ---------------------------------------------------------------------------


class TestWaitForRecomposeDefaults:
    def test_no_check_fn_returns_failure_outcome(self):
        """Calling wait_for_recompose without a check_fn returns a failure
        outcome with a diagnostic naming the unwired PRD-E contract.
        The orchestrator wraps this same case with a `skip` path; this
        test checks the lower-level helper's behavior directly.
        """
        outcome = rr.wait_for_recompose(commit_sha="abc")
        assert outcome.status == "failure"
        assert "PRD-E" in outcome.diagnostic


# ---------------------------------------------------------------------------
# revert_l4_commit — happy path
# ---------------------------------------------------------------------------


class TestRevertL4CommitHappy:
    def test_revert_then_push_calls_git_in_order(self, tmp_path):
        run, calls = _make_runner()
        outcome = rr.revert_l4_commit(
            commit_sha="deadbeefcafe1234",
            reason="compose dry-run R5 orphan step",
            runner=run, target_root=tmp_path,
        )
        assert outcome.ok is True
        assert outcome.pushed is True
        argvs = [c["argv"] for c in calls]
        # First a git revert, then a push
        revert_idx = next(i for i, a in enumerate(argvs) if a[:2] == ["git", "revert"])
        push_idx = next(i for i, a in enumerate(argvs) if a[:2] == ["git", "push"])
        assert revert_idx < push_idx

    def test_push_uses_plain_push_no_force(self, tmp_path):
        run, calls = _make_runner()
        rr.revert_l4_commit(
            commit_sha="abc", reason="x", runner=run, target_root=tmp_path,
        )
        all_args = [a for c in calls for a in c["argv"]]
        assert "--force" not in all_args
        assert "-f" not in all_args
        assert "--rebase" not in all_args

    def test_revert_uses_no_edit_to_avoid_interactive_editor(self, tmp_path):
        """Defensive: --no-edit prevents git from launching an editor on
        the agent's terminal (which would hang the subprocess).
        """
        run, calls = _make_runner()
        rr.revert_l4_commit(
            commit_sha="abc", reason="x", runner=run, target_root=tmp_path,
        )
        revert_argv = next(c["argv"] for c in calls if c["argv"][:2] == ["git", "revert"])
        assert "--no-edit" in revert_argv


# ---------------------------------------------------------------------------
# revert_l4_commit — failure modes
# ---------------------------------------------------------------------------


class TestRevertL4CommitFailures:
    def test_revert_fails_returns_revert_stage(self, tmp_path):
        run, _ = _make_runner(fail_command_prefix=("git", "revert"))
        outcome = rr.revert_l4_commit(
            commit_sha="abc", reason="x", runner=run, target_root=tmp_path,
        )
        assert outcome.ok is False
        assert outcome.failure_stage == "revert"
        assert outcome.pushed is False
        assert "simulated failure" in outcome.failure_detail

    def test_push_fails_returns_push_stage(self, tmp_path):
        run, _ = _make_runner(fail_command_prefix=("git", "push"))
        outcome = rr.revert_l4_commit(
            commit_sha="abc", reason="x", runner=run, target_root=tmp_path,
        )
        assert outcome.ok is False
        assert outcome.failure_stage == "push"
        # revert_sha was still captured (the revert commit landed locally)
        assert outcome.revert_sha is not None


# ---------------------------------------------------------------------------
# Orchestrator — AC5(a) recompose succeeds → no revert
# ---------------------------------------------------------------------------


class TestOrchestratorSuccessPath:
    def test_recompose_success_returns_success_no_action(self, tmp_path):
        check = _make_check(("success", "compose ok"))
        run, calls = _make_runner()
        plan = rr.recover_on_recompose_failure(
            commit_sha="commitsha1234",
            check_recompose_fn=check,
            runner=run,
            sleep_fn=_instant_sleep,
            clock_fn=_stepped_clock(),
            target_root=tmp_path,
        )
        assert plan.path_chosen == "success-no-action"
        # No git operations dispatched
        assert calls == []
        assert plan.revert is None
        assert "succeeded" in plan.alert_message.lower()


# ---------------------------------------------------------------------------
# Orchestrator — AC5(b) recompose fails → revert lands + alert
# ---------------------------------------------------------------------------


class TestOrchestratorFailurePath:
    def test_recompose_failure_triggers_revert_and_alert(self, tmp_path):
        check = _make_check(("failure", "R5 orphan step id"))
        run, calls = _make_runner()
        plan = rr.recover_on_recompose_failure(
            commit_sha="commitsha1234",
            check_recompose_fn=check,
            runner=run,
            sleep_fn=_instant_sleep,
            clock_fn=_stepped_clock(),
            target_root=tmp_path,
        )
        assert plan.path_chosen == "revert-attempted"
        assert plan.revert is not None and plan.revert.ok
        # Alert names both the original commit + the recompose reason
        assert "commitsh" in plan.alert_message
        assert "R5 orphan step id" in plan.alert_message
        # Git operations actually fired
        argvs = [c["argv"] for c in calls]
        assert any(a[:2] == ["git", "revert"] for a in argvs)
        assert any(a[:2] == ["git", "push"] for a in argvs)


# ---------------------------------------------------------------------------
# Orchestrator — AC5(c) recompose times out → same as failure
# ---------------------------------------------------------------------------


class TestOrchestratorTimeoutPath:
    def test_recompose_timeout_treated_as_failure(self, tmp_path):
        check = _make_check(("pending", "still working"))
        run, calls = _make_runner()
        plan = rr.recover_on_recompose_failure(
            commit_sha="commitsha1234",
            check_recompose_fn=check,
            runner=run,
            sleep_fn=_instant_sleep,
            clock_fn=_stepped_clock(),
            target_root=tmp_path,
            timeout_seconds=3,
            poll_interval_seconds=1,
        )
        # Timeout → revert (same as failure per AC3)
        assert plan.path_chosen == "revert-attempted"
        assert plan.recompose.status == "timeout"


# ---------------------------------------------------------------------------
# Orchestrator — revert itself fails (critical path)
# ---------------------------------------------------------------------------


class TestOrchestratorRevertFailedPath:
    def test_revert_failure_returns_critical_path(self, tmp_path):
        check = _make_check(("failure", "compose exit 5"))
        run, _ = _make_runner(fail_command_prefix=("git", "revert"))
        plan = rr.recover_on_recompose_failure(
            commit_sha="abc",
            check_recompose_fn=check,
            runner=run,
            sleep_fn=_instant_sleep,
            clock_fn=_stepped_clock(),
            target_root=tmp_path,
        )
        assert plan.path_chosen == "revert-failed"
        assert "CRITICAL" in plan.alert_message
        # Both the recompose AND revert diagnostics are in the alert
        assert "compose exit 5" in plan.alert_message
        assert "simulated failure" in plan.alert_message


# ---------------------------------------------------------------------------
# Orchestrator — skip path when no check_recompose_fn wired
# ---------------------------------------------------------------------------


class TestOrchestratorSkipPath:
    def test_no_check_fn_returns_skip(self):
        """Until PRD-E lands, the harness-watch contract is unwired.
        The orchestrator returns a skip path so the caller continues
        normally (no revert, no alert).
        """
        plan = rr.recover_on_recompose_failure(
            commit_sha="abc",
            check_recompose_fn=None,
        )
        assert plan.path_chosen == "skip"
        assert plan.revert is None
        assert "PRD-E" in plan.alert_message


# ---------------------------------------------------------------------------
# format_iteration_log_entry (AC5 fields)
# ---------------------------------------------------------------------------


class TestFormatIterationLogEntry:
    def test_success_entry_has_original_sha_and_status(self, tmp_path):
        check = _make_check(("success", "compose ok"))
        plan = rr.recover_on_recompose_failure(
            commit_sha="abc12345678",
            check_recompose_fn=check,
            sleep_fn=_instant_sleep,
            clock_fn=_stepped_clock(),
            target_root=tmp_path,
        )
        log = rr.format_iteration_log_entry(plan)
        assert "abc12345" in log
        assert "success" in log

    def test_revert_entry_has_all_three_required_fields(self, tmp_path):
        """AC5 mandates: (a) original L4 write commit SHA, (b) recompose
        failure reason, (c) revert commit SHA.
        """
        check = _make_check(("failure", "R5 orphan step id"))
        run, _ = _make_runner(head_sha="revertabc789")
        plan = rr.recover_on_recompose_failure(
            commit_sha="origsha98765",
            check_recompose_fn=check,
            runner=run,
            sleep_fn=_instant_sleep,
            clock_fn=_stepped_clock(),
            target_root=tmp_path,
        )
        log = rr.format_iteration_log_entry(plan)
        # (a) original commit SHA
        assert "origsha9" in log
        # (b) failure reason
        assert "R5 orphan step id" in log
        # (c) revert commit SHA
        assert "revertab" in log

    def test_skip_entry_records_skip_marker(self):
        plan = rr.recover_on_recompose_failure(
            commit_sha="abcdef", check_recompose_fn=None,
        )
        log = rr.format_iteration_log_entry(plan)
        assert "skipped" in log.lower()
        assert "abcdef" in log


# ---------------------------------------------------------------------------
# Dataclass surface
# ---------------------------------------------------------------------------


class TestRecoveryPlanShape:
    def test_path_choice_literal_round_trip(self):
        for path in ("success-no-action", "revert-attempted",
                     "revert-failed", "skip"):
            plan = rr.RecoveryPlan(path_chosen=path)
            assert plan.path_chosen == path

    def test_recompose_outcome_succeeded_property(self):
        assert rr.RecomposeOutcome(status="success").succeeded is True
        assert rr.RecomposeOutcome(status="failure").succeeded is False
        assert rr.RecomposeOutcome(status="timeout").succeeded is False

    def test_revert_outcome_ok_property(self):
        assert rr.RevertOutcome(pushed=True).ok is True
        assert rr.RevertOutcome(failure_stage="revert").ok is False
        assert rr.RevertOutcome(failure_stage="push").ok is False
