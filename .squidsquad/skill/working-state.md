# Working State

- **Task**: picking up **#12409 (HIGH)** — qa slow event-mode reboot loop + inert-boot; #12244 backoff misses slow loops. RCA next.
- **Updated**: 2026-06-20 (skill — event-mode; #12294 SHIPPED, #13032 pending-test)
- **Quiet Cycle Counter**: 0

## DONE this session (2026-06-20)
- **#12294 SHIPPED + CLOSED** — .claude-pid authoritative across harness restart (image-verified liveness C+A). PR #13033 merged to main. Residual psutil orphan re-adoption → **#13034** (human decision). Now on main: `process_utils.is_claude_process_alive` / `image_name_for_pid` available.
- **#13032 pending-test** — deploy-signal halt must END session (/quit) so respawn isn't singleton-blocked. PR #13037 (branch merges main incl. #12294; gate 4795 pass, CQ 13032 3/3). Part A contract + Part B harness respawn PID-death wait + honest-fail. DS-13032-B folded (single emit, 10s wait). F3 (respawn outside _deploy_lock) + F4 (refresh claude_pid post-spawn, pre-existing) → **#13036**.

## NEXT (in progress): #12409 (HIGH, role:skill)
qa was stable event-mode ~4h then degraded: (1) SLOW reboot loop — 4 auto-reboots in ~18min, each >60s lifetime so #12244 fast-death breaker (≥3 deaths <60s) MISSED it; (2) inert/zombie final respawn — bootup_complete=false 11+min, PID-alive so no further reboot (same class as #10855). PM pinned qa to loop mode (hybrid: skill/dm event, qa loop). Two gaps: (a) #12244 backoff doesn't catch slow loops; (b) inert-boot not detected by PID-liveness. Likely ties to #12271 progress-liveness (shadow data / cutover). RCA needed: read the issue fully + crash-loop backoff + progress_liveness + bootup_complete handling. NOTE: #12271 progress-liveness is OBSERVATIONAL/shadow only today — cutover gated. So inert-boot detection may need either the cutover or a bootup_complete-timeout reboot.

## SECONDARY in-progress (parked)
- **#12451** (status-bar) S1+S3 on branch (PR #13024); S2 PARKED on PM CQ-AC via **#13031**. Resume S2 when PM lands the CQ-coverage AC.

## Gated / parked (externally blocked)
- **#12801** (Textual TUI) — needs textual dep + interactive terminal.
- **#12493** (pipeline-sentinel HALT) — PR #12494 HELD pending §8.3 backstop (PR #12507 unmerged).
- **#12450** (installer unit-test strategy) — S3/S4 PM-gated.

## Other open candidates
- #11600 (HIGH) — prev verified-resolved + recommended close; still open (PM disposition pending; re-verify if picked up).
- #12495/#12854/#12363/#11140/#10540 (medium); #12971/#12861/#12846/#12747/#12519/#11716 (low).

## Recurring meta-risk
Clone chronically behind origin. Always `git pull --ff-only` before compose/commit. Use `git -c credential.helper='!gh auth git-credential' push` (manager helper wedges).

## Improvement Scan
Status: eligible (idle). Last completed: (none — productive session).
