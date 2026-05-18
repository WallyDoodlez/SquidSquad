# Working State

- **Task**: #8915
- **Status**: in-progress (AC-3 + AC-5/6/7 content shipped via PR #8996; remaining ACs pending)
- **Started**: 2026-05-18 11:33
- **Last Processed Event ID**: 9d7c2489

## Completed Steps
- Cycle 1135: AC-3 — event_poll.py to spec (PR #8996 first commit).
- Cycle 1136: AC-5 / AC-6 / AC-7 — 5 common-events/ content fragments (l1-base, cursor-management, forge-read-pattern, idle-cooldown-loop, comment-handling) added to PR #8996 second commit. 7-iter external review.

## Remaining Steps
- AC-1 / AC-4: tests/comprehension/8694_spec.json + comprehension test (needs fragments wired into composition first).
- Per-role events fragments under references/sub-skills/roles/<role>/events/.
- Manifest wiring (includes-events.yml) + tests/comprehension/8697_fixtures/ regeneration.
- AC-2 / AC-3 M-3.2: integration tests under tests/integration/test_event_mode_e2e.py.
- Cleanup of pre-existing common-events/event-driven-workflow.md (contains forbidden mode-conditional tokens).

## Key Decisions
- PR #8996 now covers AC-3 + AC-5/6/7. Each subsequent AC will get its own commit on the same branch.
- Manifest wiring deferred to keep current PR contained — currently in `known_unused` list in test_manifest.py.
- 7 review iterations caught 19 real correctness bugs across the content fragments — case precedence, working-state ownership race, degraded-mode gaps, dead boot paths.
