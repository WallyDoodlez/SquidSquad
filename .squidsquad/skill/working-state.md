# Working State

- **Task**: #12509 → pending-test (PR #12517); #12493/#12492 held on gates; #12506 w/PM; #12511 next pickup
- **Status**: 4 shipped; #12509 in verifier's hands; #12492/#12493 held; #12506 w/PM (§8.6); #12511 queued
- **Updated**: 2026-06-16 (skill — event-mode)
- **Quiet Cycle Counter**: 0

## >>> #12509 → PENDING-TEST (PR #12517) — test 'harness' basename shadow <<<
Renamed `tests/integration/harness.py` → `integration_harness.py` (git mv) so it stops shadowing `references/scripts/harness.py` in sys.modules — `pytest tests/` now collects 4706 / 0 errors (was Interrupted, 2 errors). Updated 3 importers + 2 e2e stale comments; regression guard `tests/test_12509_no_harness_basename_shadow.py`. Verified: collection clean, 8 harness-importing files + guard = 432 passed, integration collects 53. Test-only → no DS/CQ. (Branch off main.)

## >>> #12511 (NEXT PICKUP, fresh context) — test-isolation: force-transition tests leak real events to live bus <<<
PM-filed (MEDIUM), assigned to me. **My dup #12510 → CLOSED.** Root cause: unit tests calling real `tracker.transition(... --force)` (test_12475_force_bypasses_legality.py etc.) POST real `status-transition` events to the LIVE harness for placeholder #999 → wakes the whole team (the recurring #999 flurry that plagued THIS session). **Fix design:** autouse fixture in tests/conftest.py stubbing `event_bus.emit` (or the harness POST) for unit tests — CAREFUL: must not break tests that themselves assert emit was called (e.g. test_forced_transition_emits_status_event mocks event_bus directly — per-test mock must take precedence over the autouse no-op). Verify the #999 flurry stops. Active disruption was from MY suite runs (now stopped), so not urgent — but real test-hygiene (CI/other agents). Fresh context warranted (event_bus internals + fixture-interaction care).

## >>> #12506 IMPL SCOPE (front-loaded; HANDS BACK to skill when PR #12518 §8.6 merges) <<<
PM's DS-audit (deepseek-v4-pro, .squidsquad/pm/planning/AUDIT-AGENT-RUNTIME-86-83-2026-06-16.md) split the work. PM-lane doc fixes already on PR #12518. **MY-LANE items (must land WITH my impl — §8.6.1 arch flags them knowingly-inconsistent until then):**
1. **config.md `## Improvement Scanning`:** add `- **Idle Scan Burst**: 3`; add `m` unit → `Improvement Scan Cool-Down: 30m` (currently unitless `30`, drifts vs sub-skill/arch).
2. **idle-cooldown-loop.md step 5:** REMOVE the false 'Monitor delivers NUDGE at a short fixed cadence' claim (the exact #12506 bug); name the **§8.6.1 periodic driver** as the cadence source; KEEP the 'if NUDGE arrives' branch (orthogonal forge-event wake) + cool-down eligibility check unchanged.
3. **idle-cooldown-loop.md 'Cool-Down Configuration':** document the new `Idle Scan Burst` key (default 3 = bounded burst per idle period).
4. **The actual driver:** schedule a low-freq cron/`/loop` self-wake at event-mode boot (per §8.6.1), alongside the Monitor (two orthogonal wake sources, no harness change). Wire into event-mode-contract / boot. + tests.
§8.6.1 audited COMPLEMENTARY to HARNESS-ARCH §15 liveness (no conflict — driver tool-calls generate §15 activity heartbeats). **GATE: PR #12518 merge (operator) → reassigns #12506 to skill.** Read the audit file when it's on main.

## >>> #12506 (improvement subloop dormant team-wide) — RCA DONE, routed to PM as ARCH gap <<<
**RCA (confirmed):** event-mode boot schedules NO periodic driver for idle work — only forge-event wakes. So an idle event-mode agent (pm/skill/dm) never wakes to evaluate the improvement-scan cool-down → scan never fires (dormant for weeks). `idle-cooldown-loop` step 5 ASSUMES a 'fixed-cadence Monitor wake' that `event_poll.py` never delivers (it only NUDGEs on forge events, L325 `if clean or evicted`).
**Operator (2026-06-16) reframed it ARCH-FIRST** (I had started a transport-layer fix — idle-tick in event_poll.py — operator correctly called it the wrong layer; **BACKED OUT**, branch deleted). Correct fix = scheduling layer using the existing cron/`/loop` primitive: event-mode boot should schedule a low-freq self-wake for idle work, alongside the Monitor. **Routed #12506 → planning (PM)** for AGENT-RUNTIME §8.6 spec (event-mode periodic driver + how a cron/`/loop` tick coexists with the persistent Monitor + reconcile idle-cooldown-loop step 5). **Comes back to skill for the code impl once §8.6 lands** (same shape as #12493). Leads 2 (dm #10540 gate, PM) + 3 (qa loop-mode staleness, separate path) noted, not in this arch.

## >>> #12493 (pipeline-sentinel) — BUILT + DS-SHIP, HELD on arch-first gate <<<
Operator restructured #12493 **arch-first** (2026-06-16): PM authors a semantic-handoff-backstop subsection in **AGENT-RUNTIME §8.3** FIRST (the sentinel backstops *semantic/comment-only* handoffs the way EAD backstops *forge-state* changes — EAD polls state, not comment bodies, so a comment-only handoff like #12460 rides no event + no EAD catch). **#12493 impl is GATED on §8.3 landing** (impl conforms to + cites arch, not reverse). My #12495 (work-assign doc/impl gap) was folded into the SAME §8.3 reconciliation (PM owns arch).
- **Built + ready**: branch `squidsquad/task/12493` → PR #12494. Rewrote pipeline-sentinel.md §2: progress-based halt detection (incl. comment-only failed-handoff), 4-class investigate, event-effective remedies (authorized transition→EAD wake; NO bare-comment handoffs; does NOT prescribe phantom work-assign), PM-authority boundary, escalate-with-options (pending-human-review + options), #12460 worked example. 2 DS reviews (R1 BLOCK→fixed, R2 SHIP). compose+catalog green (159); marker-loaded sub-skill (AC8 = marker present in PM CLAUDE.md, body runtime-loaded not inlined). installer-files.txt already lists it (AC9 no-op). CQ AC7 in body (verifier authors spec).
- **ON RESUME when §8.3 lands** (watch for a wake event from PM — bare comment won't reach me): (1) add citation to the new §8.3 semantic-handoff-backstop subsection, (2) reconcile class-naming/terminology to match arch verbatim, (3) re-compose + re-DS, (4) → pending-test.

## >>> #12460 → pending-test (SHADOW) + #12492 held cutover — operator PATH B split <<<

## >>> #12460 → PENDING-TEST (SHADOW) + #12492 HELD CUTOVER — operator PATH B split (2026-06-16) <<<
Operator chose **PATH B (formal split)** on my #12460 fork:
- **#12460 = the SHADOW increment** (observational): progress_liveness() computed alongside PID in update_health(), divergence LOGGED, reboot decision UNCHANGED. Advanced → pending-test (PR #12472, branch refreshed onto main bd1072f05, 303 green). Verifier scope: reboot behavior unchanged + shadow CAN produce a 'dead' verdict for a constructed zombie + suite green. NOT the flip. (Unread-feedback guard blocked the first transition; cleared after posting my scoped handoff comment.)
- **#12492 = the CUTOVER flip** (approved, role:skill, HIGH, **HARD-GATED**): remove PID-poll as reboot decider, progress-liveness authoritative, PID→teardown-only. **DO NOT START** until #12460's shadow has MERGED + run on the live harness and produced a clean PID-vs-progress divergence window (no false pos/neg). I hold the cutover commits (foundation: progress_liveness/should_advance_dispatch/last_dispatch_at already on the #12460 branch; the flip itself = replace `alive = boot_remote._is_process_alive(pid)` ~harness.py:542 with progress-derived under self._lock, demote PID, remove #10101/#10440 walk from liveness path; AC: cite the divergence window as evidence, slow-boot agent (qa #12409) not falsely rebooted). Front-load map: planning/12460-liveness-map.md. Vault: [[learning-activity-liveness-redispatch-must-not-reset-grace]]. **WATCH for: DM pr-merged on #12472 → then the observation window opens → then #12492.**

## LEARNED THIS SESSION (process)
- A bare tracker-comment wakes NO agent in event mode — my 22:03 #12460 ask stalled ~2.5h until PM re-raised it via a real event. **To get an agent to act, post + ensure a routing event fires (transition/assigned-to/@mention that the harness emits), not just a comment.**

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
