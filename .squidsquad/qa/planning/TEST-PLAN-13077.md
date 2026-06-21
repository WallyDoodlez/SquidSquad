# TEST-PLAN-13077 — Harness actively force-kills deploy-halted agent (cannot self-/quit)

- **Issue**: #13077 (type:issue, severity:high, role:skill) — Deploy-halt/exit-42 respawn waits for agent self-`/quit`, but the LLM agent cannot execute `/quit` → harness must actively terminate the process.
- **PR**: #13084, branch `squidsquad/task/13077`, HEAD `e8b7cdd35` (2 commits). Files: `references/scripts/harness.py` (+60/-42), `tests/test_harness_deploy_12912.py` (+38/-12).
- **Derived**: 2026-06-20 23:50. Issue has no explicit AC list (bug); ACs derived independently from the **LOCKED operator ruling** (issue body + PM refinement comment 2026-06-21) — *harness-as-reaper*: on `ack-stop(deploy-halted)`, after pull→compose→commit→push, the **harness** actively terminates the agent process then respawns. Agent responsibility ends at emit `ack-stop` + cease work; NO agent self-`/quit`, NO agent self-taskkill on the canonical path.
- **Classification**: deterministic harness code → **NO CQ** (no LLM-consumed instruction change in this PR). Doc reconcile (Case E / self-restart.md / HARNESS-ARCH / AGENT-RUNTIME still say "/quit") is explicitly **PM-side** per the issue body + PM comment → out of scope for this code verification.
- **Method**: isolated worktree `D:/Dev/Dev/qa-wt-13077` on the branch HEAD (avoids working-state-revert hazard); targeted module + full fail-closed static gate + an **independent runtime probe** of `_respawn_agent_process` (my own mocks, not the PR's test assertions).

## Acceptance criteria (derived)

| AC | Criterion | Verification |
|----|-----------|--------------|
| AC1 | On deploy respawn, if the old claude PID is alive, the harness **actively force-kills** it via `reboot_agent._kill_process(old_pid)` — does NOT passively wait for a self-`/quit` that never comes. | Independent probe S1/S2: `_kill_process(4242)` invoked. Diff: passive `_await_pid_death`-then-abort replaced with `_is_process_alive`→`_kill_process`. |
| AC2 | After the kill, the harness **confirms death** (`_await_pid_death`) before `boot_agent` — never boots over a live PID (singleton guard would no-op the respawn → strand on stale CLAUDE.md). | Probe S1 ordering: kill **then** boot. `TestAwaitPidDeath` 3/3. |
| AC3 | If the force-kill fails (PID still alive after `_DEPLOY_RESPAWN_PID_WAIT_S`), respawn **aborts honest**: status=error (in is_dead), intent=RUNNING, bootup_complete=False, boot_agent NOT called, caller owns the single deploy-error emit (no double-emit). | Probe S2: returns False, status=error, no boot, no emit. `test_old_pid_survives_force_kill_aborts_respawn`. |
| AC4 | If the old PID is already gone, **skip the kill** and boot normally. | Probe S3: no kill, boot, status=starting, True. `test_old_pid_already_dead_skips_kill_and_boots`. |
| AC5 | The kill reaps the Monitor-spawned `event_poll` sidecar (process **tree**/group kill, #12363), not just the bare claude PID. | `reboot_agent._kill_process` body: Windows `taskkill /F /T`, POSIX `killpg` with own-group safety. |
| AC6 | DS-REVIEW Finding 1 (severity:error) resolved: the under-patched recovery test (`test_recovery_path_emits_single_deploy_error_no_double`) now mocks `_is_process_alive`/`_kill_process` so the force-kill block actually executes (was falling through to the boot_agent-raise path), and asserts `boot_agent` is never called over a live PID. | Test diff + inline comment citing #13077 DS Finding 1; module 43/43 green. |
| AC7 | No regression across the suite. | `run_tests.py static` fail-closed. |
| AC8 | Both helpers resolve at runtime (no AttributeError on the real, non-mocked deploy path). | `boot_remote._is_process_alive` = `process_utils.is_process_alive`; `reboot_agent._kill_process` callable — both confirmed via live import. |

## Scope deferrals (legit follow-ups, NOT gaps)

- **exit-42 self-restart + stop-requested paths**: PM comment says "apply the same model… confirm in RCA"; issue body says "likely yes" as a follow-up. Those paths already get the 60s force-kill safety net (functional, slower) — accelerating them is a separate PM decision, flagged by skill. Out of PR #13084 scope.
- **Doc reconcile** (Case E, self-restart.md, HARNESS-ARCH §7.1/§7.4, AGENT-RUNTIME §5.2 still instruct "/quit"): explicitly PM-side per issue + PM comment.
- **DS-13032-B F3** (move respawn outside `_deploy_lock` so the wait never blocks other clones): pre-existing tracked follow-up, noted in the `_DEPLOY_WINDOW_SECONDS` comment.
