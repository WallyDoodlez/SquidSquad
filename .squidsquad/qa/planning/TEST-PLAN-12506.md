# TEST-PLAN #12506 — Event-mode periodic driver (improvement-subloop dormancy fix)

**Derived**: 2026-06-18 13:41 by verifier (qa), independently from the 12 ACs in the issue body + the LOCKED design AGENT-RUNTIME §8.6.1 — NOT from the worker's diff.
**Issue**: #12506 (type:issue, severity:high, role:skill). PR #12812 (branch `squidsquad/task/12506`).
**Design contract**: AGENT-RUNTIME §8.6.1 (PR #12518, merged 06888b854) — driver lazy-armed on first idle, bounded burst, re-arm on re-idle, no harness change, event-mode scope (pm/skill/dm).

## Verification surfaces
- `references/scripts/subloop_driver.py` (new deterministic state machine) + `tests/test_subloop_driver_12506.py`.
- `references/sub-skills/common-events/idle-cooldown-loop.md` (rewritten step-5 → driver-tick model).
- `.squidsquad/config.md` `## Improvement Scanning` (`Cool-Down: 30m` + `Idle Scan Burst: 3` — landed direct-to-main per #11511 guard; PR branch carries the default path).
- `references/scripts/config.py` + `wizard.py` (new-install wiring) + `tests/test_config_functions.py`.
- DS-review records (AC12). compose deploy-all references (AC9). harness.py diff (AC8). installer-files.txt (AC11).

## Test cases (one per AC; live-instance CLI walk + suite + comprehension)

- **TC1 (AC1 lazy enable):** fresh alias → `arm` returns `action=schedule`; second `arm` returns `already-armed` (idempotent, no reset). A busy agent never calls `arm` (only invoked at idle/drained per sub-skill Step A). PASS criterion: schedule-once semantics.
- **TC2 (AC2 idle scan fires):** armed + `tick --drained true` with `last_run=null`/throttle elapsed → `action=scan`. Sub-skill Step A arms on first idle, Step B tick fires scan — no dependence on a forge event. PASS criterion: scan fires from timer path alone.
- **TC3 (AC3 bounded):** `record-scan` ×3 → 3rd returns `at_cap:true`; subsequent `tick` (throttle elapsed) → `action=cancel reason=at-cap`. PASS criterion: burst capped at `Idle Scan Burst`=3, driver cancels.
- **TC4 (AC4 re-arm + reset):** after `cancel`, `reidle` → `action=schedule rearmed:true scan_count=0`; `last_run` preserved so throttle still holds (tick right after reidle within cooldown → `wait`, not `scan`). PASS criterion: counter reset + driver re-armed without bypassing throttle.
- **TC5 (AC5 Monitor coexistence / forgotten-work):** `tick --drained false` → `action=absorb-work` (driver doubles as missed-nudge safety net). Sub-skill Atomicity §: cron tick treated like a mid-task NUDGE, absorbed by next forge-read, no race (fires as scheduled tool-invocation, not on Monitor stdin). PASS criterion: queued work absorbed, no double-processing.
- **TC6 (AC6 config consumption):** `status` shows `burst:3, cooldown_minutes:30` from defaults (branch config); `cooldown_minutes()` tolerates `30m` (unit test) and bare `30` (legacy). PASS criterion: reads keys, graceful default 3.
- **TC7 (AC7 sub-skill reconcile):** idle-cooldown-loop.md no longer claims Monitor delivers fixed cadence (line 14 states event_poll silent on empty poll); names §8.6.1 driver as cadence source; KEEPS NUDGE branch (Step C) + cooldown eligibility (Step B); documents `Idle Scan Burst` (Cool-Down Configuration §). PASS criterion: all four conditions met.
- **TC8 (AC8 no harness change):** `git diff origin/main...HEAD` contains no `harness.py`. PASS criterion: harness.py untouched.
- **TC9 (AC9 composes):** `→ run sub-skill: idle-cooldown-loop` present in all 4 composed CLAUDE.md (runtime-loaded fragment; body not inlined by design). PASS criterion: reference resolves to updated source in every event-mode composed output.
- **TC10 (AC10 comprehension — HARD GATE):** fresh agent given ONLY idle-cooldown-loop.md answers "periodic self-wake driver scheduled at first idle re-enters the loop on a timer," NOT "Monitor wakes me on a cadence." Spec: `tests/comprehension/12506_spec.json`. PASS criterion: all CQs answered from file alone, driver (not Monitor) identified as cadence source.
- **TC11 (AC11 installer-files):** any NEW runtime file the shipped sub-skill depends on must be in `references/installer-files.txt` (the npx-squidsquad fetch manifest). PASS criterion: `subloop_driver.py` present in manifest.
- **TC12 (AC12 DS-review):** DS-review record exists for the high-blast-radius wake-loop change. PASS criterion: DS-REVIEW-12506-*.md present.
- **TC-REG (no regression):** `python tests/run_tests.py` green; targeted `pytest` of driver+config tests green. PASS criterion: suite OK, no new failures.
