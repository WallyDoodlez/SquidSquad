# TEST-PLAN-12418

**Task**: #12418 — #12271 slice 1: SessionEnd-reason hook for liveness/reboot decisions
**Type**: task (priority:high, approved 2026-06-15) · **Role**: skill · **PR**: #12441
**Derived**: 2026-06-15 from the issue AC list (independent of PR diff). Branch `squidsquad/task/12418`.

## ACs under test (from issue body)

- **AC1** — compose deploys a native `type:http` `SessionEnd` hook into each clone's `settings.json` (per-clone URL + timeout). Verify by RUNNING `compose.py deploy` (settings.json is per-clone state, #11511-excluded from PR).
- **AC2** — Hook reports on graceful exit, fire-and-forget, fail-open: POSTs `stop_reason` to harness; harness-unreachable → hook still succeeds, no teardown delay beyond timeout. No `exit_code`.
- **AC3** — Harness ingests + records `last_session_end = {stop_reason, received_at}` on AgentState, persisted to `.harness-state.json`, exposed via `GET /agents/{role}`.
- **AC4** — Reboot decision = presence/absence: graceful (SessionEnd since last_spawn_at) → respawn, NOT counted to #12244 crash-loop streak; crash (no SessionEnd) → counts → backoff; `intent=stopping` → no respawn.
- **AC5** — Unit tests (dev-authored): hook fail-open, harness ingestion, reboot-decision graceful-vs-crash streak.
- **AC6** — No regression: existing PID-based liveness/reboot unchanged except graceful/crash streak refinement.

## Test cases

| TC | AC | Method | Expected |
|----|----|--------|----------|
| TC-1 | AC5/6 | Run full `tests/test_compose.py` + `tests/test_harness.py` | all green, no prior tests red |
| TC-2 | AC1 | LIVE: run `compose.py deploy qa` (or inspect `_ensure_session_end_hook`), read resulting `settings.json` | SessionEnd `type:http` hook present, per-clone URL via X-Agent-Role, has `timeout` |
| TC-3 | AC2 | Inspect hook config + fail-open path (bounded timeout, always-success); harness-down sim if testable | fail-open: success on unreachable, no block |
| TC-4 | AC3 | Inspect/exercise `POST /hooks/session-end` + `GET /agents/{role}`; check persistence to `.harness-state.json` | last_session_end {stop_reason, received_at} recorded + exposed |
| TC-5 | AC4 | Run the reboot-decision graceful-vs-crash unit tests; inspect the branch logic | graceful → no streak; crash → streak/backoff; stopping → no respawn |
| TC-6 | AC6 | Confirm PID-based path tests still green (subset of TC-1) | unchanged |

## Comprehension spec
Not required — this task touches harness Python + `settings.json` hook config (compose integration). It does NOT modify LLM-consumed instructions (CLAUDE.md / sub-skills / SOUL.md / prompts). Behavior is statically + unit verifiable.

## Notes
- AC1 quirk (skill-flagged): `.claude/settings.json` is per-clone state excluded by the #11511 guard → AC1 verified by running compose, not by a committed settings.json.
- AC3 endpoint is header-based `/hooks/session-end` (role via `X-Agent-Role`), not `/{role}` — PM-affirmed as skill's design call.
- Residual deliberate-spam gap deferred to #12271 hardening (documented).
