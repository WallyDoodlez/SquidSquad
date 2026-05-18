Now I have a comprehensive picture. Let me compile my findings.

---

## Findings Summary

**R1 Resolution Verification**: All 12 R1 findings (2 errors + 10 warnings) are correctly resolved in the revised TEST-PLAN-4792.md. The CONTEXT-4792.md revision log confirms parallel fixes were applied there too. However, the revisions introduced two new cross-file inconsistencies and one internal contradiction.

---

### Finding 1

- **File**: `.squidsquad/pm/planning/TEST-PLAN-4792.md`
- **Line**: 57 (AC-16 summary), also `.squidsquad/pm/planning/CONTEXT-4792.md` line 800-802 (§8.1)
- **Severity**: error
- **Issue**: AC-16's summary description and CONTEXT §8.1 claim the harness force-kills the stuck claude PID as the degraded path for #7693 context-pressure restart. This is incorrect. The force-kill safety net is scoped to `intent ∈ {STOPPING, RESTARTING}` per AC-5 (line 35), DECISIONS Q7 (line 53-54), and CONTEXT §3.3 (line 278). During #7693 context-pressure restart, intent stays RUNNING — the harness never flips intent to STOPPING or RESTARTING. The §3.3 force-kill timer does NOT apply. TC-4.8 step 5 (line 296) correctly notes this: *"The §3.3 force-kill timer does NOT apply here because intent stays RUNNING during a context-pressure restart."*
- **Evidence**:
  - TEST-PLAN line 57 (AC-16): *"OR harness force-kills the stuck claude PID (degraded path, < 60s)"*
  - CONTEXT lines 800-802: *"degraded path < 60s via force-kill"*
  - TEST-PLAN line 296 (TC-4.8 step 5): *"The §3.3 force-kill timer does NOT apply here because intent stays RUNNING during a context-pressure restart"* — this is the correct statement.
  - TEST-PLAN line 35 (AC-5): force-kill scope is `{STOPPING, RESTARTING}` only.
  - CONTEXT line 278: trigger condition is `state.intent in (STOPPING, RESTARTING)`.
  - DECISIONS lines 53-54: Q7 safety net scoped to `{STOPPING, RESTARTING}`.
  - TC-4.8 step 5 correctly says if agent fails to terminate within 60s, *"mark the test FAILED"* — not "harness force-kills." The degraded path for #7693 is: agent fails to `/quit` → agent stays stuck → test fails (same as yesterday's bug). There is no harness safety net for this case.
- **Suggested fix**: 
  1. In AC-16 (TEST-PLAN line 57): change *"OR harness force-kills the stuck claude PID (degraded path, < 60s)"* to something like *"OR the agent fails to self-quit within 60s and the test fails (the §3.3 force-kill safety net does not cover this case because intent stays RUNNING)"*.
  2. In CONTEXT §8.1 (line 800-802): change *"degraded path < 60s via force-kill"* to *"degraded path: agent fails to self-quit → test fails (force-kill safety net is scoped to STOPPING/RESTARTING intents only, not RUNNING)"*.

---

### Finding 2

- **File**: `.squidsquad/pm/planning/TEST-PLAN-4792.md`
- **Lines**: 95 (TC-3.1.1), 106-107 (TC-3.1.3b)
- **Severity**: warning
- **Issue**: TEST-PLAN references `STOPPED` as a distinct intent value, but CONTEXT-4792.md and DECISIONS-4792.md never define a `STOPPED` intent — they use `STOPPING` as the intent and `stopped` as a status, with intent staying `STOPPING` after the agent terminates.
- **Evidence**:
  - TEST-PLAN line 95 (TC-3.1.1): *"intent transitions to `STOPPED` after kill confirmation"* — treats STOPPED as an intent value.
  - TEST-PLAN lines 106-107 (TC-3.1.3b): *"Force-kill does NOT fire when intent ∈ {RUNNING, STOPPED}"* — lists STOPPED alongside RUNNING as an intent value.
  - CONTEXT §3.3 line 286-287: *"If intent == STOPPING: marks status=stopped, intent stays STOPPING (no respawn)"* — intent stays STOPPING, never transitions to STOPPED.
  - CONTEXT §5.1 force-kill code (lines 524-525): checks only `if state.intent in (STOPPING, RESTARTING)` — no STOPPED check.
  - DECISIONS-4792.md: zero mentions of STOPPED as an intent; all Q7 discussion uses STOPPING.
  - CONTEXT §3.6 line 375: *"if state.intent[role] == STOPPING and PID dead → leave stopped"* — consistent with STOPPING-as-intent model.
- **Suggested fix**: Either (a) update TEST-PLAN to match CONTEXT's model (remove STOPPED as an intent, keep STOPPING as the only "stop" intent, gate force-kill exclusion on PID-dead check rather than a separate intent value), or (b) update CONTEXT to define a STOPPED intent that the state machine transitions to after termination. The implementer needs one consistent model to build against.

---

### R1 Resolution Confirmation

All 12 prior findings verified as resolved:

| Finding | Original Issue | Resolution |
|---------|---------------|------------|
| F1 (error) | Phantom AC-16 ref in TC-3.2.2 | Replaced with Q16 reference (line 130) |
| F2 (error) | AC-13/TC-7.2 contradicted Q8 `harness_status` | AC-13 (line 50) and TC-7.2 (lines 420-422) now explicitly allow the Q8 delta |
| F3 (warn) | AC-14 blanket clone-path claim | Split into per-role vs harness-owned (lines 51-54) |
| F4 (warn) | No #7693 gating test | Added AC-16 + TC-4.8 (lines 57, 287-308) |
| F5 (warn) | AC-6 measured only by comprehension | Added behavioral verification component (lines 36-39, 217) |
| F6 (warn) | TC-6.8 escape hatch | Removed OR clause, mandated AST sha256 (lines 381-383) |
| F7 (warn) | TC-3.4.3 `current-state` undefined | Replaced with concrete `.claude-pid` + process probes (lines 167-169) |
| F8 (warn) | CONTEXT §3.4 RESTART force-kill inconsistency | Both documents now consistent: RESTARTING included (TC-3.1.3 lines 101-104, CONTEXT §3.3 lines 259, 278) |
| F9 (warn) | TC-7.4 end-state diff vague | Specified exact files and ALLOWED-DIFFERENT fields (lines 433-441) |
| F10 (warn) | TC-9.2 non-deterministic ancestor | Three-tier deterministic preference (lines 503-507) |
| F11 (warn) | §4.1 unbounded cycle_remaining | Bounded to short-cycle agent, < 55s (lines 209-216) |
| F12 (warn) | §4.2 unspecified stub | Three concrete mechanisms enumerated (lines 223-228) |