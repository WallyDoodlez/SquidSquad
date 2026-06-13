# DM Iteration 417 — 2026-06-13 16:15–16:18

**Wake mode**: POLLING (harness DOWN). First scan showed 0 pending-ship, but qa cycle-1085 had just transitioned #11745 → pending-ship (git push landed seconds before the label propagated). Re-scan / direct issue check found it.

## Shipped 1 item (local-merge #10540)
- **#11745** (role:skill) — PR #11811. _spawn_windows uses `cmd /c start "squidsquad-<role>"` so the OS closes each agent console window on ANY exit code — leftover terminals no longer accumulate. Drops orphaning wt-tab + legacy `pwsh -NoExit`. Operator-ratified Option A. Verifier PASS, win32-guarded TestSpawnWindows11745. Counter 12→13.

## Ship mechanics
- base=main, not draft, no delivery:skip, merge-tree CLEAN. ff-first pull (clean), merge --no-ff, push. PR auto-MERGED.
- Harness-script (boot_remote.py) — no compose/reboot; operator restart picks it up. Counter set via `config.py set shipped-since-bump 13`.

## Flagged to PM
- #11745 macOS (Terminal.app close) / Linux (tmux kill-session) orphan handling = follow-up; PM to file before auto-close (verifier preservation ask, same as #11723).

## Bump gate
- Counter **13/10**. HELD ([[feedback_bump_requires_pm_signal]]). Operator flagged cycles 415 & 416; no green-light yet.

## Learning captured
- pending-ship scan can race qa's label transition — added re-scan/direct-check note to working-state. (Not a vault note; cycle-local tactic.)

## Carried
- #10540 OPEN (DM-domain, PM routing). #11600 OPEN (clone-reg half). #11723 Parts 1&3 + #11745 macOS/Linux (PM follow-ups). pending DM approvals #8702/#7447/#9933. Harness still down.
