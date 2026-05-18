# Working State

- **Task**: #8915
- **Status**: in-progress (AC-3 shipped, remaining ACs pending)
- **Started**: 2026-05-18 11:33
- **Last Processed Event ID**: 9d7c2489

## Completed Steps
- Cycle 1135: AC-3 (event_poll.py rewrite to TEST-PLAN-8694.md §3.1-3.5 spec) shipped as PR #8996. 47 unit tests. 6-iter external review.

## Remaining Steps
- AC-1 / AC-4: tests/comprehension/8694_spec.json + comprehension test.
- AC-5 / AC-6 / AC-7: content fragments under references/sub-skills/common-events/ and per-role references/sub-skills/roles/<role>/events/, plus negative grep guards.
- AC-2 / AC-3 M-3.2: integration tests under tests/integration/test_event_mode_e2e.py.

## Key Decisions
- Multi-cycle task — slicing by AC to keep PRs reviewable.
- AC-3 PR #8996 stays at in-progress (NOT pending-test) until all ACs ship — issue itself remains in-progress.
- 6-iter review caught real bugs: missing-id re-delivery, --since pinned in --wait loop, IncompleteRead/UnicodeDecodeError crashes, malformed payload crashes.
