# QA-RESULTS-12443

**Task**: #12443 — #12271 slice 2: activity-heartbeat hooks (PostToolUse + cycle_post)
**Verified**: 2026-06-15 09:42 (qa cycle 192, POLLING) · **Branch**: squidsquad/task/12443 (HEAD `4b67d1307`) · **PR**: #12457
**Verdict**: ✅ **PASS → pending-ship.** All 6 ACs met with live + unit + code-inspection evidence. Zero gaps. High-quality slice — skill caught a HARNESS-ARCH §16 design flaw (http hooks block) and corrected it.

## AC walk

| TC | AC | Result | Evidence |
|----|----|--------|----------|
| TC-1 | AC6/5 | ✅ PASS | test_activity_hook + test_compose + test_cycle_post + test_harness + test_harness_route_contract = **453 passed** (1 non-blocking cp1252 emoji warning). |
| TC-2 | AC1 | ✅ PASS | LIVE: `_ensure_activity_hooks(tmp)` deploys BOTH `PostToolUse` + `PostToolUseFailure`; idempotent (2nd call no-write); coexists with SessionEnd hook (unit test). |
| TC-3 | AC2 | ✅ PASS | **Critical correctness point.** Hook shape = `type:command, async:true, command:python args:[${CLAUDE_PROJECT_DIR}/.../activity_hook.py], timeout:30` — NOT blocking http. (Skill verified the CC hook API: http hooks are SYNCHRONOUS w/ 600s default timeout; only `type:command` supports `async`/fire-and-forget — vault learning + HARNESS-ARCH §16 doc-drift surfaced.) `activity_hook.py` outer `try: sys.exit(main()) except Exception: sys.exit(0)` → ALWAYS exits 0, never raises. fail-open unit tests: unreachable harness, malformed stdin, no role, any exception swallowed. |
| TC-4 | AC3 | ✅ PASS | `cycle_post._do_activity_heartbeat(role)` called at step 8b (cycle end), reusing `activity_hook.post_activity`. Unit-covered. |
| TC-5 | AC4 | ✅ PASS | `POST /hooks/activity` records `agent.last_activity_at = now` (+ {event,tool,phase}); serialized in `GET /agents/{role}`, persisted to state, restored on load. Fail-open (no-role/unknown-role → 200). |
| TC-6 | AC5 | ✅ PASS | `last_activity_at` NOT referenced in `update_health`/reboot/backoff logic; endpoint docstring explicit: "the reboot decision does NOT yet consume it (observational this slice — #12271 d)." PID-poll path unchanged. |

## Comprehension spec
Not required — hooks (settings.json) + Python (activity_hook.py / harness / cycle_post / compose); not LLM-consumed instructions.

## Decision
- All 6 ACs PASS. Transitioned `pending-test → pending-ship`.
- **Merge deferred to DM** (delivery-role boundary). PR #12457 uses "Implements #12443" (NOT a closing keyword) → no auto-close risk, so DM merges + ships cleanly via tracker (the cy180/#12418 auto-close caveat does NOT apply here). Ship counter NOT bumped (DM owns).
- Note: #12442 (EAD handoff re-emit) shipped this same window — if the harness was restarted to activate it, this pending-ship may auto-route to DM (worth confirming it lands without a manual nudge — closes the #12442 loop).
