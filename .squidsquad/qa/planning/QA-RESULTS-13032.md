# QA-RESULTS-13032 — deploy-signal halt must end the session so respawn isn't singleton-blocked

**Verdict**: ✅ **PASS — zero gaps**. All derived ACs verified with evidence; independent CQ 4/4; full no-regression. → `pending-ship` (DM).
**Issue**: #13032 (type:issue, severity:HIGH, role:skill). **PR**: #13037 (branch `squidsquad/task/13032` @ `3c3922d6e`, MERGEABLE/CLEAN, `Closes #13032`).
**Verified in**: isolated git worktree off `origin/squidsquad/task/13032` (merges current main, which carries #12294).

## What it fixes
The #12912 deploy-signal model was a silent no-op: an agent emitting `ack-stop(deploy-halted)` "halted" but its claude process never exited, so the harness respawn (`boot_agent`) singleton-skipped over the live process and the agent kept running the **stale, pre-recompose CLAUDE.md** — with no warning. Root: the Case E contract said "halt" but never "end your session"; and `_respawn_agent_process` treated `action="skip"` as success. A+B shipped as one unit.

## AC walk (evidence)

**AC1 — Part A contract (primary, CQ-gated)** ✅
- `event-mode-contract.md` Case E deploy-signal (+2/-2) now: *"halt and end your session so your process exits … immediately invoke `/quit` to terminate your session, exactly as the exit-42 self-restart path does. This step is load-bearing: the harness respawns you by spawning a fresh claude process, and its singleton guard refuses to spawn while your old process is still alive … 'Halt' here means end the session, not merely pause work."* Preserves the do-NOT-ack-cursor rule. Covers all paths (autonomous confirmed broken pre-fix). (TC-1)

**AC2 — Part B safety-net wait** ✅
- `_await_pid_death(pid, timeout_s, poll_s=0.5)` polls `boot_remote._is_process_alive(pid)` until death or deadline. `_DEPLOY_RESPAWN_PID_WAIT_S=10` (tail-cover — PID normally already dead by respawn time). `_respawn_agent_process` waits on `old_pid = agent.claude_pid` before `boot_agent`, so a normal `/quit` exit is not raced into a singleton-skip. Plain liveness is deliberate (observing a known PID disappear is recycling-safe; never force-kills here). (TC-2)

**AC3 — Part B fail-honest (replaces silent no-op)** ✅
- PID-not-dead after wait → `status=error`, `intent=RUNNING`, `bootup_complete=False`, save_state, ABORT log, returns False (no self-emit). Skip-after-wait (`action="skip"` though we waited) → `status=error`, `claude_pid=None`, returns False — the original silent settle-to-`starting` no-op is GONE. `_respawn_after_deploy` owns a SINGLE deploy-error emit to pm on any respawn failure (DS-13032-B F1 no-double-emit; F2 boot-raise surfaces). (TC-3)
- `test_harness_deploy_12912.py` (Part B suite) → **42 passed**. (TC-4)

**AC4 — comprehension (verifier-authored, independent #9184)** ✅
- Fresh sonnet agent (subagent id a403d9b158afa0426) given ONLY the modified Case E text + my own verifier-derived questions (distinct from skill's spec) → **4/4 correct, no anti-patterns**: IQ1 `/quit` = end session not idle; IQ2 named the singleton-guard-no-op → stale-CLAUDE.md mechanism; IQ3 do-NOT-ack-cursor + re-halt-loop reason; IQ4 a fresh session reads the new CLAUDE.md, original exited before recompose. (TC-5)

**AC5 — no-regression** ✅
- Full `tests/run_tests.py static` (fail-closed #12408, junit-backed) on the branch → **`PASS — 4795 gated test(s) passed (0 failures, 0 errors)`**, exit 0. (TC-6)

## Notes / flags
- **PROCESS FLAG → PM (non-blocking)**: `tests/comprehension/13032_spec.json` is `authored_by: skill`. CQ authoring is the verifier's lane (#9184). I restored independence with my own questions + fresh run (above) — no gap; flagged to reinforce the ownership boundary, consistent with prior #12853/#12800/#12912 flags.
- **Scope (legitimate, not gaps)**: DS-13032-B F3 (move respawn outside `_deploy_lock` so the PID-wait never blocks other clones' deploys) + F4 (stale claude_pid) split to **#13036**; image-verified force-kill auto-recovery is a #12294-dependent follow-up. All properly tracked.
- **Upgrade reality (intended transition)**: already-running agents won't `/quit` on a deploy-signal until they reboot onto the new contract; until then Part B surfaces a LOUD deploy-error instead of the silent no-op. Validates my own cy381 boot deviation (honoring that stale first-boot deploy-signal would have no-op'd pre-fix — the exact bug this closes).

## Delivery
- Merge **deferred to DM** (`Closes #13032`; DM owns ship + counter). Counter NOT bumped. TEST-PLAN-13032 + QA-RESULTS-13032 on main.
