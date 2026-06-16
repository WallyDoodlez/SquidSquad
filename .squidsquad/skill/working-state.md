# Working State

- **Task**: ON RESUME → resume #12460 (in-progress, shadow deploy-ready, cutover HELD on external gate)
- **Status**: #12475 SHIPPED+CLOSED; #12460 gated on shadow merge→observe (PR #12472). Honoring restart-required at clean boundary.
- **Updated**: 2026-06-15 (skill — event-mode, pre-restart checkpoint)
- **Quiet Cycle Counter**: 0

## >>> ON RESUME — #12460 (#12271 slice-d CUTOVER) is the live in-progress task <<<
Shadow phase DONE + deploy-ready (PR #12472, merged main, 303 green, pushed). CUTOVER (ACs 1/4: flip reboot decision PID→progress at ~harness.py:542, demote PID to teardown-only, remove #10101/#10440 walk from liveness path) is HELD per operator shadow-first mandate — needs PR #12472 to MERGE + run on the live harness to produce a PID-vs-progress divergence window BEFORE writing the flip. Decision posted to #12460 (22:03): asked DM to merge #12472 (open observation window) OR PM to formally split (shadow shippable now / cutover follow-up). **WATCH for: DM pr-merged on #12472, or PM transition/assigned-to on #12460.** Front-load map: planning/12460-liveness-map.md. Vault: [[learning-activity-liveness-redispatch-must-not-reset-grace]].

## Shipped this session (all 3 CLOSED)
- **#12475** SHIPPED+CLOSED (PR #12486 DM-merged) — tracker.py `--force` full legality override (+ authority + unread-feedback); ship-integrity gates kept hard. Forced swap strips LIVE status labels (no double-label corruption — DS R1 catch). 2 DS reviews, 17 tests. Vault: [[learning-human-override-must-make-the-mutation-idempotent-not-just-skip-the-gate]].
- **#11613** SHIPPED+CLOSED (PR #12471) — installer dep auto-provisioning. Vault: [[learning-shell-out-provisioning-has-three-sharp-edges]].
- **#12473** SHIPPED+CLOSED (PR #12474) — L1 no-action-wake plain-language comms.

## Next queue (fresh-context pickups; not yet started)
- **#12450** (approved + assigned, medium) — installer auto-detect unit-test strategy (L3). Operator locked a design Q in the approval comment — read it. Independent of harness (branch off main).
- **#12451** (status bar event-vs-loop) — planning-complete + operator-approved 22:10; pick up when its approved/assigned-to routes.
- Then reboot-churn: #12409 ask-1 → #12408 (fix EARLY) → #12397 (no-op recompose restart-required — note: this very class of event) → #12363 → features #10690/#10686.

## Process / standing directives
- Operator (06-15): proceed WIP-safe (commit incrementally + checkpoint), DS-review-per-change.
- Feature-branch pre-commit guard (#11511) STRIPS .squidsquad/ from task-branch commits → vault/working-state land on MAIN directly (working branch), not in feature PRs.
- Verify `git branch --show-current` before commits (task-begin switches branch). Always merge main into branch, never rebase.
- Verify with pytest exit codes, not run_tests.py gate (#12408 masks failures).

## Improvement Scan
Status: idle
Last completed: (none this session)
Next scan after: (eligible)

## >>> ON RESUME — #12460 (#12271 slice-d CUTOVER), high priority, HIGHEST blast radius <<<
Operator APPROVED the cutover (2026-06-15 18:02) with the **shadow/parallel validation** mandate: run progress-based liveness ALONGSIDE PID-liveness first → log divergence → confirm no false-pos/neg → THEN remove PID-liveness. Restart resume directive (a771871299) reaffirms: "Resume the APPROVED cutover #12460 ... shadow-mode strategy ... Commit incrementally."

**SHADOW PHASE = DONE + DEPLOY-READY** (3 commits on branch, PR #12472 OPEN):
- `73dab2d58` progress-liveness foundation — `AgentState.progress_liveness(now)` + `last_dispatch_at` dispatch-reference + `should_advance_dispatch()` (re-nudge of unacted work must NOT reset grace — the DS-c1 trap; `ACTIVITY_GRACE_SECONDS=600` == `_HANDOFF_REEMIT_SECONDS=600`). EAD emit site stamps `last_dispatch_at` under lock, guarded by `should_advance_dispatch()`.
- `3b16ebba0` DS review fixes (c1, 4 findings).
- `4f9f15c82` shadow divergence logging in `update_health()` (OBSERVATIONAL — computes `progress_liveness` alongside PID `alive`, logs "LIVENESS DIVERGENCE / candidate-zombie / candidate-false-reboot-avoided"; does NOT change `alive` or the reboot decision).
- This cycle: merged current `origin/main` (clean — main's 6 new commits = #11613 ship + qa/pm ops, zero harness.py/roles overlap), full suite **GREEN 303 passed**, pushed → PR #12472 current & mergeable (`f8b23e350`).
- Tests: `tests/test_12460_progress_liveness.py` (24 — zombie repro #10855, re-emit-never-resets-grace, persistence, update_health divergence logging).
- Front-load map: `.squidsquad/skill/planning/12460-liveness-map.md`. DS reviews: `DS-REVIEW-12460-c1.md`, `-c2.md`.
- Vault: [[learning-activity-liveness-redispatch-must-not-reset-grace]].

**CUTOVER (ACs 1 & 4) = HELD, NOT YET WRITTEN.** Gated on the shadow MERGING + running on the live harness to produce a PID-vs-progress divergence window (per the mandate; writing the flip before observing violates "run alongside first → confirm → THEN remove"). Cutover commit when unblocked:
- Replace `alive = boot_remote._is_process_alive(pid)` (~harness.py:542) with progress-derived liveness; call `progress_liveness()` UNDER `self._lock`.
- Demote PID to teardown-only; remove #10101/#10440 descendant-walk from the LIVENESS path (keep for teardown/kill).
- AC4 + zombie repro e2e (#10855 inert-boot pattern); AC5 no-regression (genuine death still reboots; #12244 backoff, #12442 routing, SessionEnd graceful-vs-crash intact).
- Then → pending-test. Completes #12271; subsumes #10855 + #12409 ask-2.

**Decision posted to #12460 (22:03):** shadow deploy-ready; asked DM to merge PR #12472 so the observation window opens (I keep #12460 in-progress + hold cutover), OR PM to formally split (shadow = shippable now via #12460→pending-test, cutover = follow-up task). Awaiting PM/DM. WATCH for a transition/assigned-to on #12460, or a DM pr-merged on #12472.

## >>> NEXT QUEUE (do NOT bulldoze mid-#12460-hold; fresh context for substantive ones) <<<
- **#12450** (approved + assigned, medium) — installer auto-detect **unit-test strategy** (L3 software-dev). Operator locked one design Q in the approval comment (read it). Fresh-context warm-up; independent of harness (branches off main, no #12460 conflict).
- **#12451** (status bar event-vs-loop mode) — **NOT ready**: operator state-corrected approved→**planning** (21:59, swept into an "approve-all" then pulled back). PM still planning. Do NOT pick up until re-approved.
- Then reboot-churn cluster + features: #12409 ask-1 (freq breaker) → #12408 (run_tests gate masking — fix EARLY) → #12397 (no-op recompose) → #12363 (orphan kill-tree) → #10690 (sub-skill CQ+DS+compose) → #10686 (V2 migration smoke).

## Shipped this session
- **#11613** SHIPPED + CLOSED (PR #12471 DM-merged) — installer dependency auto-provisioning (gather-all → consent → provision → re-verify, INSTALLER-ARCH §4.1). wizard.py `gather_deps`/`provision_deps` + helpers + CLI; WIZARD.md Step 0; 55 tests. Vault: [[learning-shell-out-provisioning-has-three-sharp-edges]].
- **#12473** SHIPPED + CLOSED (PR #12474 DM-merged) — operator L1 comms fix: no-action wake shows plain one-liner (`🦑 Checked the latest activity …`), prohibits internal jargon. SOUL.md User-Facing Communication subsection + instructions.md §3 ref; all 4 roles recomposed/verified.
- **#12418 / #12443 / #12458** (slices a/b/c of #12271) shipped earlier — SessionEnd-reason, activity-heartbeat, pause-aware guard. All on main; slice-d (#12460) consumes them.

## Process / standing directives
- Operator (06-15) stands: **proceed WIP-safe (commit incrementally + checkpoint every step), DS-review-per-change.**
- DS per-change review caught real regressions (#12342, #12380, #12418-C, #12460-c1) that forward-only tests missed — hold pending-test for DS on high-blast-radius.
- Verify with pytest exit codes, NOT run_tests.py gate (#12408 masks failures).
- Always merge main into branch, never rebase. Verify `git branch --show-current` before every commit (task-begin can switch branch mid-cycle).

## Improvement Scan
Status: idle
Last completed: (none this session)
Next scan after: (eligible)
