After a thorough review of CONTEXT-4792.md against DECISIONS-4792.md and RESEARCH-4792-lifecycle-audit.md, I've identified several issues. Here are my findings:

---

### Finding 1

- **File**: .squidsquad/pm/planning/CONTEXT-4792.md
- **Line**: §1 (Executive Summary), line ~12 (paragraph 2)
- **Severity**: warning
- **Issue**: The executive summary incorrectly describes `.claude-pid` as a "single-reader" mutex. It states: "`.booting` and `.claude-pid` are kept unchanged — they are single-writer/single-reader mutexes, not split-brain control paths (Q9, Q14)."
- **Evidence**: `.booting` is correctly single-writer/single-reader (both inside `boot_remote`). However, `.claude-pid` has 5 distinct readers across the codebase per RESEARCH §2.2 table: `harness.update_health` (line 148), `boot_remote._needs_boot` (line 309), `reboot_agent._read_claude_pid` (line 83), `health_check._read_claude_pid_file` (line 193), and `thin_launcher._check_singleton` (line 73). DECISIONS Q14 correctly states it is "single writer (atomic), multiple readers." The CONTEXT executive summary's "single-reader" claim is factually wrong and could mislead an implementer about which files may legitimately read `.claude-pid`.
- **Suggested fix**: Replace "single-writer/single-reader mutexes" with "single-writer mutexes (`.booting` has a single reader; `.claude-pid` has multiple readers, per Q14)" or equivalent accurate language.

---

### Finding 2

- **File**: .squidsquad/pm/planning/CONTEXT-4792.md
- **Line**: §3.4 (Agent restart), lines describing "[Force-kill safety net per Q7]"
- **Severity**: error
- **Issue**: The CONTEXT extends the Q7 force-kill safety net to the RESTARTING intent, but DECISIONS Q7 only specifies the safety net for STOPPING. This is a new design choice beyond the locked decisions.
- **Evidence**: DECISIONS Q7 states: "Safety net: Harness force-kill timeout — if intent=STOPPING AND `.claude-pid` alive AND >60s since intent set, harness force-kills the claude PID." Only STOPPING is mentioned. CONTEXT §3.4 applies the same mechanism to restart: "[Force-kill safety net per Q7]: → if neither path fires within 60s, harness force-kills then respawns." This is a semantically meaningful extension — for STOPPING the agent stays stopped after kill, but for RESTARTING it would respawn. The DECISIONS lock does not authorize this extension.
- **Suggested fix**: Either (a) clarify with PM whether RESTARTING should be included in the force-kill safety net and, if so, amend DECISIONS-4792.md Q7 to match, or (b) remove the force-kill safety net reference from §3.4 and restrict it to STOPPING only as locked.

---

### Finding 3

- **File**: .squidsquad/pm/planning/CONTEXT-4792.md
- **Line**: §3.3 vs §3.4 vs §5.1 (force-kill conditions)
- **Severity**: error
- **Issue**: Internal inconsistency within CONTEXT about whether the force-kill safety net applies to RESTARTING. §3.4 asserts it does, but §3.3 trigger conditions and §5.1 pseudo-code both check only `intent == STOPPING`.
- **Evidence**: 
  - §3.3 trigger conditions: "1. `state.intent == STOPPING`" (only STOPPING).
  - §5.1 pseudo-code: `if state.intent == STOPPING and self.intent_set_at.get(role):` (only STOPPING).
  - §3.4 describes force-kill safety net for restart, implying RESTARTING should also trigger the check.
  - §5.1 bullet points direct the implementer to set `intent_set_at[role]` in `restart_agent(role)` and `/agents/all/stop` — the restart path sets the timer but the §5.1 check code never reads it for RESTARTING.
  
  An implementer reading these three sections will reach contradictory conclusions about whether force-kill applies to restart.
- **Suggested fix**: Reconcile all three sections. If RESTARTING is in scope (pending Finding 2 resolution), change §3.3 condition 1 and §5.1 code to `intent in (STOPPING, RESTARTING)`. If RESTARTING is out of scope, remove the §3.4 force-kill reference and remove `intent_set_at` setting from `restart_agent` in §5.1.

---

### Finding 4

- **File**: .squidsquad/pm/planning/CONTEXT-4792.md
- **Line**: §3.6, crash recovery section (near "→ if state.intent[role] == STOPPING and PID alive and intent_set_at > 60s")
- **Severity**: warning
- **Issue**: The crash-recovery pseudocode uses imprecise temporal logic that doesn't match the implementation described in §5.1.
- **Evidence**: §3.6 writes: "if state.intent[role] == STOPPING and PID alive and intent_set_at > 60s → force-kill per 3.3." This reads as comparing a timestamp (`intent_set_at` is a `time.time()` float, e.g., `1715970000.123`) directly to 60, which would always be true. The correct expression (shown in §3.3 and §5.1) is `time.time() - intent_set_at > 60`. The implementer won't be misled because §5.1 has the correct code, but the workflow spec in §3.6 is the authoritative reference for test-plan authors and is wrong as written.
- **Suggested fix**: Change to "if state.intent[role] == STOPPING and PID alive and `time.time() - intent_set_at > 60` → force-kill per 3.3."

---

### Finding 5

- **File**: .squidsquad/pm/planning/CONTEXT-4792.md
- **Line**: §5.1 bullet: "Crash-recovery `load_state` path — if loaded state has STOPPING intent but no `intent_set_at`, default to `time.time()` (i.e., reset the 60s window post-recovery)."
- **Severity**: warning
- **Issue**: The parenthetical "(i.e., reset the 60s window post-recovery)" is ambiguous and conflicts with DECISIONS Q10 scenario 2.
- **Evidence**: DECISIONS Q10 scenario 2 states: "Harness crash during force-kill timeout — on restart, harness reads `intent_set_at` from JSON; if elapsed > 60s and PID still alive, force-kill immediately." This mandates that when `intent_set_at` IS present and the timeout has expired, the harness acts immediately — NOT reset. The CONTEXT correctly handles this in §3.6 ("if elapsed > 60s... force-kill immediately"). However, the §5.1 bullet only addresses the legacy case (no `intent_set_at` in JSON) and parenthetically says "reset the 60s window post-recovery" — which, read in isolation, could be misinterpreted as resetting the window even when `intent_set_at` IS present. The phrase "post-recovery" is ambiguous: does it refer to recovery from the missing-field case, or recovery from a crash generally?
- **Suggested fix**: Clarify: "if loaded state has STOPPING intent but no `intent_set_at`, default to `time.time()` (i.e., the 60s window begins fresh when the field was missing from a pre-#4792 state file). If `intent_set_at` is present, preserve it unchanged — the normal health poll will compute elapsed time and force-kill immediately if >60s per Q10 scenario 2."

---

### Summary

| Criterion | Status |
|---|---|
| 1. Q1–Q17 faithfully represented | PASS (all 17 locks correctly captured, with the exception flagged in Finding 2) |
| 2. No new design choices beyond locks | **FAIL** — Force-kill extension to RESTARTING (§3.4) is a new design choice beyond Q7 |
| 3. #7693 closure mechanism correctly documented | PASS (dual mechanism correctly described across §3.2, §3.3, §5.1, §5.6, §5.11, §8.1) |
| 4. §6 coordination with Phase 5 (#8697) sound both directions | PASS (matches DECISIONS Q12, either merge order is workable) |
| 5. §5 per-surface specs match research file:line refs | PASS (all file:line references verified against RESEARCH Appendix A) |
| 6. §3 workflow specs consistent with locks | **PARTIAL** — Inconsistency between §3.4 (force-kill on restart) and DECISIONS Q7 (STOPPING only), plus internal inconsistency between §3.3/§3.4/§5.1 |
| 7. No §10 residual open questions beyond Phase 6+ tech debt | PASS (three items match DECISIONS "Side-Decisions" exactly) |

The two blocking issues are **Findings 2 and 3** — the force-kill safety net scope on RESTARTING needs to be resolved with PM and the CONTEXT must be internally reconciled before this artifact can transition to planned. **Findings 1, 4, and 5** are documentation-quality issues that should be fixed but don't block the design.