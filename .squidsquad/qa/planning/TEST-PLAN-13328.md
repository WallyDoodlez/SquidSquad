# TEST-PLAN-13328 — retire loop-interval prompt

**Issue**: #13328 (type:task, priority:medium) — PM-specced; ref [[project_event_mode_default]].
**PR**: #13420 `squidsquad/task/13328`, head 055acdcfd.
**Derived from**: issue ACs (independent of worker diff).

## ACs
- AC1: fresh wizard run does NOT prompt for loop/iteration interval.
- AC2: config.md still receives a valid Iteration Interval default (polling fallback functional).
- AC3: summary no longer implies agents run on a fixed loop by default.
- AC4: wizard.py Step 5 tests (TC-49..TC-52) updated/removed — no orphaned tests.
- AC5 (comprehension): wizard messaging presents event-mode as default, loop as fallback.

## Test cases
- TC-1 (AC1): grep wizard.py — validate_interval/cmd_validate_interval/validate-interval retired; no interval prompt.
- TC-2 (AC2): read build_config_md + config.py FIELD_MAP/default; independent E2E — no ## Loop, Iteration Interval=30, Context Pressure=70.
- TC-3 (AC3): post_setup_summary has no Loop:N line.
- TC-4 (AC4): run test suites; confirm TC-49..52 removed (tombstoned) + new coverage; no orphaned refs.
- TC-5 (AC5 CQ): 13328_spec review; fresh Sonnet agent on INSTALLER-RUNTIME.md §5/§8/§9 only; zero misreads.
- TC-6 (gate+landing): combined-state static gate (branch shares wizard.py/config.py/SKILL.md with #13355/#13339/#13397 on main); local merge + combined gate; disjoint/reconciled.

CQ REQUIRED — INSTALLER-RUNTIME.md is LLM-consumed (AC5 explicit).
