# QA-RESULTS-11745 — Agent terminal not closed on kill → leftover terminals accumulate

**Verifier**: verifier-lead (qa)
**Date**: 2026-06-13
**PR**: #11811 (squidsquad/task/11745 → main)
**Branch verified**: squidsquad/task/11745 @ 62945bb4c
**Verdict**: **PASS** (Windows deliverable, operator-ratified Option A) + macOS/Linux scope flag for PM

## Scope (operator-ratified, 2026-06-13)
Option A = self-closing console via `cmd /c start` — inherently Windows. The AC lists cross-platform,
but the operator explicitly ratified the Windows-specific approach; that scopes THIS PR to Windows
(the "immediate pain"). macOS/Linux orphan handling is follow-up. Per the zero-gap gate, an explicit
operator scope decision is a valid override — Windows-only here is sanctioned, not a waved gap.

## AC Walk

### AC: kill/stop agent → terminal closes, no leftover (Windows primary)
**PASS.** _spawn_windows (boot_remote.py:382) now spawns `cmd /c start "title" /D <dir> <inner>`:
  - `start <program>` gives the console window a lifetime equal to the spawned process — the OS
    closes it on ANY exit code (vs the old `wt new-tab`, whose closeOnExit=graceful kept the tab on
    a killed/non-zero exit → orphan accumulation; microsoft/terminal#15747 = no wt flag to override).
  - The pwsh path drops `-NoExit` (boot_remote.py:401) — `-NoExit` pinned the window open forever,
    itself a guaranteed orphan source.
  - Title is QUOTED (`cmd /c start "squidsquad-<role>"`) — DS Finding 1: an unquoted no-space first
    token is taken by START as the program to run, so the agent would never launch. Critical, fixed.

### Regression test (AC permits "regression test OR documented manual verification" — BOTH provided)
**PASS — unit (command construction):** tests/test_boot_remote.py::TestSpawnWindows11745 — 6/6:
  - test_thin_spawns_self_closing_cmd_start — asserts `'cmd /c start "squidsquad-skill"' in cmd`
    (title quoted), Popen gets a STRING, role arg last
  - test_does_not_use_wt_new_tab, test_ps1_path_drops_noexit (the orphan source removed),
    test_detached_creation_flags_preserved, test_clone_root_with_spaces_is_quoted, test_spawn_failure_returns_false

**PASS — documented live mechanism verification (this verifier, Windows):** spawned the exact fix
pattern with a transient inner command — `cmd /c start "qa-probe-11745" /D <tmp> cmd /c "echo > marker"`.
Result: marker written (the window RAN its command → title parsed as title, not misexec'd — DS Finding 1
mechanism validated live) and the inner `cmd /c` self-exited (window self-closes; no `-NoExit` pin).
A real agent spawned via this pattern therefore gets a window whose lifetime is the agent process;
killing the agent closes the window — inherent to `start <process>`.

## Test Execution
- `pytest tests/test_boot_remote.py -k Spawn/11745/windows/terminal` → 13 passed, 1 skipped.
- Live self-close probe → marker written + self-exit confirmed.
- `python tests/run_tests.py static` → EXIT=0, 2337 passed / 0 failed.
- skill full suite green; DS re-review NO_FINDINGS (after fixing the title-quote bug).

## Scope flag for PM (NOT an AC failure — does not block the Windows ship)
macOS (Terminal.app window-close) and Linux (tmux stop-time kill-session) orphan handling are
follow-up, tracked ONLY in #11745's comments ("will file if you want it tracked separately").
#11745 is type:issue → shipping auto-closes it and the cross-platform remainder drops off the tracker.
Recommend PM file a follow-up issue for macOS/Linux terminal-orphan handling before #11745 closes.
(Same preservation pattern flagged on #11723.)

## Verdict
**PASS → pending-ship** for the Windows deliverable. DM ships PR #11811. PM to preserve macOS/Linux follow-up.
