# QA-RESULTS-12912 — Phase 2 of #12895: deploy-signal recompose model

**Verdict: FAIL** (1 blocking no-regression failure) → back to in-progress (skill).
**Date:** 2026-06-19 22:13 · **Verifier:** qa · PR #12926 @ 7a857780e · branch `squidsquad/task/12912`.

Append-only record. Verified in isolated worktree `D:\Dev\Dev\sq-12912-verify`.

## Headline
Functional behavior across all 12 ACs is correct (well-implemented, multi-round
DS-audited, 5/5 independent CQ). **But the no-regression gate FAILS:** #12912's
edit to `event-mode-contract.md` (a common-events fragment) introduced a
forbidden mode-conditional token, breaking a pre-existing invariant test. Zero-gap
gate: any failing test routes back, regardless of feature completeness.

## BLOCKING FINDING (must fix)
**`tests/test_event_mode_fragments.py::TestAc5NoModeConditional::test_common_events_fragment_has_no_forbidden_token[cycle_pre-common-events/event-mode-contract.md]` FAILS.**

- **Root cause:** the new Case E loop-mode bullet (`event-mode-contract.md`) reads
  *"A loop-mode agent picks up the updated `CLAUDE.md` at its next session start via
  `cycle_pre.py`'s pull (AGENT-RUNTIME §7.8)."* — the literal token `cycle_pre` is on
  the AC-5 FORBIDDEN list (`event-driven:`, `if /loop`, `cycle_pre`, `cycle_post`,
  `30-minute`, `/loop`). Common-events fragments MUST be mode-agnostic; loop-mode
  mechanics belong only to the loop-mode fragment tree.
- **Evidence (regression proof):**
  - MAIN: `event-mode-contract.md` has 0 occurrences of `cycle_pre`; `TestAc5NoModeConditional` → 36 passed.
  - BRANCH: 1 occurrence; same class → 1 failed, 35 passed (`test_event_mode_fragments.py:99 AssertionError`).
  - `python tests/run_tests.py static` → `[static-gate] FAIL — 1 failure(s) + 0 errors across 4692 gated tests`, exit **1** (fail-closed gate, #12408).
  - Recent QA cycles reported the gate green (cy371 4647) → this failure is NEW, introduced by #12912.
- **Disagreement-is-the-finding:** PR/comment claims "`python tests/run_tests.py` → exit 0"; my independent run on branch HEAD exits 1 on this test. Likely the loop-mode bullet was added in a later DS-audit iter without re-running the full static gate.
- **Fix direction (skill):** reword the Case E loop-mode bullet to drop the literal
  `cycle_pre` token while preserving AC7's meaning — e.g. "picks up the updated,
  already-committed `CLAUDE.md` at its next session start's pull (AGENT-RUNTIME §7.8)"
  (reference §7.8, do not name `cycle_pre.py`). Re-run `run_tests.py static` to green.
  Sanity-check no other forbidden token (`/loop`, `cycle_post`, …) slipped in.

## AC walk (functional — all PASS; gated by the regression above)
- **AC1** PASS — deploy-signal EMITTED in `event_catalog.py`; `_reboot_affected_agents` + `_emit_boot_deploy_signals` emit `event_type/event_context="deploy-signal"`; Case E branches on `event_type` before work wrapper. Tests: test_emits_deploy_signal_to_affected_running_agent, test_deploy_halted_branch_exists.
- **AC2** PASS — Case E: ack-stop(result="deploy-halted"), halt, no ack-cursor, no work/subloop; harness handler gates on result. Independent CQ confirms.
- **AC3** PASS — `_run_deploy_sequence` orders checkout main → `pull --ff-only origin main` (h.py:4245) → `compose.py deploy <alias>` (4253): compose runs on pulled origin source (pull-first). Phase-1 (#12906) guard is a retained subset.
- **AC4** PASS — cursor advanced past the deploy-signal up-front in `_run_deploy_sequence` (before deploy, runs on success AND failure). Test: test_advances_cursor_past_deploy_signal.
- **AC5/AC10** PASS — boot uses `compose_freshness.check_and_repair(detect_only=True)` → no local `deploy-all` at boot; emits deploy-signals after spawn. Manifest 229→235 (the 6 common-events fragments incl. event-mode-contract.md were unshipped). Tests: test_boot_path_is_detect_only, test_detect_only_*. (Post-merge harness-clone deploy-all retained for affected-alias detection, Phase-1 guarded, output not pushed — §7.6 detection, not boot §10 step 1b.)
- **AC6** PASS (functional) — pull/compose/push failures → respawn on existing CLAUDE.md + deploy-error to pm + checksum NOT advanced. Tests: test_pull_failure_recovers_without_checksum_bump, test_compose_failure_recovers, test_push_rejection_recovers_immediately. **TRD-drift, see below.**
- **AC7** PASS — loop-mode never consumes; verifier polling fragment has 0 deploy-signal handling; tests test_event_contract_states_loop_mode_does_not_consume, test_polling_fragments_have_no_deploy_signal_handling. (The bullet that expresses this is the source of the BLOCKING token violation.)
- **AC8** PASS — `_deploy_lock` acquired at top of `_run_deploy_sequence`; per-alias signals; sequential. Tests: test_deploy_lock_is_a_lock, test_ack_stop_spawns_deploy_thread.
- **AC9** PASS (post-merge path) — `_reboot_affected_agents` sets INTENT_DEPLOYING + save_state BEFORE emit; update_health/load_state DEPLOYING handling. **Boot-path TRD-drift, see below.**
- **AC11** PASS — confirmed: per-alias `compose.py deploy <alias>` does NOT write `.claude/settings.json`; the hook writes (_ensure_session_end_hook/_ensure_activity_hooks/_ensure_pause_hooks, compose.py L2265/2270/2274) live only in the `deploy-all` branch (L2200), not `deploy` (L2131). → #12519 stays a SEPARATE installer-managed workstream. Skill's finding accurate.
- **AC12** DS-audit — see TRD-drift items below.
- **CQ HARD GATE** PASS 5/5 — verifier-authored independent questions, fresh sonnet given ONLY the modified Case E text → all correct, zero anti-patterns. (Note: skill also authored `12912_spec.json` — CQ authoring is verifier's lane #9184; flagged to PM, non-blocking; I ran my own to restore independence.)

## TRD reconciliation items (AC12 — non-blocking for code; route to PM)
1. **AC6 §11 push-retry drift.** HARNESS-ARCH §11 (line 481) mandates push rejection
   "retries the deploy sequence … up to 2 times." Code does 0 retries (test
   test_push_rejection_recovers_immediately locks single-push). Code's reasoning is
   SOUND: after a local compose commit, `git pull --ff-only` cannot fast-forward a
   diverged branch, so the §11 retry-as-written is futile. The AC6 end-state guarantees
   (respawn + deploy-error + checksum-unadvanced) all hold. But code↔TRD still drift,
   unreconciled — the issue explicitly says "do not let code+TRD drift." Resolution =
   **PM amends §11** to match the (correct) shipped behavior. Skill must route this
   doc-change to PM as part of AC12.
2. **AC9 boot-drift intent-sequencing.** AGENT-RUNTIME §5.2 says set `intent=deploying`
   at emit time. The post-merge path does this; the boot-drift path defers to the
   ack-stop handler (which sets it synchronously before PID death — functionally
   equivalent: the agent only exits after emitting ack-stop). **Already disclosed by
   skill in the PR body as a TRD-clarification candidate to PM.** No further skill
   action; PM to reconcile §5.2 wording. Not a gap.

## No-regression
- #12912-specific: test_harness_deploy_12912.py (40) + test_event_catalog.py + test_harness_freshness_restart_e5.py → 78 passed; test_harness.py → 290 passed.
- Full static gate: **FAIL** on the one forbidden-token test above (the blocking finding). All other 4690 gated tests pass; 2 allowlisted known-failures (#10360) unchanged.
- Live-gh integration: 53 run, 2 environmental errors (test_status_flow raw `gh issue edit/view` on throwaway issues — not #12912 code).

## Disposition
pending-test → **in-progress** (role:skill). Fix the forbidden-token regression
(blocking) and route the §11 push-retry doc-reconciliation to PM (AC12). One-cycle fix.
