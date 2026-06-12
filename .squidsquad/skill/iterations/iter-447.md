# Iteration 447 (cycles 1637-1638)

**Time**: 2026-06-12 18:08
**Type**: bug fix (high-priority operator report)

## Task: #11512 — thin_launcher forces loop mode at boot

### Root cause
thin_launcher.py:502 injected `/loop {interval}m execute one Ralph Loop cycle` as the spawned agent's literal first-turn prompt. The first turn ran the /loop skill instead of composed CLAUDE.md boot Step 1 (the harness-reachability probe), so every agent booted loop/polling mode even when the harness was up — event mode dead-on-arrival.

### Fix (option 1: mode-neutral spawn prompt)
- Replaced /loop spawn prompt with _SPAWN_PROMPT (mode-neutral boot trigger). Boot Step 1 now owns mode selection — single source of truth. Its POLLING block already self-schedules /loop, so the launcher injection was redundant + harmful. Rejected options 2/3 (launcher-side probe / conditional /loop): duplicate the harness probe in Python = parallel control path, HARNESS-ARCH forbids.
- Removed dead _get_interval (sole purpose was the /loop prompt).
- Rewrote #9725 unit (test_thin_launcher.py → TestSpawnPromptIsModeNeutral, 31 pass) + live (test_feat_9725...live.py, 3 pass) tests to the #11512 contract.

### Gates
- run_tests.py canonical gate: 54 OK.
- DS review (high blast radius): NO_FINDINGS, 5/5 invariants pass.
- 18 test_feat_9588 reds confirmed PRE-EXISTING (#11503 test-debt, moved boot-bootstrap.md) via stash.

### Outcome
PR #11518, transitioned pending-test. No review:human-required → QA auto-merge path. Already-running agents unaffected until respawn.
