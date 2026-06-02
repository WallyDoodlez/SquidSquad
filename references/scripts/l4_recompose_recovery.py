"""C7: Recompose-failure recovery — git-revert + alert after C6 lands (#10656, PRD-C C7).

§7.4 step 3 race: after C6's atomic write + commit + push lands, the
harness's file-watch (per PRD-E) triggers ``compose.py deploy-all``.
If that recompose fails, the agent must revert the L4 commit so the
operator's on-disk CLAUDE.md state stays consistent — otherwise the
next agent boot reads stale L4 prose and behaves on a recipe that
the compose pipeline rejected.

This module is the recovery orchestrator. It:

1. Polls (or awaits an event) for the harness's recompose result
   within a bounded window via ``wait_for_recompose``.
2. On ``success``: returns a no-op plan; caller logs success and
   moves on.
3. On ``failure`` / ``timeout``: dispatches ``revert_l4_commit`` to
   run ``git revert <sha> --no-edit`` and push the revert commit.
   Per AC4 the revert is a NEW commit on top of HEAD (additive
   history) — never a force-push or rebase.

The orchestrator NEVER raises — failure modes carry in
``RecoveryPlan.path_chosen`` so callers branch on data:
``success-no-action`` / ``revert-attempted`` / ``revert-failed`` /
``skip`` (when the harness-watch contract is disabled).

The PRD-E harness file-watch trigger contract is wired through the
``check_recompose_fn`` injection seam — tests pass a stub that
returns canned ``pending`` / ``success`` / ``failure`` outcomes;
real callers will pass a function that queries the harness HTTP
API once the PRD-E lane lands.

Iteration-log fields per AC5 are formatted by
``format_iteration_log_entry`` so callers append a consistent
block to ``.squidsquad/skill/iterations/iter-<N>.md``.
"""

import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


PathChoice = Literal[
    "success-no-action",
    "revert-attempted",
    "revert-failed",
    "skip",
]


@dataclass
class RecomposeOutcome:
    """Result of one ``wait_for_recompose`` call.

    ``status`` is one of ``"not-checked"`` (default sentinel) /
    ``"success"`` / ``"failure"`` / ``"timeout"`` /
    ``"skip"``. ``diagnostic`` carries the failure reason on
    non-success outcomes so the caller can surface it to the human
    and log it. ``duration_seconds`` is the wall time the wait
    actually took.

    Default sentinel ``"not-checked"`` lets ``RecoveryPlan`` carry a
    non-``None`` instance on the ``skip`` path, so callers accessing
    ``plan.recompose.diagnostic`` don't ``AttributeError`` when
    recovery wasn't wired (C7 review concern #3).

    ``"skip"`` (added per #10753 W2) is returned by the standalone
    ``wait_for_recompose`` when ``check_recompose_fn=None`` — the
    PRD-E harness-watch contract is not wired in this install. Prior
    behavior returned ``"failure"`` here, which the orchestrator
    correctly mapped to a recovery-skip path but direct callers
    interpreted as a real failure (would trigger spurious reverts).
    The orchestrator's ``RecoveryPlan.path_chosen="skip"`` already
    used this semantic; ``RecomposeOutcome.status="skip"`` aligns the
    standalone path with it.
    """

    status: str = "not-checked"
    diagnostic: str = ""
    duration_seconds: float = 0.0

    @property
    def succeeded(self):
        return self.status == "success"

    @property
    def skipped(self):
        """True iff the check was deliberately not performed (e.g.
        ``check_recompose_fn=None``). Distinct from ``failure`` —
        callers should NOT treat a skipped outcome as a reason to
        revert."""
        return self.status == "skip"


@dataclass
class RevertOutcome:
    """Result of one ``revert_l4_commit`` call.

    ``revert_sha`` is the SHA of the new revert commit when revert+push
    succeeded; ``None`` otherwise. ``pushed`` is True iff the revert
    push to remote succeeded. ``failure_stage`` is ``""`` on full
    success, otherwise one of ``"revert"`` / ``"push"`` — callers
    render stage-specific human guidance.

    ``amend_failed_detail`` is non-empty when the commit-amend step
    that injects the recompose failure reason into the revert message
    failed (non-fatal to the revert+push flow, but the audit-trail
    message on the revert commit will be git's default rather than
    the agent's enriched one). Surfacing this lets the alert message
    note the degraded audit trail.
    """

    revert_sha: str | None = None
    pushed: bool = False
    failure_stage: str = ""
    failure_detail: str = ""
    amend_failed_detail: str = ""

    @property
    def ok(self):
        return self.failure_stage == ""


@dataclass
class RecoveryPlan:
    """Outcome of one ``recover_on_recompose_failure`` invocation.

    Callers branch on ``path_chosen`` to decide what to log and what to
    surface to the human:

    - ``"success-no-action"`` — recompose succeeded; log success and
      continue.
    - ``"revert-attempted"`` — recompose failed/timed out, revert
      landed cleanly; log original SHA + recompose reason + revert
      SHA per AC5.
    - ``"revert-failed"`` — recompose failed AND the revert itself
      failed; the L4 file is in a broken-state and the operator
      MUST intervene. Highest-priority alert.
    - ``"skip"`` — caller disabled recovery (PRD-E harness-watch
      contract not yet wired in this install); informational return,
      no action taken.

    Sentinel-default subfields (``recompose=RecomposeOutcome()``,
    ``revert=RevertOutcome()``) mean callers can safely access
    ``plan.recompose.diagnostic`` / ``plan.revert.failure_stage``
    without checking ``path_chosen`` first — wrong-path access just
    returns empty strings, not AttributeError.
    """

    path_chosen: PathChoice
    original_commit_sha: str = ""
    recompose: RecomposeOutcome = field(default_factory=RecomposeOutcome)
    revert: RevertOutcome = field(default_factory=RevertOutcome)
    alert_message: str = ""


# ---------------------------------------------------------------------------
# wait_for_recompose
# ---------------------------------------------------------------------------


def wait_for_recompose(
    *,
    commit_sha,
    timeout_seconds=60,
    poll_interval_seconds=2,
    check_recompose_fn=None,
    sleep_fn=None,
    clock_fn=None,
):
    """Poll the harness's recompose status for ``commit_sha`` within a window.

    ``check_recompose_fn(commit_sha)`` is the injection seam — tests
    pass a stub returning ``(status, diagnostic)`` tuples where
    ``status`` is one of ``"pending"`` / ``"success"`` / ``"failure"``.
    Real callers will wire this to a function that queries the
    harness HTTP API for the recompose lane that started after C6's
    commit was observed by the file-watch.

    The poll fires every ``poll_interval_seconds`` and gives up at
    ``timeout_seconds``. A status of ``"failure"`` short-circuits the
    poll loop — no point waiting longer once the harness has reported
    a definitive failure. A status of ``"success"`` likewise short-
    circuits.

    Returns :class:`RecomposeOutcome`. NEVER raises — a polling-fn
    exception is captured as a ``"failure"`` outcome with the
    exception text in the diagnostic.
    """
    if check_recompose_fn is None:
        # #10753 W2: standardize on `"skip"` so direct standalone
        # callers don't interpret a missing-config no-op as a real
        # failure (which would trigger a spurious revert). The
        # orchestrator's `recover_from_l4_write` already returns
        # `RecoveryPlan.path_chosen="skip"` for the same condition;
        # `RecomposeOutcome.status="skip"` here makes both code paths
        # agree.
        return RecomposeOutcome(
            status="skip",
            diagnostic=(
                "wait_for_recompose called without a check_recompose_fn — "
                "the PRD-E harness-watch contract is not yet wired in this "
                "install. Skip the recovery flow or wire the seam first."
            ),
        )
    if sleep_fn is None:
        sleep_fn = time.sleep
    if clock_fn is None:
        clock_fn = time.monotonic

    start = clock_fn()
    deadline = start + timeout_seconds
    last_diagnostic = ""

    while True:
        try:
            status, diagnostic = check_recompose_fn(commit_sha)
        except Exception as e:  # noqa: BLE001
            return RecomposeOutcome(
                status="failure",
                diagnostic=f"check_recompose_fn raised: {e}",
                duration_seconds=clock_fn() - start,
            )

        last_diagnostic = diagnostic or last_diagnostic

        if status == "success":
            return RecomposeOutcome(
                status="success",
                diagnostic=diagnostic or "",
                duration_seconds=clock_fn() - start,
            )
        if status == "failure":
            return RecomposeOutcome(
                status="failure",
                diagnostic=diagnostic or "harness reported recompose failure",
                duration_seconds=clock_fn() - start,
            )
        # status == "pending" — keep waiting
        now = clock_fn()
        if now >= deadline:
            return RecomposeOutcome(
                status="timeout",
                diagnostic=(
                    f"recompose did not complete within {timeout_seconds}s. "
                    f"Last polled diagnostic: {last_diagnostic or '(none)'}"
                ),
                duration_seconds=now - start,
            )
        sleep_fn(poll_interval_seconds)


# ---------------------------------------------------------------------------
# revert_l4_commit
# ---------------------------------------------------------------------------


def revert_l4_commit(*, commit_sha, reason, runner=None, target_root=None):
    """Revert ``commit_sha`` via ``git revert --no-edit`` then push.

    Per AC4 the revert is a NEW commit on top of HEAD (additive
    history) — NEVER a force push or rebase. The revert commit's
    message is augmented with the recompose failure reason so
    ``git log`` reads as a complete audit trail without operators
    needing to dig back into the conversation.

    No ``-m`` flag: C6's L4 commits are always linear (one parent),
    never merges (see ``l4_write_commit.py``), so the ``-m
    <parent-number>`` flag would never apply and any attempted
    "retry without -m on non-merge error" pattern is unreliable
    because git's error string varies across versions. Drop the
    retry; pass no ``-m``. (C7 review BLOCKER #1.)

    NEVER raises. Returns :class:`RevertOutcome` with
    ``failure_stage`` in ``""`` / ``"revert"`` / ``"push"``. An
    amend failure is captured into ``amend_failed_detail`` but does
    not block the push — the revert still lands with git's default
    message.
    """
    if runner is None:
        runner = subprocess.run
    if target_root is None:
        target_root = str(Path(__file__).resolve().parent.parent.parent)
    else:
        target_root = str(target_root)

    # Phase 1: git revert --no-edit <sha>
    revert_msg = (
        f"Revert L4 write {commit_sha[:12]} after recompose failure\n"
        f"\nRecompose failure reason: {reason}\n"
    )
    revert_result = runner(
        ["git", "revert", "--no-edit", commit_sha],
        cwd=target_root, capture_output=True, text=True,
    )
    if revert_result.returncode != 0:
        return RevertOutcome(
            failure_stage="revert",
            failure_detail=(
                f"git revert failed for {commit_sha[:8]}: "
                f"{revert_result.stderr.strip() or revert_result.stdout.strip()}"
            ),
        )

    # Amend the revert's commit message to include the failure reason.
    # git revert --no-edit uses the default "Revert \"<subject>\"" message;
    # we replace it with one that names the failure reason for the audit
    # trail per AC5. Amend failure is captured but non-fatal — the revert
    # still lands, just with git's default message.
    amend_result = runner(
        ["git", "commit", "--amend", "-m", revert_msg],
        cwd=target_root, capture_output=True, text=True,
    )
    amend_failed_detail = ""
    if amend_result.returncode != 0:
        amend_failed_detail = (
            f"amend of revert message failed (non-fatal — revert still "
            f"landed with git's default message): "
            f"{amend_result.stderr.strip() or amend_result.stdout.strip()}"
        )

    # Capture the revert SHA after any amendment. On amend failure HEAD
    # is unchanged so rev-parse returns the original revert SHA — still
    # the correct SHA for the audit trail.
    sha_result = runner(
        ["git", "rev-parse", "HEAD"],
        cwd=target_root, capture_output=True, text=True,
    )
    revert_sha = sha_result.stdout.strip() if sha_result.returncode == 0 else None

    # Phase 2: push (plain, no --rebase, no --force per operator rule)
    push_result = runner(
        ["git", "push"],
        cwd=target_root, capture_output=True, text=True,
    )
    if push_result.returncode != 0:
        return RevertOutcome(
            revert_sha=revert_sha,
            pushed=False,
            failure_stage="push",
            failure_detail=(
                f"git push of revert {revert_sha[:8] if revert_sha else '?'} "
                f"failed: {push_result.stderr.strip() or push_result.stdout.strip()}"
            ),
            amend_failed_detail=amend_failed_detail,
        )

    return RevertOutcome(
        revert_sha=revert_sha, pushed=True,
        amend_failed_detail=amend_failed_detail,
    )


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def recover_on_recompose_failure(
    *,
    commit_sha,
    timeout_seconds=60,
    poll_interval_seconds=2,
    check_recompose_fn=None,
    runner=None,
    sleep_fn=None,
    clock_fn=None,
    target_root=None,
):
    """Wait for recompose; on failure or timeout, revert + alert.

    ``commit_sha`` is the SHA returned by C6 (``WriteResult.committed_sha``).
    The orchestrator NEVER raises — every failure path lands in the
    returned :class:`RecoveryPlan`'s ``path_chosen`` field.

    When ``check_recompose_fn`` is ``None``, returns
    ``path_chosen="skip"`` — the PRD-E harness-watch contract is not
    wired and the orchestrator cannot decide. The caller logs the skip
    and continues; this is the expected state until PRD-E lands.
    """
    if check_recompose_fn is None:
        return RecoveryPlan(
            path_chosen="skip",
            original_commit_sha=commit_sha,
            alert_message=(
                "Recompose-failure recovery skipped — PRD-E harness-watch "
                "contract not wired. The L4 commit is on disk; if the "
                "harness's deploy-all step fails, recover manually."
            ),
        )

    recompose = wait_for_recompose(
        commit_sha=commit_sha,
        timeout_seconds=timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
        check_recompose_fn=check_recompose_fn,
        sleep_fn=sleep_fn,
        clock_fn=clock_fn,
    )

    if recompose.succeeded:
        return RecoveryPlan(
            path_chosen="success-no-action",
            original_commit_sha=commit_sha,
            recompose=recompose,
            alert_message=(
                f"Recompose succeeded for {commit_sha[:8]} in "
                f"{recompose.duration_seconds:.1f}s. No action required."
            ),
        )

    # status is "failure" or "timeout" — both route to revert per AC3.
    revert = revert_l4_commit(
        commit_sha=commit_sha,
        reason=recompose.diagnostic,
        runner=runner,
        target_root=target_root,
    )

    if revert.ok:
        alert = (
            f"L4 write {commit_sha[:8]} reverted via "
            f"{revert.revert_sha[:8] if revert.revert_sha else '?'} "
            f"after recompose {recompose.status}. "
            f"Reason: {recompose.diagnostic}"
        )
        if revert.amend_failed_detail:
            alert += (
                f" (note: revert commit message uses git's default — "
                f"{revert.amend_failed_detail})"
            )
        return RecoveryPlan(
            path_chosen="revert-attempted",
            original_commit_sha=commit_sha,
            recompose=recompose,
            revert=revert,
            alert_message=alert,
        )

    # Revert itself failed — the worst path. The L4 file is on disk in
    # the broken state; manual operator intervention is required.
    return RecoveryPlan(
        path_chosen="revert-failed",
        original_commit_sha=commit_sha,
        recompose=recompose,
        revert=revert,
        alert_message=(
            f"CRITICAL: L4 write {commit_sha[:8]} caused a recompose "
            f"{recompose.status} AND the revert itself failed at the "
            f"`{revert.failure_stage}` phase. Manual operator intervention "
            f"required. Recompose diagnostic: {recompose.diagnostic}. "
            f"Revert diagnostic: {revert.failure_detail}"
        ),
    )


# ---------------------------------------------------------------------------
# Iteration-log entry (per AC5)
# ---------------------------------------------------------------------------


def format_iteration_log_entry(plan):
    """Render a one-block iteration-log entry per AC5.

    Block carries: original L4 write commit SHA, recompose outcome /
    reason, and the revert commit SHA when a revert occurred. The
    skip path emits a single-line marker so the iteration log still
    shows that recovery was considered.
    """
    lines = []
    sha = plan.original_commit_sha or "(unknown)"
    if plan.path_chosen == "skip":
        lines.append(f"- L4 write {sha[:8]}: recovery skipped (no check_recompose_fn wired).")
        return "\n".join(lines)

    lines.append(f"- L4 write {sha[:8]} — post-commit recompose recovery:")
    if plan.recompose is not None:
        lines.append(f"  - recompose status: `{plan.recompose.status}`")
        if plan.recompose.diagnostic:
            lines.append(f"  - recompose diagnostic: {plan.recompose.diagnostic}")
        if plan.recompose.duration_seconds:
            lines.append(f"  - wait duration: {plan.recompose.duration_seconds:.1f}s")
    if plan.revert is not None:
        if plan.revert.revert_sha:
            lines.append(f"  - revert commit: `{plan.revert.revert_sha[:8]}`")
        if plan.revert.failure_stage:
            lines.append(
                f"  - revert failed at `{plan.revert.failure_stage}`: "
                f"{plan.revert.failure_detail}"
            )
    return "\n".join(lines)
