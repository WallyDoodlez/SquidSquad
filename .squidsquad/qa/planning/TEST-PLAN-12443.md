# TEST-PLAN-12443

**Task**: #12443 — #12271 slice 2: activity-heartbeat hooks (PostToolUse + cycle_post)
**Type**: task (priority:high) · **Role**: skill · **PR**: #12457 · **Branch**: squidsquad/task/12443
**Derived**: 2026-06-15 from issue AC list (independent of PR diff).

## ACs (from issue body)
- **AC1** — `PostToolUse` + `PostToolUseFailure` hooks present in each clone's `settings.json` via compose. Verify by running compose.
- **AC2** — Fire-and-forget / fail-open: bounded timeout, backgrounded, ALWAYS exit 0, NEVER blocks/delays the tool call. (Critical: these fire per-tool-call.)
- **AC3** — `cycle_post` emits an activity heartbeat at cycle end (covers quiet stretches).
- **AC4** — Harness records `last_activity_at` per agent (persisted), exposed via `GET /agents/{role}`.
- **AC5** — Observational only: heartbeat does NOT drive reboot/liveness decision this slice; PID-poll/reboot unchanged.
- **AC6** — Unit tests: hooks fail-open, harness ingestion, last_activity_at from both PostToolUse and cycle_post.

## Test cases
| TC | AC | Method | Expected |
|----|----|--------|----------|
| TC-1 | AC6/5 | full affected suites (test_activity_hook/compose/cycle_post/harness/route_contract) | all green, no regression |
| TC-2 | AC1 | LIVE run `_ensure_activity_hooks(tmp)`; inspect settings.json | both hooks present, idempotent |
| TC-3 | AC2 | inspect hook shape + activity_hook.py exit path | type:command async:true, timeout bounded, always sys.exit(0) |
| TC-4 | AC3 | inspect cycle_post _do_activity_heartbeat | emits at cycle end |
| TC-5 | AC4 | inspect /hooks/activity + AgentState + GET serialization + persist | last_activity_at recorded/exposed/persisted |
| TC-6 | AC5 | grep last_activity_at in reboot/update_health | not consumed → observational |

## Comprehension spec
Not required — hooks (settings.json) + Python (activity_hook.py, harness, cycle_post, compose); not LLM-consumed instructions.
