# Working State

- **Task**: #8915
- **Status**: in-progress (AC-3 + AC-5/6/7 + AC-1 partial + AC-4 + AC-5 cleanup + DM events shipped via PR #8996)
- **Started**: 2026-05-18 11:33
- **Last Processed Event ID**: 9d7c2489

## Completed Steps
- Cycle 1135: AC-3 — event_poll.py to spec (PR #8996 commit ec23381f).
- Cycle 1136: AC-5/6/7 — 5 common-events/ fragments + 53 tests (commit f304fab2; 7-iter review).
- Cycle 1137: AC-1 partial + AC-4 — comprehension spec + 18-test validator (commit 3381ce0a; 1-iter clean).
- Cycle 1138: AC-5 cleanup — rewrote legacy event-driven-workflow.md (commit c76b6335; 3-iter review).
- Cycle 1139: DM per-role events fragment pr-merge-wait.md (commit 5bbea452; 6-iter review).

## Remaining Steps
- AC-1 M-1.3: live run_comprehension_test.py against the spec (deferred to QA).
- pm/qa/skill per-role events fragments (if needed — DM has the obvious one).
- Manifest wiring (includes-events.yml) + tests/comprehension/8697_fixtures/ regeneration.
- AC-2 / AC-3 M-3.2: integration tests under tests/integration/test_event_mode_e2e.py.

## Key Decisions
- DM was the only role with an explicitly-named per-role fragment in CONTEXT.md §5.1.
- 6-iter review for the DM fragment caught 17 correctness bugs (Case B/D framing, delivery:skip prohibition, TOCTOU, precedence rules, etc.).
- Three high-priority approved tasks (#8950, #8917, #8916) waiting behind #8915.
