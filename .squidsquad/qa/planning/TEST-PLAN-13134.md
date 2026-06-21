# TEST-PLAN-13134 — reconcile /quit instructions to harness-reaper model

**Issue**: #13134 (type:issue, severity:medium, role:skill) — agent `/quit` instructions (Case E + self-restart) contradict shipped harness-reaper model (#13077).
**PR**: #13137, branch `squidsquad/task/13134`.
**Derived independently** from the issue's "Locked model" + "Required" sections — not from the PR diff.
**CQ**: **HARD GATE** (LLM-instruction change) — verifier-authored spec per #9184.

## Locked model to reconcile to (from issue)
- Agent on any cooperative exit: finish atomic unit, emit ack-stop/exit-42 signal, then **halt = cease output / end turn**. Agent does NOT (cannot) self-`/quit`.
- **Deploy-halt**: harness **actively force-kills** the halted process (reaps event_poll sidecar #12363) immediately, confirms death, then boots replacement (status="deploying" not covered by 60s net).
- **exit-42 / stop-requested**: same can't-self-`/quit`, but get the **60s force-kill net** (functional, slower). NOT instant. Accelerating = separate future decision, not in #13077.
- `/quit` must NOT be framed as load-bearing / canonical / "safety net should never fire."

## Acceptance criteria
- **AC1** Case E (event-mode-contract.md) stop-requested + deploy-signal reconciled to locked model.
- **AC2** self-restart.md reconciled (no "Self-Quit Protocol is canonical / should never fire" framing).
- **AC3** instructions.md Step 7 self-restart lede reconciled.
- **AC4** TRD reconcile consistent: HARNESS-ARCH §7.4/§7.1/§7 + AGENT-RUNTIME §5.2/§7.5/state-diagram — agree with sub-skills + each other.
- **AC5** prose-drift: docs ↔ shipped harness.py `_respawn_agent_process` consistent; no dangling refs; no residual load-bearing /quit framing.
- **AC6** CQ HARD GATE (verifier-authored): fresh agent understands halt=cease output + harness terminates; does NOT believe self-/quit is load-bearing.
- **AC7** consumption path: reconciled text reaches composed CLAUDE.md (instructions inlined; self-restart + event-mode-contract runtime-loaded via marker → reconciled source consumed).
- **AC8** no-regression: full static gate green.

## Execution method
1. Read source diffs (event-mode-contract.md, self-restart.md, instructions.md) — check vs locked model.
2. grep modified sources for residual load-bearing/canonical/should-never-fire /quit framing.
3. Read TRD diffs (HARNESS-ARCH, AGENT-RUNTIME) — cross-pair consistency.
4. Cross-check docs vs shipped harness.py `_respawn_agent_process` (active force-kill, `_DEPLOY_RESPAWN_PID_WAIT_S`, `FORCE_KILL_TIMEOUT_SECONDS`).
5. Author 13134_spec.json; run fresh sonnet given ONLY reconciled passages.
6. compose.py deploy + grep composed CLAUDE.md for reconciled text + absence of stale framing.
7. Full static gate (run_tests.py static).

## Pass condition
All ACs PASS with evidence; CQ 3/3; zero-gap; static gate green.
