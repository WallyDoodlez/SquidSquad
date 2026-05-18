Now I have a complete picture. Let me compile findings.

---

### Finding 1

- **File**: `.squidsquad/pm/planning/TEST-PLAN-4792.md`
- **Lines**: 296 and 298 (TC-4.8 steps 5 and 7)
- **Severity**: error
- **Issue**: TC-4.8 was not updated for the routing fix (R2 Finding 1 resolution). The routing fix says `cycle_post.py` POSTs `/agents/{role}/restart` before exiting 42 on context-pressure, flipping `intent=RESTARTING`. But TC-4.8 step 5 still claims "intent stays RUNNING" and "the §3.3 force-kill timer does NOT apply," and step 7 still says `intent=RUNNING`. These contradict AC-16 (line 57), DECISIONS Q7 (lines 59–66), and CONTEXT §8.1 (lines 797–812) — all of which correctly describe intent=RESTARTING after the routing POST, putting the degraded path within the RESTARTING force-kill scope.
- **Evidence**:
  - DECISIONS Q7 (lines 60–62): *"it first POSTs `/agents/{role}/restart`... to flip `intent=RESTARTING`"*
  - CONTEXT §8.1 (lines 810–811): *"degraded path < 60s via force-kill since intent=RESTARTING is in scope"*
  - AC-16 (line 57): *"harness force-kills the stuck claude PID via the RESTARTING force-kill scope (degraded path, < 60s) → harness observes the dead PID with `intent=RESTARTING`"*
  - TC-4.8 step 5 (line 296): *"The §3.3 force-kill timer does NOT apply here because intent stays RUNNING during a context-pressure restart (context-pressure does not flip intent to STOPPING or RESTARTING — it is an agent-side termination signal)."* — **incorrect after routing fix**, since cycle_post explicitly flips intent to RESTARTING.
  - TC-4.8 step 7 (line 298): *"observes the dead PID with `intent=RUNNING`"* — **should be `intent=RESTARTING`**.
- **Suggested fix**:
  - **Step 5**: Replace with: *"**Degraded path** (only if step 4 does not occur): the §3.3 force-kill timer DOES apply because `cycle_post.py` POSTed `/restart` before exiting (intent=RESTARTING is in force-kill scope). Wait for the force-kill to fire within 60s of `intent_set_at`. If the agent still fails to terminate within 65s of `cycle_post` exit time (60s + 5s grace), mark the test FAILED — this indicates both the Q7 self-quit instruction and the RESTARTING force-kill safety net failed."*
  - **Step 7**: Change *"`intent=RUNNING`"* to *"`intent=RESTARTING`"*.

---

### Finding 2

- **File**: `.squidsquad/pm/planning/TEST-PLAN-4792.md`
- **Line**: 219 (TC-4.1 assertion)
- **Severity**: warning
- **Issue**: §4.1 assertion says *"`.harness-state.json` updated to `intent=stopped`"*, but CONTEXT §3.3 (line 286–287) and §3.2 (line 251–253) consistently state that intent stays `STOPPING` after termination — `stopped` is a status, not an intent. TC-3.1.1 (line 95) was correctly fixed to read *"status transitions to `stopped` (lowercase status; intent remains `STOPPING` until cleared per Q10)"*, but §4.1 line 219 was missed.
- **Evidence**:
  - CONTEXT §3.3 (lines 286–287): *"If intent == STOPPING: marks status=stopped, intent stays STOPPING (no respawn)."*
  - CONTEXT §3.2 (lines 251–253): *"intent STOPPING — does NOT respawn... Marks agent status=stopped, idle in the table."*
  - TEST-PLAN TC-3.1.1 (line 95): *"status transitions to `stopped` (lowercase status; intent remains `STOPPING` until cleared per Q10)"* — **correct**.
  - TEST-PLAN §4.1 (line 219): *"`.harness-state.json` updated to `intent=stopped`"* — **contradicts** the STOPPING-as-intent model.
- **Suggested fix**: Change line 219 to: *"`.harness-state.json` reflects `intent=STOPPING, status=stopped`"* or *"Harness marks agent `status=stopped` (intent remains `STOPPING` per Q10)."*

---

### Finding 3

- **File**: `.squidsquad/pm/planning/TEST-PLAN-4792.md`
- **Line**: 561 (§12 post-ship validation step 4)
- **Severity**: warning
- **Issue**: Post-ship context-pressure soak step 4 says *"sees intent=running, respawns"*, but after the routing fix (cycle_post POSTs /restart → intent=RESTARTING), the harness should see `intent=RESTARTING`. This is the same root cause as Finding 1 but in the post-ship validation section.
- **Evidence**:
  - DECISIONS Q7 (lines 60–62): cycle_post POSTs /restart → intent=RESTARTING.
  - CONTEXT §8.1 (lines 806–807): *"After claude PID dies with `intent=RESTARTING`, the harness respawns..."*
  - TEST-PLAN §12 (line 561): *"Harness observes dead PID within 5s, sees intent=running, respawns via `boot_remote.boot_agent`."* — **intent should be RESTARTING, not running**.
- **Suggested fix**: Change *"sees intent=running"* to *"sees `intent=RESTARTING`"* (or, for implementation flexibility, *"sees `intent=RESTARTING` (set by `cycle_post.py`'s pre-exit POST)"*).

---

### Finding 4

- **File**: `.squidsquad/pm/planning/TEST-PLAN-4792.md`
- **Line**: 107 (TC-3.1.3b parenthetical)
- **Severity**: warning
- **Issue**: TEST-PLAN lists `IDLE` as a valid intent value (*"intent values are RUNNING / STOPPING / RESTARTING / IDLE per `.harness-state.json` schema"*), but neither CONTEXT-4792.md nor DECISIONS-4792.md define `IDLE` as an intent. CONTEXT uses `idle` only as a status/descriptor (line 253: *"status=stopped, idle in the table"*), not as an intent in the state machine. The implementer has ambiguity: should the harness code handle an `IDLE` intent, or is this a documentation gap?
- **Evidence**:
  - TEST-PLAN line 107: *"intent values are RUNNING / STOPPING / RESTARTING / IDLE per `.harness-state.json` schema"*
  - CONTEXT §3.3 (line 264): force-kill scope enumerated as only `{STOPPING, RESTARTING}` — IDLE not mentioned.
  - CONTEXT §3.2 (line 251–252): auto-reboot gate checks `intent ≠ RUNNING/RESTARTING` — IDLE not mentioned.
  - CONTEXT §3.6 (line 375): *"if state.intent[role] == STOPPING and PID dead → leave stopped"* — no IDLE intent state.
  - DECISIONS-4792.md: zero mentions of IDLE as an intent.
- **Suggested fix**: Either (a) add `IDLE` to the enumerated intent set in CONTEXT §11 Glossary or the state-machine descriptions in §3, or (b) remove `IDLE` from the TEST-PLAN line 107 parenthetical and use a scope-based exclusion instead, e.g.: *"(the force-kill safety net is scoped to STOPPING and RESTARTING only; all other intent values — RUNNING, and any future additions — are excluded)"*.

---

**Summary**: The R2 Finding 1 fix (routing POST) was correctly applied to DECISIONS Q7, CONTEXT §8.1, and AC-16, but TC-4.8 steps 5/7 and §12 post-ship step 4 were not updated — they still describe the pre-fix model where intent stays RUNNING during context-pressure restart. The R2 Finding 2 fix (STOPPED → status terminology) was correctly applied to TC-3.1.1 and TC-3.1.3b, but §4.1 line 219 was missed (still says `intent=stopped`). Additionally, the `IDLE` intent value introduced by the TC-3.1.3b fix is not cross-referenced in CONTEXT or DECISIONS, creating a documentation gap.