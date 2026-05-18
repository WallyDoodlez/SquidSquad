Now I have a complete picture. Let me verify each finding systematically.

---

## R1 Finding Resolution Summary

### Finding 1 (warning — `.claude-pid` "single-reader" claim)

**Status: RESOLVED.** The executive summary at line 38-41 now reads:
> `.booting` and `.claude-pid` are kept unchanged — they are single-writer mutexes (`.booting` has a single reader; `.claude-pid` has multiple readers, per Q14)

The revision log (line 15) explicitly cites "`.claude-pid` multi-reader clarification applied (Finding 1)." The glossary at line 936-938 also correctly says "single writer (atomic), multiple readers."

---

### Finding 2 (error — Force-kill extended to RESTARTING without PM authorization)

**Status: RESOLVED.** DECISIONS-4792.md Q7 (lines 53-57) now reads:
> **Safety net:** Harness force-kill timeout — if **intent ∈ {STOPPING, RESTARTING}** AND `.claude-pid` alive AND >60s since intent set, harness force-kills the claude PID. (Scope extended to RESTARTING per PM lock 2026-05-18 after deepseek R1 review of CONTEXT-4792.md flagged the ambiguity. Same stuck-agent failure mode applies to both intents; no reason to differentiate.)

The revision log (line 15) cites "PM-locked RESTARTING scope extension." This is now an authorized design decision, not an unapproved extension.

---

### Finding 3 (error — Internal inconsistency between §3.3/§3.4/§5.1 on force-kill scope)

**Status: RESOLVED.** All sections now consistently use `intent ∈ {STOPPING, RESTARTING}`:

| Section | Line | Expression |
|---------|------|------------|
| §1 Executive Summary | 65 | `intent ∈ {STOPPING, RESTARTING}` |
| §2 Q7 | 121 | `intent ∈ {STOPPING, RESTARTING}` |
| §3.3 Header | 259 | `intent ∈ {STOPPING, RESTARTING}` |
| §3.3 Pseudocode | 264 | `if state.intent in (STOPPING, RESTARTING):` |
| §3.3 Trigger condition 1 | 278 | `state.intent in (STOPPING, RESTARTING)` |
| §3.4 Force-kill safety net | 324 | `the §3.3 timer force-kills` |
| §3.6 Crash recovery | 371 | `if state.intent[role] in (STOPPING, RESTARTING) and PID alive` |
| §5.1 Pseudocode | 525 | `if state.intent in (STOPPING, RESTARTING) and self.intent_set_at.get(role):` |
| §5.1 `intent_set_at` sites | 497-498 | `flips intent to STOPPING or RESTARTING` |
| §11 Glossary | 917-919 | `to STOPPING (or RESTARTING)` |

The singular `== STOPPING` / `== RESTARTING` checks at lines 286, 288, 375, 376 are all **post-kill consequence logic** (distinguishing what to do after the PID is dead), not force-kill trigger conditions. This is correct — they need to diverge there.

---

### Finding 4 (warning — §3.6 imprecise temporal expression)

**Status: RESOLVED.** §3.6 line 372 now reads:
> `time.time() - intent_set_at > 60`

This matches §3.3 line 280 and §5.1 line 526. The revision log (line 15) cites "§3.6 elapsed-time expression corrected (Finding 4)."

---

### Finding 5 (warning — §5.1 ambiguous crash-recovery "reset the 60s window" language)

**Status: RESOLVED.** §5.1 lines 506-519 now has explicit two-case handling:

- **(a)** Legacy state file (no `intent_set_at` field): defaults to `time.time()`, fresh window begins — explicitly scoped to pre-#4792 files where no clock data exists.
- **(b)** Current state file (`intent_set_at` IS present): preserve unchanged. Explicit imperative: **"Do NOT reset the window — that would indefinitely defer the kill on every harness restart."**

The revision log (line 15) cites "§5.1 `intent_set_at` migration handling now explicitly two-case (legacy vs present) (Finding 5)."

---

## Regression Check

I audited the remaining document for any regressions introduced by the fixes:

- **§3.6 crash scenario 2** (line 383-386) correctly references both STOPPING and RESTARTING with `time.time() - intent_set_at > 60`.
- **DECISIONS Q10**(scenario 2) matches CONTEXT §3.6 crash scenario 2 — both say "force-kill immediately" when elapsed > 60s.
- **`intent_set_at` setting sites** in §5.1 (lines 497-505) correctly cover all intent-flip sites for both STOPPING and RESTARTING.
- **Glossary** (lines 917-919, 936-938, 941-942) is consistent with updated scope.
- **§3.3 after-kill reconciliation** (lines 286-292) correctly distinguishes STOPPING (leave stopped) vs RESTARTING (respawn via normal gate).
- **§5.1 pseudocode comment** (lines 531-533) matches §3.3 after-kill behavior.
- No residual references to an unqualified "single-reader `.claude-pid`" remain outside the glossary's "single-writer/reader mutexes" parenthetical — which is a looser usage in a definition context and not misleading.

---

## Conclusion

All 5 R1 findings are resolved. No regressions detected. The document is internally consistent and faithfully reflects DECISIONS-4792.md per the criteria.

**NO_FINDINGS**