Now I'll verify each R1 finding against the revised document and check for any residual or new issues.

**R1 finding verification summary:**

| # | Finding | Status | Evidence |
|---|---------|--------|----------|
| F1 | TC-N2 contradiction | ✓ Fixed | Lines 206-215: split into (a) no stale-warning, (b) bootup_complete/status update via harness. Note clarifies `current_phase` staleness is expected. |
| F2 | TUI process model | ✓ Fixed | Lines 172-173: TC-I4 "Stop the harness; start the panel as a separate process." OQ6 closed (line 388). |
| F3 | HTTP error response coverage | ✓ Fixed | Lines 233-242: TC-N5 added with 5 sub-cases (500, 404, missing key, missing fields, malformed JSON). |
| F4 | Refresh independence | ✓ Fixed | Lines 116-119: TC-U4 "zero agent activity, zero events, zero state changes"; asserts no events emitted. |
| F5 | TC-N4 tracer scope | ✓ Fixed | Lines 227-231: expanded to `/tmp`, `~/.cache`, repo root. context-pressure locked to NOT preserved. |
| F6 | TC-U4 counts only `/agents` | ✓ Fixed | Lines 117-118: "counts ALL HTTP requests across all endpoints"; expected guards against per-agent call explosion. |
| F7 | TC-T4 conflated propagation | ✓ Fixed | Lines 313-316: decoupled per panel; human-queue panel ≤ 20s (includes cache TTL). "Same render window" removed. |
| F8 | SIGTERM exit code | ✓ Fixed | Line 181: "exit code 0 or 143 acceptable." |
| F9 | Mode detection edge cases | ✓ Fixed | Line 113: note about `compose.py`'s `_read_config_value()` tests; reimplement-only fallback. |
| F10 | Refresh interval source | ✓ Fixed | Lines 115-116, 387: OQ5 closed; TC-U4 uses hard-coded 5s. |

All 10 R1 findings plus both locked gaps (Gap 1, Gap 4) were addressed. However, the hard-coded-5s lock from Gap 4 was not fully propagated to two tests that still reference configurable cadence values. Three issues remain:

---

### Finding 1

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8700.md`
- **Line**: 184-191 (TC-I5)
- **Severity**: error
- **Issue**: TC-I5 still specifies "Refresh interval = 3s" and expects state change visible "within 6s" with sampling "for up to 6s." PM Gap 4 locked the refresh interval to hard-coded 5s with no config knob in v1. The test as written is unimplementable — there is no mechanism to set the interval to 3s, and the 6s sampling window would be too short (a single 5s refresh cycle could miss the window before sampling ends).

- **Evidence**: Line 184: "Refresh interval = 3s." Line 187: "sample panel output every 500ms for up to 6s." Line 188-189: "within 6s (= 2 × interval)." The Revision Log (lines 13-14) states Gap 4 locked: "hard-coded 5s default, no config knob in v1." TC-U4 was updated for this lock but TC-I5 was not. At the locked 5s cadence, 2× interval = 10s, requiring at least 10s of sampling (not 6s).

- **Suggested fix**: Update TC-I5 to use the hard-coded 5s interval: "Refresh interval = 5s (hard-coded, per PM Gap 4)." Change expected to "within 10s (= 2 × interval)" and extend sampling to "for up to 12s" (or 10s + buffer). Update the verification to "≤ 2 × the hard-coded 5s interval (i.e. ≤ 10s)."

---

### Finding 2

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8700.md`
- **Line**: 301-306 (TC-T3)
- **Severity**: warning
- **Issue**: TC-T3 says "Single TUI process with cadence configured to 4s" and expects "both panels fire on the shared 4s schedule." The cadence is now hard-coded at 5s (PM Gap 4), making the test's specific value wrong and the word "configured" misleading — there is no configuration knob in v1.

- **Evidence**: Line 301: "cadence configured to 4s." Line 304: "shared 4s schedule." The Revision Log (lines 13-14) and A8 (line 60) both state: "hard-coded 5s in v1 per PM Gap 4." TC-T3 was not updated to reflect this.

- **Suggested fix**: Change line 301 to "Single TUI process with the hard-coded 5s cadence (PM Gap 4)." Change line 304 to "shared 5s schedule." Update the implied measurement window accordingly (40s / 5s = 8 expected refresh cycles per panel, not 10).

---

### Finding 3

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8700.md`
- **Line**: 47-49 (A4 measurable refinement)
- **Severity**: warning
- **Issue**: The A4 measurable refinement (bracketed text added by the test plan author, not verbatim from CONTEXT.md) says "at the default 2–5s cadence." PM Gap 4 locked the cadence to hard-coded 5s — there is no 2–5s range in v1. This creates a conflict between the measurable refinement and the actual locked value stated in A8 (line 60) and TC-U4 (line 115-116).

- **Evidence**: Line 47-49: "at the default 2–5s cadence, the panel makes ≤1 HTTP call per refresh per panel and consumes <5% CPU on the harness host during a 30s sample." Line 60 (A8): "hard-coded 5s in v1 per PM Gap 4." The 2–5s range implies variability that doesn't exist. If "2–5s" was deliberately retained as a future-proofing note, it should explicitly say so and reference the locked v1 value.

- **Suggested fix**: Change "at the default 2–5s cadence" to "at the hard-coded 5s cadence (v1; range 2–5s possible in future)." Or simply "at the hard-coded 5s refresh cadence."