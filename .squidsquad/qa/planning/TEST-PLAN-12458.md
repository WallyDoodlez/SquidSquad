# TEST-PLAN-12458

**Task**: #12458 — #12271 slice 3: pause-aware liveness guard (Pre/Notification/PreCompact/StopFailure)
**Type**: task (priority:high) · **Role**: skill · **PR**: #12459 · **Branch**: squidsquad/task/12458
**Derived**: 2026-06-15 from issue AC list.

## ACs (from issue body)
- **AC1** — PreToolUse/Notification/PreCompact/StopFailure hooks deployed per-clone, fail-open, PreToolUse NEVER blocks a real tool call.
- **AC2** — Harness records pause state: in-flight tool + tool_call_max deadline; waiting (Notification); compacting (PreCompact); last StopFailure cause.
- **AC3** — Reboot decision GUARDED: (a) mid-tool-call within deadline → hold; (b) Notification-waiting → not dead; (c) compacting → not dead; (d) StopFailure rate_limit/overloaded → back off.
- **AC4** — tool_call_max hard ceiling above longest legit tool call; only past it (no PostToolUse) is mid-call agent wedged.
- **AC5** — No regression: genuinely-dead (PID dead, NO pause signal) still reboots as today.
- **AC6** — Tests per guard branch.

## Test cases
| TC | AC | Method | Expected |
|----|----|--------|----------|
| TC-1 | AC6/5 | full test_harness + test_compose + route_contract | green |
| TC-2 | AC1 | LIVE compose deploy; inspect PreToolUse shape | type:command async:true (non-blocking) |
| TC-3 | AC2 | TestPauseHook12458 ingestion tests | in-flight/waiting/compacting/cause recorded |
| TC-4 | AC3 | TestPauseGuard12458 hold/backoff branches | holds reboot per signal; throttle backs off |
| TC-5 | AC4 | inspect TOOL_CALL_MAX_SECONDS + active_pause ceilings | ceilinged; past-ceiling → not paused |
| TC-6 | AC5 | test_genuine_death_no_pause_reboots + operator_stop_wins | genuine death reboots; stop wins |

## Comprehension spec
Not required — harness.py + compose + settings.json hooks; not LLM-consumed instructions.
