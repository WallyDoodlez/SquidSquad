# TEST-PLAN-12912 — Phase 2 of #12895: deploy-signal recompose model

**Derived independently** from the issue AC list + the authoritative merged TRDs
(`docs/HARNESS-ARCH.md` §7.1/7.3/7.4/7.5/7.6/10/11, `docs/AGENT-RUNTIME.md`
§5.2/7.8/8.1/8.2/8.6/9.2) — NOT from the worker's PR diff. PR #12926, branch
`squidsquad/task/12912`. Verifier: qa. type:task/high/role:skill.

Blast radius: HIGH (fleet-wide agent event-loop halt branch + harness deploy
sequence + boot-time compose retirement). Authoritative spec is doc-first/locked
→ verify code against TRD prose, not just code self-consistency (AC12).

## Method
- Isolated worktree on the PR branch (`D:\Dev\Dev\sq-12912-verify`) to avoid the
  prior-cycle working-state-revert hazard.
- Run branch test suites + full static gate (no-regression).
- Independent TRD↔code consistency audit (AC12) — sonnet subagent, findings
  independently re-verified by reading TRD §11 / §5.2 text myself.
- Independent comprehension test (CQ HARD GATE) — verifier-authored questions,
  fresh sonnet given ONLY the modified `event-mode-contract.md` Case E text.

## Test cases (one per AC)
- **TC1 (AC1)** — drift → harness emits `deploy-signal` (`event_type="deploy-signal"`)
  to affected alias(es); agent care filter branches on `event_type` to halt branch.
  Evidence: `event_catalog.py` deploy-signal EMITTED; `harness.py` _reboot_affected_agents
  + _emit_boot_deploy_signals payload; event-mode-contract Case E branch; tests
  test_emits_deploy_signal_to_affected_running_agent / test_deploy_halted_branch_exists.
- **TC2 (AC2)** — agent emits `ack-stop(result="deploy-halted")`, halts, does NOT
  ack-cursor the signal, no work pickup / no subloop. Evidence: Case E text + CQ;
  harness ack-stop handler gates on result=="deploy-halted".
- **TC3 (AC3)** — clone behind origin → composed `CLAUDE.md` matches ORIGIN
  (pull-first), not stale local. Evidence: _run_deploy_sequence orders
  `pull --ff-only origin main` BEFORE `compose.py deploy`; Phase-1 (#12906) guard
  is a subset that stays.
- **TC4 (AC4, infinite-loop guard)** — harness advances cursor past the deploy-signal
  before respawn; respawned drain does not re-process it. Evidence:
  test_advances_cursor_past_deploy_signal; advance done up-front in _run_deploy_sequence
  regardless of success/failure.
- **TC5 (AC5/AC10)** — boot does NOT run `compose.py deploy-all` locally; emits
  deploy-signals; agent boot does not recompose. Evidence:
  `compose_freshness.check_and_repair(detect_only=True)`; test_boot_path_is_detect_only;
  test_detect_only_drift_does_not_run_compose; manifest 229→235.
- **TC6 (AC6)** — each failure mode (pull non-ff/conflict, compose error, push
  rejection) → respawn on existing CLAUDE.md + deploy-error to pm + checksum NOT
  advanced. Evidence: test_pull_failure_recovers_without_checksum_bump,
  test_compose_failure_recovers, test_push_rejection_recovers_immediately.
  **NOTE: §11 push-rejection drift — see Findings.**
- **TC7 (AC7)** — loop-mode agent does NOT consume deploy-signal; picks up updated
  CLAUDE.md at next cycle_pre.py pull. Evidence:
  test_event_contract_states_loop_mode_does_not_consume,
  test_polling_fragments_have_no_deploy_signal_handling, Case E loop-mode bullet.
- **TC8 (AC8)** — per-alias signals + sequential per-clone deploy (`_deploy_lock`);
  no push race. Evidence: _deploy_lock acquired at top of _run_deploy_sequence;
  test_deploy_lock_is_a_lock, test_ack_stop_spawns_deploy_thread.
- **TC9 (AC9, intent-sequencing)** — intent=deploying set before agent halts; deploy-
  halt PID death not misread as crash. Evidence: _reboot_affected_agents sets
  INTENT_DEPLOYING + save_state BEFORE emit; update_health DEPLOYING branch; load_state
  reset. **NOTE: boot-drift path drift — see Findings.**
- **TC10 (AC10)** — see TC5; manifest + compose consumption.
- **TC11 (AC11, #12519 fold)** — per-alias `compose.py deploy <alias>` does NOT write
  `.claude/settings.json` (only `deploy-all` does). Evidence: compose.py — hook writes
  (_ensure_session_end_hook/_ensure_activity_hooks/_ensure_pause_hooks) only in
  `deploy-all` branch (L2265/2270/2274), not `deploy` branch (L2131). → #12519 stays
  SEPARATE installer-managed workstream. CONFIRMED.
- **TC12 (AC12, DS-audit / prose-drift)** — code vs merged TRDs. Independent audit +
  my own TRD reads. **Two drifts found — see Findings.**
- **CQ HARD GATE** — comprehension of event-mode-contract Case E (LLM-consumed).

## Findings to adjudicate (see QA-RESULTS for verdict)
1. AC6 push-rejection: TRD §11 mandates "retry up to 2×"; code does 0 retries
   (sound DS reasoning: `--ff-only` re-pull of a diverged branch is futile after a
   local compose commit). Unreconciled code↔TRD drift; resolution = PM §11 doc-amend.
2. AC9 boot-drift intent-sequencing: TRD §5.2 says set intent at emit; boot-drift path
   sets it in the ack-stop handler (functionally equivalent; PID dies only after
   ack-stop). Disclosed by skill as TRD-clarification candidate.
