# QA-RESULTS-12418

**Task**: #12418 — #12271 slice 1: SessionEnd-reason hook for liveness/reboot decisions
**Verified**: 2026-06-15 03:43 (qa cycle 180, POLLING) · **Branch**: `squidsquad/task/12418` (HEAD `dcc5e17bf`) · **PR**: #12441
**Verdict**: ✅ **PASS → pending-ship.** All 6 ACs met with live + unit evidence; zero blocking gaps. Two minor notes (deferred/cosmetic) flagged for PM/#12271, neither a zero-gap blocker.

## AC walk

| TC | AC | Result | Evidence |
|----|----|--------|----------|
| TC-1 | AC5/6 | ✅ PASS | `tests/test_compose.py` + `tests/test_harness.py` = **300 passed** (1 non-blocking warning — pre-existing Windows cp1252 emoji quirk in harness.py:_log shutdown). +19 net new tests vs main's 281. |
| TC-2 | AC1 | ✅ PASS | LIVE: ran `compose._ensure_session_end_hook(tmp)` → emits `hooks.SessionEnd` = `[{matcher:"", hooks:[{type:"http", url:"http://127.0.0.1:7373/hooks/session-end", timeout:5, headers:{X-Agent-Role:"${SQUIDSQUAD_ROLE}"}, allowedEnvVars:["SQUIDSQUAD_ROLE"]}]}]`. Idempotent: 2nd call returns `False` (no churn — avoids #12397 class). Preserves other keys; corrupt/non-dict handled (5 compose unit tests). |
| TC-3 | AC2 | ✅ PASS | Endpoint `POST /hooks/session-end` always returns 200 (fail-open): malformed body, no-role, unknown-role, save-failure all → 200 (4 unit tests). Hook config `timeout:5` bounds teardown. Uninterpolated `${SQUIDSQUAD_ROLE}` treated as no-role. No `exit_code` consumed. |
| TC-4 | AC3 | ✅ PASS | Endpoint records `agent.last_session_end = {reason, at}` on AgentState, persists via `save_state`, serialized in `GET /agents/{role}` + round-trips through `.harness-state.json` (test_records_reason_on_agentstate, test_persisted_and_restored, test_exposed_via_get_agent). |
| TC-5 | AC4 | ✅ PASS | `update_health` graceful-vs-crash (harness.py ~533-580): graceful (`se_at >= last_spawn_at`) → streak NOT incremented (and deliberately NOT zeroed — F2 anti-spam); crash (no SessionEnd, fast death) → streak++→ backoff at threshold; stale SessionEnd → reads crash via `>= last_spawn_at`; corrupt `{at:null}` guarded (F1 `(se.get("at") or 0)`); `last_session_end` cleared on every spawn (F3, closes delayed-hook race). `intent=stopping` unchanged. 13 TestCrashLoopBackoff tests. |
| TC-6 | AC6 | ✅ PASS | PID-based liveness/reboot path unchanged except the graceful/crash streak refinement (respawn action itself unchanged). No prior test red (300 pass). |

## Notes (flagged for PM / #12271 — NOT blockers)

1. **AC1 "per-clone URL" is a shared URL + per-clone role header.** The hook URL hardcodes `127.0.0.1:7373` for all clones; per-clone identity is the `X-Agent-Role: ${SQUIDSQUAD_ROLE}` header, not the URL. Functionally correct for harness-managed (event-mode) agents on 7373. The qa-on-59999 loop-pin is NOT harness-reboot-managed (loop mode), so the single-port assumption doesn't break any AC today. Port-flexibility = skill's F1, explicitly deferred to #12271. Surfacing so the epic tracks the multi-harness-port case.
2. **AC3 key naming**: impl uses `{reason, at}`; AC text says `{stop_reason, received_at}`. Cosmetic — data + semantics fully present. No action needed unless a downstream consumer expects the literal AC keys.
3. **Residual deliberate-spam gap** (a SessionEnd-spammer keeping the streak from growing): honestly documented in code, deferred to #12271. Natural crash loops don't POST SessionEnd, so #12244 protection is intact.

## Comprehension spec
Not required — touches harness Python + `settings.json` hook config (compose integration), NOT LLM-consumed instructions (CLAUDE.md/sub-skills/SOUL.md/prompts).

## Decision
- All 6 ACs PASS with live + unit evidence. Transitioned `pending-test → pending-ship`.
- **Merge deferred to DM** (deviation from the Merge&Ship "QA merges" step, noted in Discussion): PR #12441 carries `Fixes #12418` → QA-merging would auto-close the issue and skip DM's ship ceremony (the cy151/#12380 pattern). DM merges + ships cleanly. Ship counter NOT bumped (DM owns it).
