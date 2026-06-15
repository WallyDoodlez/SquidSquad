# Working State

- **Task**: #11613 (in-progress) — installer dep auto-provisioning; concrete fixes done, §4.1 build deferred
- **Status**: in-progress (chunk 1 committed+pushed; §4.1 main build front-loaded for fresh cycle)
- **Updated**: 2026-06-15 (skill — event-mode)
- **Quiet Cycle Counter**: 0

## >>> ON RESUME — #11613 §4.1 BUILD (TOP PICKUP, in-progress on `squidsquad/task/11613`) <<<
Operator directive (17:xx): set #10855 aside; build APPROVED installer cluster **#11613 → #12419 → #12420 (serial)**; #12363 open; #12460 (slice d cutover) gated on operator.
**#11613 chunk 1 DONE + pushed** (commit 4ff24f742): pyyaml→requirements.txt; start.sh/ps1 `pip install -r requirements.txt` + widened import probe. Drift+installer-wiring+start-team green.
**REMAINING = §4.1 main build in `references/scripts/wizard.py`** (spec: docs/INSTALLER-ARCH.md §4.1; research: .squidsquad/pm/planning/RESEARCH-INSTALLER-DEPROV-11537.md). Model = **gather-all → present → ONE consent → provision → re-verify** (never fail-fast):
1. **Gather-all detector** — ONE pass enumerating EVERY missing dep (no bail on first): `gh` installed, `gh` auth, Python3, pip, runtime pkgs (`requirements.txt`), `claude` CLI on PATH. Each annotated with its per-OS provisioning action. EXTEND wizard.py's single-helper-JSON envelope pattern (today it checks ONLY gh, fail-fast — see wizard.py:166 `shutil.which("gh")`). Returns the full missing-set.
2. **Per-platform dispatch** in ONE helper (don't scatter): system tools (gh/Python/pip) → winget|choco (Win) / brew (macOS) / apt|dnf (Linux); packages → `pip install -r requirements.txt`.
3. **Consent** — present full missing-set in plain language + proposed action each; ONE permission ask ("Install these N?"); nothing installed before consent.
4. **Guided (NOT auto)**: `claude` CLI (npm `npm i -g @anthropic-ai/claude-code`, only if npm present else instruct) + `gh auth login` (interactive) — surface as guided steps.
5. **Re-verify** — re-run gather-all; still-missing → instruct + stop clean (Phase 0 is pre-Phase-5, abort = no repo writes).
Notes: install-time = consent gate (human present); boot-time start.sh/ps1 = SILENT re-ensure (no prompt) — chunk 1 already did the start-script unified read. DS-review-per-AC (install+boot blast radius). Installer agent acts on helper JSON, never invents checks. AC: compose-consumption verified, no regression to existing prereq check.
**This §4.1 build is high-blast-radius → fresh context warranted (deferred from a 3-feature marathon tail).**

## >>> #12460 (slice d — #12271 CUTOVER) — NOW APPROVED (operator 2026-06-15), highest blast radius <<<
Completes #12271: flips the harness reboot decision PID-existence → progress signals (the heartbeat #12443 + pause-guard #12458 already on main), demotes PID to teardown-only. **PM-MANDATED STRATEGY = SHADOW/PARALLEL VALIDATION (do NOT hard-flip first):** (1) run progress-based liveness ALONGSIDE the existing PID-liveness in update_health — log what EACH would decide, alert on divergence; (2) confirm no false-positives (rebooting a healthy/paused agent) AND no false-negatives (missing a real zombie — the #10855/#10440 pattern); (3) ONLY THEN remove the PID-liveness path. DS-review-per-change, incremental commits, comprehensive tests INCL. a zombie repro. Build it from `active_pause()`/`last_activity_at` (slice b/c) — silence relative to dispatched work = the new death signal. **THE most sensitive harness change — fresh context + the shadow strategy mandatory.** Subsumes #10855 (inert/zombie boot) + #12409 ask-2.

## (earlier this session) RESTART context
restart-required acked; 3 liveness slices (a/b/c) shipped + #11613 chunk 1. TWO high-blast-radius approved items queued for fresh context: **#11613 §4.1 build** + **#12460 cutover**. Then #12419/#12420 (serial), #12363 → #12409 ask-1 → #12408 → #12397 → #10690/#10686.
**#12458 → SHIPPED + CLOSED (PR #12459 merged)** — pause-aware guard. #12271 slice c pause-aware guard: silence/dead-PID = death only when no hook explains it; guards update_health (HOLD while active_pause, ceiling-bounded + clock-skew; StopFailure throttle→backoff; AC5 genuine-death unchanged). 6 commits. DS: guard (DeepSeek — caught 2 errors: in-flight ceiling + graceful-throttle streak; fixed), plumbing (Sonnet fallback after model_router exit 2; fixed). Curated gate GREEN (2x; one transient exit-1 flake ruled out). §16 doc flagged @pm. StopFailure cause best-effort (verify payload). Vault: [[learning-guarding-a-status-machine-death-decision-needs-hold-resume-and-ceilinged-signals]].
**THREE #12271 liveness slices shipped today (a/b/c = #12418/#12443/#12458).** Slice d = **#12460 (FILED, status:pending — NOT approved, do NOT build)**: the cutover (flip reboot decision PID→progress, demote PID to teardown). PM holding for explicit operator go + cutover strategy (PM recommends SHADOW/PARALLEL validation: run progress-liveness alongside PID-liveness, log divergence, confirm no false-positives, THEN hard-flip). Highest blast radius — fresh context + the agreed strategy when approved. WATCH for #12460 approval.
Next pickup order: **#12363** (/T teardown + killpg, design posted) → #12409 ask-1 → #12408 (fix EARLY) → #12397 → installer batch (#11613/#12419/#12420) → #10690/#10686.
Operator directive (06-15) stands: **proceed WIP-safe (commit incrementally + checkpoint every step), DS-review-per-change.**

## >>> ON RESUME (fresh-cycle pickup order) <<<
**#12443 → SHIPPED + CLOSED (PR #12457 merged)** — #12271 slice b activity heartbeat (PostToolUse/PostToolUseFailure async-command hooks + cycle_post → harness /hooks/activity → AgentState.last_activity_at, throttled disk write). Observational only (AC5). DS: harness 1-warn-fixed, emitters NO_FINDINGS. Also closed slice-1's latent /hooks/session-end route-contract gap (#12408 masking hid it). **§16 doc-sync flagged to @pm** (native-http only for low-freq/teardown; high-freq telemetry = async command hooks). Vault: [[learning-claude-code-http-hooks-block-only-command-hooks-async]].
**#12442 → SHIPPED + CLOSED (PR #12444 merged)** — EAD handoff re-emit. Vault: [[learning-single-emit-wake-nudge-needs-bounded-reemit-and-must-bypass-time-filter]].
**Both shipped this session.**

## >>> TOP FRESH-CYCLE PICKUP: #12458 (#12271 slice c — pause-aware guard) — APPROVED, role:skill, HIGH <<<
**Deferred to a FRESH context window on purpose** (build-at-low-context discipline): unlike slices a/b which were OBSERVATIONAL (record-only), slice c **MODIFIES THE REBOOT DECISION** (update_health / #12244 backoff / PID-death path) — highest-blast-radius harness code (the reboot-churn cluster's core; cf. #12418-C where DS caught a breaker-bypass). Do NOT build it at a long-session tail.

**Front-loaded plan (context warm from slices a/b — reuse, don't re-derive):**
- **Hooks (compose):** add PreToolUse + Notification + PreCompact + StopFailure to settings.json via the SAME `_ensure_hook_entries` helper I built (#12443). PreToolUse CAN block → MUST be async command hook (NOT http) — same lesson as [[learning-claude-code-http-hooks-block-only-command-hooks-async]]. Notification/PreCompact/StopFailure are low-freq → http is OK (but verify each can't block harmfully). Extend activity_hook.py OR a sibling poster; new harness endpoint(s) e.g. /hooks/pause (mirror /hooks/activity: X-Agent-Role, fail-open, unknown-role drop, throttle if hot).
- **Harness records pause state** on AgentState: in_flight tool-call + tool_call_max deadline (PreToolUse sets; PostToolUse from #12443 CLEARS it — wire the clear), waiting (Notification), compacting (PreCompact, cleared by PostCompact), last StopFailure cause. New __slots__ + to_dict + save/load + route-contract manifest entries (don't repeat the #12443 orphan-route miss!).
- **GUARD update_health (AC3, the sensitive part):** before the dead-PID/silence→reboot decision, suppress reboot if a pause signal active: (a) mid-tool-call within tool_call_max → suspend death timeout; (b) Notification-waiting → not dead; (c) compacting → not dead; (d) StopFailure rate_limit/overloaded → BACK OFF via the #12244 backoff (reboot_blocked_until), not tight respawn. AC5: genuinely-dead (PID dead + NO pause signal) still reboots exactly as today — regression-test this hard.
- **tool_call_max** = hard ceiling above longest legit single call (full suite run, slow build, long subagent). Open Q in §15.7 — pick a generous default (e.g. 600-900s), make configurable.
- DS-review-per-change MANDATORY (reboot decision). Tests per guard branch (AC6): in-flight, waiting, compacting, rate-limit-backoff, genuine-death.
- Design refs: HARNESS-ARCH §15.1 + §16.2. Builds on slice-b last_activity_at.
- **Next after c:** slice (d) retire PID-poll (the cutover — consumes heartbeat + this guard, removes #10101/#10440 from liveness path). PM files (d) when (c) lands.

Then the rest of the queue: #12363 (/T teardown + killpg) → #12409 ask-1 → #12408 (fix EARLY) → #12397 → installer batch (#11613/#12419/#12420) → #10690/#10686.
Next pickup order: **#12363** (/T teardown + killpg, design posted) → #12409 ask-1 → #12408 (fix EARLY — its masking hid the route-contract gap) → #12397 → installer batch (#11613/#12419/#12420 serial) → #10690/#10686.
NOTE: a restart-required (recompose, .squidsquad/skill/CLAUDE.md changed) was acked but deferred — context healthy; honor at next clean boundary if it recurs.
Operator directive (06-15) stands: **proceed WIP-safe (commit incrementally + checkpoint every step), DS-review-per-change.**

## Shipped to QA / SHIPPED
- **#12442** → **SHIPPED** (PR #12444 merged 2026-06-15) — EAD re-emits assigned-to for stuck handoff statuses (600s cadence, bypasses updatedAt filter); fixed single-emit + startup-blindness starvation. NOW LIVE. Routing landed EAD-assigned-to-only (PM doc-syncing /work/assign removal). Vault: [[learning-single-emit-wake-nudge-needs-bounded-reemit-and-must-bypass-time-filter]].
- **#12418** → **SHIPPED** (PR #12441 merged) — SessionEnd-reason hook (#12271 liveness slice 1). 3 DS-reviewed components; C review caught a None-TypeError + breaker-bypass (fixed). Vault: [[learning-sessionend-presence-not-stop-reason-and-spam-resistant-breaker]].
- **#12442** (NEW, open, medium, mine) — #12342 EAD gap: pending-ship→dm single-emit; if DM misses the one nudge there's no re-emit (same single-delivery limit as back-transitions). #12380 shipped fine (routing works), so likely emitted-but-missed → fix = delivery-robustness (re-emit cadence for unhandled pending-* / DM idle-rescan). **Fresh-cycle pickup** (don't debug EAD at 79% ctx).
- (orig) **#12418** → pending-test (PR #12441). SessionEnd-reason hook (#12271 slice 1). 3 components, each DS-reviewed: A (compose+settings.json native type:http hook, role via X-Agent-Role header from $SQUIDSQUAD_ROLE), B (harness ingest — NO_FINDINGS), C (reboot decision graceful-vs-crash; **DS caught a None-TypeError ERROR + a crash-loop-breaker bypass** → graceful no longer resets the streak, last_session_end cleared on all spawn paths). ~30 tests; full suite green (pytest exit codes). Endpoint header-based /hooks/session-end (PM affirmed shape). AC1 verifies by RUNNING compose. Residual deliberate-spam gap → #12271 hardening. DS-REVIEW-12418-{A,B,C}.md on main. Vault: [[learning-sessionend-presence-not-stop-reason-and-spam-resistant-breaker]].

## Shipped this session
- **#12282** SHIPPED — reboot-churn root cause (test POSTing real /restart to live harness). Vault: [[learning-default-port-fallback-is-live-egress-trap-in-tests]].
- **#12244** SHIPPED — re-marked from stuck per PM AC-amendment (cause-agnostic backoff).
- **#12342** SHIPPED — event-mode EAD routes pending-test→qa / pending-ship→dm (was starving QA/DM). NOW LIVE (harness restarted — confirmed by receiving real routed assigned-to events; QA/DM pipeline now works end-to-end). Vault: [[learning-ead-status-routing-and-back-transition-dedup]], [[learning-runtime-resolves-by-alias-not-role-class]].
- **#12380** SHIPPED (PR #12391) — compose `.local-config` alias-keying (QA boots into PM's clone). QA rejected once (a clone-refusal test asserted the qa-absent BUG as its premise) → fixed by mocking `_get_clone_path`, re-verified, shipped. #11600 (role:pm) can close as tracked-under-#12380. PM can stop band-aiding `.local-config`.

## Filed (my domain, deferred to fresh cycle — all reboot-churn cluster)
- **#12409** (open, high) — slow reboot loop (>60s, #12244 backoff misses it). **Ask 1 = frequency-based breaker = my next pickup.** Ask 2 → #12271 (SessionEnd-reason); Ask 3 → #12363 (orphans). Triaged. qa stable on loop-mode stopgap.
- **#12397** (open, high) — l4_file_watcher emits restart-required on NO-OP recompose (got a spurious one, declined to reboot). Fix design in issue.
- **#12408** (open, high, QA-filed) — run_tests.py static gate exits 0 despite failing tests (masked my #12380 regression). Use pytest exit codes until fixed.
- **#12363** (open, medium) — orphan claude/event_poll accumulation.
- **#10855** (in-progress, QA FAIL-back) — inert/zombie boot. FAIL reason was "harness down, couldn't test AC-4 live" (not a code defect found); real fix overlaps #12271 progress-based liveness. Effectively blocked on #12271.

## Approved (next feature work)
- **#10690** (approved, medium, gate lifted) — Wiki-link rework + documentation-linkage sub-skill (LLM-consumed → CQ + DS-review + compose).
- **#10686** (approved, medium) — PRD-E E7 V2 migration smoke.

## Resolved / off-plate
- **#11505** — PM pipeline-sentinel **verified my analysis** and ruled it superseded-by-#10025 (capability-check is one load-bearing unit owned by #10025; #11505's only bounded scope was already done in the 05-27 cleanup). PM recommends OPERATOR close it (part of an operator bundle). skill: stay off it; capability-check resumes under #10025. **Done — no skill action.**

## APPROVED — top fresh-cycle pickups (operator batch-approved 2026-06-15; build at LOW context, not marathon-tail)
- **#12418** (task, approved, HIGH) — **#12271 slice 1: SessionEnd-reason hook.** TOP PICKUP. Add a `SessionEnd` hook (deployed per-clone via compose/installer `settings.json`) reporting exit reason+code → harness records on AgentState → reboot decision (§7.4) consumes it. Augments PID-poll (doesn't retire it). Design on main: HARNESS-ARCH §15.4 + §16. Multi-file (compose + harness + settings.json) → front-loaded plan + tests + DS review. De-risks the #12244 reboot-decision root.
- **#12271** (task, approved, high) — parent: progress-based liveness redesign (hooks + heartbeat, demote PID to teardown). Being delivered in SLICES; #12418 is slice 1. Subsumes #10855 + #12409-ask2.

## Pending-approval (not buildable yet)
- **#10025** (task, pending, low) — FULL capability-check framework retirement (absorbed #11505's scope). Mine once approved.
- **#12416** (task, pending, low) — delete thin_launcher.py / direct spawn (HARNESS-ARCH §14).

## Installer tasks (approved 2026-06-15, medium — fresh-cycle)
- **#11613** — installer dependency auto-provisioning (gather-all → …).
- **#12419** — installer migration-walk in wizard.py (INSTALLER-ARCH).
- **#12420** — installer post-commit harness restart (INSTALLER-ARCH).

## Budget note (this session)
Context ~56% at last check (threshold 70%) — ~14% headroom, insufficient to COMPLETE a high-blast-radius implementation (tests + DS review) cleanly. Deferring new implementation to a fresh cycle is the budget+quality call, NOT avoidance — all deferred items carry pinned RCAs + fix designs on their issues. **Operator/pressure-restart gives a clean fresh cycle** (better than marathon-tail partials).

**Fresh-cycle priority order:**
1. **#12418** (slice 1, HIGH) — SessionEnd-reason hook (de-risks reboot decision).
2. Reboot-churn hardening (open, high): #12409 ask-1 (freq breaker), #12408 (run_tests gate masking — fix EARLY, it hid my #12380 regression), #12397 (no-op recompose), #12363 (orphan kill-tree, design posted).
3. #12271 further slices (#12419/#12420 are installer, not liveness — #12271 has more liveness slices coming).
4. Installer batch: #11613, #12419, #12420 (medium).
5. Features: #10690 (sub-skill — CQ+DS+compose), #10686 (V2 migration smoke, manual).
6. Housekeeping: #10855 stale PR #10952 (close-as-superseded vs salvage — assess vs shipped #12342/#12380), #12294 (.claude-pid authority), #11716 (low).

## Process learnings this session
- DS per-change review caught real regressions in BOTH #12342 (back-transition dedup) and #12380 (duplicate alias) that forward-only tests missed. Hold pending-test for DS on high-blast-radius.
- #12380 regression: a test asserted the inverted invariant (qa absent = the bug). Tests must control config state, not depend on live `.local-config`. (QA vault: pattern-resolve-config-against-live-install-not-test-fixture.)
- Verify with pytest exit codes, NOT run_tests.py gate (#12408 masks failures).

## Improvement Scan
Status: idle
Last completed: (none this session)
Next scan after: (eligible)
