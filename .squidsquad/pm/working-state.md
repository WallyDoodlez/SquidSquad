# Working State

- **Task**: Monitoring — multiple items pending verification
- **Status**: in-progress
- **Started**: 2026-04-05

## Pending QA Verification
- #107 (SKILL.md old BUG-[ROLE]-XXX IDs) — pending-test
- #108 (SKILL.md old FEAT-SKILL-XXX format) — pending-test
- #114 (SKILL.md PR branching old NNN IDs) — pending-test
- #115 (BRIEFING.md stale test suite constraint) — pending-test, closed by DM
- #116 (SKILL.md config template 0.9.0 + missing Aliases) — pending-test

## Open Bugs
- #117 (DM template not regenerated — no tracker.py) — approved, high priority

## Recently Shipped
- #67 (test framework) — 58 static tests
- #66 (deterministic script layer) — 5 Python modules
- #29 (agent aliases) — session naming, Co-Authored-By, config
- #94 (improvement scan bug gate)
- #71 (missing --remove-label in transitions)
- #55, #64, #65, #68, #69, #70, #95, #96 (various bug fixes)
- DM bugs: #56, #57, #59, #60, #62, #93

## Active Features
- #2 (README overhaul) — approved, DM pickup after bug gate clears
- #3 (going public) — on hold

## Key Context
- Script layer (#66) confirmed working for skill-lead — clean label transitions
- DM still on old template (bare gh commands) — #117 must ship first
- compose.py deploy command exists but DM template wasn't deployed
- DM filed #107, #108, #115, #116 improvement scan findings — all pending approval for non-DM items
- 58 static tests passing via pytest
