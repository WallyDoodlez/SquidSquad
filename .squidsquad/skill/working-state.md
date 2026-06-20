# Working State

- **Task**: none (between tasks). Three harness fixes delivered this session. No open HIGH items remain in the skill queue.
- **Updated**: 2026-06-20 (skill — event-mode; 3 harness fixes shipped/handed-off)
- **Quiet Cycle Counter**: 0

## DELIVERED this session (2026-06-20) — harness reliability cluster
1. **#12294 SHIPPED + CLOSED** — .claude-pid authoritative across harness restart (image-verified liveness C+A). PR #13033 merged. `process_utils.is_claude_process_alive` / `image_name_for_pid` now on main. Residual psutil orphan re-adoption → **#13034** (human decision).
2. **#13032 pending-test** — deploy-signal halt must END session (/quit) so respawn isn't singleton-blocked. PR #13037 merged to main. Part A contract (CQ 13032 3/3) + Part B respawn PID-death wait + honest-fail. Follow-ups (respawn outside _deploy_lock F3 + refresh claude_pid post-spawn F4) → **#13036**.
3. **#12409 pending-test** — frequency-based slow reboot-loop breaker (lifetime-agnostic, complements #12244). PR #13039. Asks 2/3 routed → #12271 / #12363; inert-framing → #12820.

All three: full static gate 0 failures; DS/Claude review cycles folded per commit.

## SECONDARY in-progress (parked)
- **#12451** (status-bar) S1+S3 on branch (PR #13024); S2 PARKED on PM CQ-AC via **#13031**. Resume S2 when PM lands the CQ-coverage AC.

## Gated / parked (externally blocked)
- **#12801** (Textual TUI) — needs textual dep + interactive terminal.
- **#12493** (pipeline-sentinel HALT) — PR #12494 HELD pending §8.3 backstop (PR #12507 unmerged).
- **#12450** (installer unit-test strategy) — S3/S4 PM-gated.

## NEXT actionable (open, non-urgent — pick up next session w/ fresh budget)
Medium: **#12363** (orphan claude/event_poll accumulation — same harness-reliability cluster; now can use #12294 image-verify for safe kills), **#11140** (composed CLAUDE.md header orientation prose — CQ-gated), **#10540** (DM batch-ship race), **#12495** (medium), **#12854** (medium — part-1 was folded into #12451).
Low: #12971/#12861/#12846/#12747/#12519/#11716.
Pending (human-gated): #302, #303 (low).

## Recurring meta-risk
Clone chronically behind origin. Always `git pull --ff-only` before compose/commit. Push via `git -c credential.helper='!gh auth git-credential' push` (manager helper wedges silently). Feature work on `squidsquad/task/<n>` branch; working-state commits direct-to-main (#11511 guard).

## Improvement Scan
Status: eligible (idle). Last completed: (none — productive session).
