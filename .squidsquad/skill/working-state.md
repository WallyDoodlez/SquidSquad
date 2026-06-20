# Working State

- **Task**: none (between tasks). #12294 SHIPPED to verifier (pending-test). Next pickup: **#13032 (HIGH)**.
- **Updated**: 2026-06-20 (skill — event-mode, #12294 handed off)
- **Quiet Cycle Counter**: 0

## #12294 — DONE this session → pending-test (PR #13033)
Implemented dependency-free **C+A** (image-verified liveness). Branch `squidsquad/task/12294` pushed, **PR #13033**, transitioned in-progress→pending-test. Full static gate: 4787 passed, 0 failures. Two review passes folded (DS-c1 empty-image parity; Claude review DS-c3 blocker — image helpers made total so a ctypes fault can't abort the fleet health poll; write-back gated on intent=RUNNING).
- **process_utils**: `image_name_for_pid` + `is_claude_process_alive` (total; None-image → fall back to liveness = AC2-safe).
- **thin_launcher**: `_win32_all_procs()` factored; local mirrors; `_check_singleton` image-verified (recycled PID no longer defeats singleton).
- **harness.update_health**: image-verifies in-mem + .claude-pid PIDs (AC1/AC3); self-heals .claude-pid via new `reboot_agent.write_claude_pid` (gated intent=RUNNING). Whole block guarded (fault → treat-as-dead, not fleet-abort).
- **AC coverage**: AC1/AC3 full; AC2/AC4 covered for the realistic restart (harness persists claude_pid in .harness-state.json → restored + image-verified even with missing/stale .claude-pid + self-heal write-back). **Residual**: truly never-recorded orphan needs psutil → filed **#13034** (HUMAN DECISION). terminal_pid re-resolution ruled out (cmd /c start PID is dead/short-lived on Windows).

## NEXT: #13032 (HIGH, role:skill, open) — deploy-signal respawn no-op
Deploy-signal respawn no-ops when the halted agent's process stays alive (missing terminate-session handoff after ack-stop "deploy-halted" → harness respawn no-ops on a still-alive process). Pairs with #12294 (harness reliability). Pick up next.

## SECONDARY in-progress (parked)
- **#12451** (status-bar) S1+S3 on branch (PR #13024); S2 PARKED on PM CQ-AC via **#13031** (role:pm filed to wake PM). Resume S2 when PM lands the CQ-coverage AC.

## Gated / parked in-progress (externally blocked)
- **#12801** (Textual TUI action bar) — needs textual dep + interactive terminal.
- **#12493** (pipeline-sentinel HALT detection) — PR #12494 HELD pending §8.3 backstop (PR #12507 unmerged).
- **#12450** (installer unit-test strategy detect) — S3/S4 PM-gated.

## Other open candidates (not started)
- #12363 (orphaned claude.exe/event_poll accumulation — related to #12294/#13032 cluster), #11140 (composed CLAUDE.md header prose — CQ-gated), #10540 (DM batch-ship race), #12495/#12971/#12861/#12846/#12747/#12519/#11716 (lower).
- #12527 (foreign-repo installer smoke — interactive), #12492 (cutover flip — gated on #12460), #12271 (liveness umbrella — gated/sliced), #10690 (gated E7), #10686 (manual).

## Recurring meta-risk
Clone chronically behind origin (#12526 SHIPPED — launcher no longer rebases). Always `git pull --ff-only` before compose/commit.

## Improvement Scan
Status: eligible (idle). Last completed: (none — productive session).
