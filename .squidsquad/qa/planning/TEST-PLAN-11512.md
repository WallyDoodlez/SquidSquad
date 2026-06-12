# TEST-PLAN-11512 — thin_launcher mode-neutral spawn prompt

**Issue**: #11512 (type:issue, severity:high, role:skill) — thin_launcher hardcodes `/loop` spawn prompt → agents always boot loop mode, event mode never reached.
**PR**: #11518 (`squidsquad/task/11512` → main)
**Derived from**: issue body "Expected" section (independent of worker code). Bug = auto-approved.

## Acceptance Criteria (verifier interpretation of "Expected")

- **AC-1**: The launcher's spawn prompt must NOT force loop mode — the spawned command contains NO `/loop` directive.
- **AC-2**: Mode selection remains with composed boot Step 1 — the spawn prompt instructs the agent to run Step 1 / probe harness reachability and defer mode choice to the probe.
- **AC-3**: The `/loop`-only support code (`_get_interval`) is removed (dead once the `/loop` prompt is gone) with no dangling callers.
- **AC-4** (comprehension): A fresh agent reading the new spawn prompt correctly understands it must probe harness reachability first and NOT pre-commit to loop mode.
- **AC-5** (regression/no-stall): existing thin_launcher unit + live tests pass; neither wake mode stalls (event→Monitor, polling→Step1 self-schedules /loop).

## Test Cases

| TC | AC | Method | Expected |
|----|----|--------|----------|
| TC-1 | AC-1 | Inspect spawned cmd (unit `TestSpawnPromptIsModeNeutral`) | no arg starts with `/loop` |
| TC-2 | AC-1/2 | Read `_SPAWN_PROMPT` content | mode-neutral; names Step 1 + probe; "do not pre-commit to a mode" |
| TC-3 | AC-3 | `hasattr(thin_launcher,'_get_interval')` + grep callers | False; zero callers |
| TC-4 | AC-5 | Run `tests/test_thin_launcher.py` | all pass |
| TC-5 | AC-5 | Run `tests/test_feat_9725_spawn_loop_registration_live.py` | all pass |
| TC-6 | AC-4 | Fresh-agent comprehension on `_SPAWN_PROMPT` + boot Step 1 excerpt | agent says probe-first, no loop pre-commit |
| TC-7 | AC-5 | Canonical gate `run_tests.py` | green (note #11394 static-gate state) |

## Notes
- Live full end-to-end (spawn agent w/ harness up → arms Monitor) is the ideal but requires a real spawn; covered indirectly by TC-1/TC-2 (command shape) + TC-6 (comprehension). Flag if a true live spawn is HUMAN-REQUIRED.
- Pre-existing 18 `test_feat_9588` reds attributed by skill to #11503 test-debt (boot-bootstrap.md move) — confirm independent of this change.
