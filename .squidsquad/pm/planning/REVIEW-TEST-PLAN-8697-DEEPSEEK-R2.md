I've now reviewed all relevant sections of both files. Here's my assessment:

---

## Second-Pass Review: TEST-PLAN-8697.md (post R1-fix application)

### TC-N-8: Cross-manifest fallback regression test (F5 fix) — CONCRETE ✅

**§7.8, lines 342–347** defines a precise, testable scenario:

- **Scenario**: Role has BOTH `includes-loop.yml` AND `includes-events.yml`. Events manifest references a *missing* fragment. Config says `event-driven: yes`.
- **Assertion chain**: `SystemExit` (non-zero) + stderr contains both the missing fragment path and `includes-events.yml` + CLAUDE.md is unmodified.
- **Why it catches #8699**: The silent-fallback bug would manifest as compose silently switching to `includes-loop.yml` when the events manifest has a broken entry — producing a successful compose (no `SystemExit`), writing loop-mode output to CLAUDE.md. TC-N-8 explicitly asserts the *opposite* of every silent-fallback symptom: non-zero exit, events manifest named in error, and output file untouched. The test is also explicitly scoped against adjacent tests (TC-U-8 generic missing-fragment, TC-N-2 entire manifest missing), so it won't be satisfied by a weaker check.

**Verdict**: Concrete and sufficient.

### L4 split reframing (F6 fix) — CLEAN ✅

- **§6.5, lines 282–291**: Title reads "Mode-specific L4 split convention (already permitted by CONTEXT §5.3, review F6)". Body states "Implementation scope decision (not PM relock)" and "Either path is consistent with CONTEXT.md." No claim of architectural ambiguity remains.
- **§12.1, line 566**: "L4 split mechanism scope decision (implementation, not architecture) — CONTEXT §5.3 already permits mode-specific L4 variants; this is not a PM relock."

Both sections correctly characterize the split as an engineering scope choice, not a PM architecture question requiring relock. Consistent with CONTEXT.md §5.3.

### All 7 F-fixes verification

| Finding | Original Severity | Fix Location | Status |
|---|---|---|---|
| F1 — AC-4-M contradictory clause | error | Lines 43–44 (AC-4-M + new AC-4b-M) | ✅ Fixed |
| F2 — `forge-read` token inconsistency | warning | Lines 40–41 (uniform `forge-read`) | ✅ Fixed |
| F3 — Hollow TC-N-1 | warning | Lines 299–304 (concrete steps) | ✅ Fixed |
| F4 — Classification at P1 only | warning | Lines 51–52 (AC-8), §5.5 (TC-M-5), line 67 (map), line 508 (gating) | ✅ Fixed |
| F5 — Cross-manifest fallback untested | error | Lines 342–347 (TC-N-8) | ✅ Fixed |
| F6 — L4 split "PM relock" framing | info | Lines 282–291 (§6.5), line 566 (§12.1) | ✅ Fixed |
| F7 — L4 boundary detection ambiguity | warning | Lines 127–130 (TC-U-7 marker mandate) | ✅ Fixed |

**No regressions introduced.** The fixes are mechanical and appropriate.

---

**NO_FINDINGS** — the revised plan is clean. All 7 R1 findings are properly addressed, no new issues introduced.