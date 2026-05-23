# QA Improvement Scan History

## Scan — 2026-04-13 15:05

- **Files scanned**: references/scripts/health_check.py, references/scripts/cycle.py, references/scripts/vault_check.py, references/scripts/vault_remember.py, references/scripts/diagnostics.py
- **Findings**: #886 (health_check.py no unit tests), #887 (cycle.py no unit tests)
- **Items rejected by human**: none

## Scan — 2026-04-13 17:34

- **Files scanned**: references/scripts/vault_check.py, references/scripts/config.py, references/scripts/tracker.py (coverage check), references/scripts/diagnostics.py
- **Findings**: #895 (vault_check.py no unit tests), #896 (config.py thin test coverage — 9/467)
- **Items rejected by human**: none

## Scan — 2026-04-14 00:04

- **Files scanned**: references/scripts/vault_remember.py, references/scripts/diagnostics.py, references/scripts/capability_check.py
- **Findings**: #919 (vault_remember.py no unit tests — 387 lines), #920 (diagnostics.py no unit tests — 236 lines)
- **Items rejected by human**: none

## Scan — 2026-04-14 05:33

- **Files scanned**: references/scripts/capability_check.py (has 8 tests in test_compose_capability.py), tests/test_wizard.py (182 tests, domain_context coverage verified), recent git changes reviewed for regression risks
- **Findings**: none — all major scripts now have adequate test coverage. 850 total tests across project. Diminishing returns on further scanning.
- **Items rejected by human**: none

## Scan — 2026-04-17 17:35

- **Files scanned**: references/scripts/compose.py (529 lines, 14 functions, 2 indirect tests), references/scripts/boot_remote.py (608 lines, 24 functions, 29 tests — spawn/lock untested), references/scripts/git_ops.py (427 lines, 39 tests — adequate)
- **Findings**: #1078 (compose.py no dedicated test file — 529 lines, 14 functions), #1079 (boot_remote.py spawn/lock/poll functions lack unit tests)
- **Items rejected by human**: none

## Scan — 2026-05-23 01:31

- **Files scanned**: state_bus.py, orphan_cleanup.py, cycle_pre.py, git_ops.py, compose.py, event_bus.py, harness.py, shared_fs.py (test:source ratios all ≥1.0x); monitor_smoke_poller.py (untested but a smoke-test tool itself).
- **Findings**: none — recently-touched files have proportional test coverage. #9925's 4 new compose.py helpers (`_read_role_manifest`, `_active_roles_for_roster`, `_render_role_roster`, `_inject_role_roster`) covered by `test_agent_boundaries.py` integration tests (live compose runs).
- **Auto-fixed**: none
- **Items rejected by human**: none
