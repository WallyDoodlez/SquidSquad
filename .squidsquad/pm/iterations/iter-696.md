# Iteration 696 — cycle 2343/2344

**When**: 2026-06-13 01:01
**Mode**: inline/loop (operator-driven incident response + 1 Ralph cycle)
**Type**: incident root-cause + ship + bug-filing

## Reboot-loop root cause — FOUND + SHIPPED
- ROOT CAUSE: `.squidsquad/.harness-port` is gitignored → absent in every sibling clone. On main, event_poll `_discover_port()` returned None on missing file → poll/main exit 2 → Monitor dies → agent session ends (#9742) → harness #4949 auto-reboots → ~15-20s loop.
- Context-pressure exit-42 RULED OUT (marker "8" = 8% used vs 70% threshold; cycle_pre.py:342). No second mechanism — prior hypothesis was wrong.
- "#11601 committed but loop continued" explained: committing on a branch ≠ running it; #11601 was never merged to main.
- FIX = #11601 (None→7373 fallback + parent-walk). Shipped to main: cleaned branch to fix+tests only (dropped incidental pm/working-state.md churn), PR #11639, merged 04:49Z.
- Verified live: skill rebooted clean, pid 22968 stable across samples, bootup=True, current-state idle. No loop.

## QA "wrong realm" (#11600) — diagnosed + routed
- Three-name drift for one agent: alias=`qa` (harness/boot lookup), `.local-config` key=`verifier`→../SquidSquad-verifier (nonexistent), real clone=../SquidSquad-qa (exists, unregistered).
- `_get_clone_path('qa')` misses → `local.get(role, REPO_ROOT)` (boot_remote.py:163) silently returns PM clone.
- Operator directive: NO fallback — must FAIL and not start. Filed #11640 (role:skill): `_get_clone_path` must raise on unregistered/missing-path clone; all spawn paths refuse + surface error; never boot into REPO_ROOT.
- #11600 retains the registry/identity half (qa→verifier rename). QA stays stopped (correct) until both land.

## Pipeline (clean)
- pending-test=1 (#10855, role:skill) — parked on QA-down, not a stall.
- in-progress=4: #11503 (skill), #11092/#11053/#9968 (pm design items).
- pending-ship=0. dm/pm/skill healthy; qa contained (no process in PM clone).

## Watch next cycle
- Confirm skill resumes productive work (picks up #11503/#11640) on its next tick; verify whether it's loop vs event mode (no event_poll observed).
- Operator decision pending: scope qa→verifier rename (#11600) now, or park QA.
