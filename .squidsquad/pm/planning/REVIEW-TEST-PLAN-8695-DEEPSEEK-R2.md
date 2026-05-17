I've reviewed both files. Let me verify each R1 fix systematically.

---

## R1 Fix Verification

### F1 (error, TC-N6 overbroad regex) — ✅ FIXED

**Original**: TC-N6 used loose regex like `dispatch.*gate` and `before.*bootup-complete` that would match negative-form documentation comments like `# No dispatch gate — informational only`.

**Revised** (lines 328–340): TC-N6 now:
- Applies the same `_strip_py_comments_and_docstrings` pre-filter from TC-N1 before any pattern search
- Uses concrete attribute-access/assignment patterns only: `self._pending_dispatch`, `state._pending_dispatch`, `_pending_dispatch[`, `_pending_dispatch\s*=`, `def\s+_hold_event`, `def\s+_queue_pending`, `def\s+_flush_pending`, `dispatch_gate\s*=\s*True`

None of these patterns match a negative-form comment like `# No dispatch gate — informational only`. The comment-stripping pre-filter provides defense-in-depth. **Genuine fix.**

---

### F2 (warning, TC-I1 ambiguity) — ✅ FIXED

**Original**: TC-I1 step 1 had `(or agent absent)` parenthetical, creating ambiguity — an absent agent returns `{"role": "skill", "status": "unknown", "message": "No health data yet"}` with no `bootup_complete` key.

**Revised** (lines 188–196): The precondition now explicitly requires:
> **Agent state pre-seeded so `state.agents["skill"]` exists before step 1**

Step 1 now asserts `response is a full to_dict() payload containing "bootup_complete": false` — no parenthetical, no ambiguity. The reference to "review F2" in the text confirms traceability. **Genuine fix.**

---

### F3 (warning, missing-role coverage) — ✅ FIXED

**Original**: No test covered `POST /events` with a missing `role` field, which could create `AgentState(None)` per harness.py:757-760.

**Revised** (lines 351–358): TC-N8 now covers:
- Sub-case (a): no `role` field at all
- Sub-case (b): empty-string `role`
- Both outcomes (400 rejection or 200 with discard) documented as acceptable
- Verification: `post_keys == pre_keys` and no response item has `role in (None, "")`

This directly addresses the gap — including the empty-string variant the original finding suggested. **Genuine fix.**

---

### F4 (warning, TC-N1 exact-substring false positives) — ✅ FIXED

**Original**: TC-N1's `assert token not in src` on raw source would match negative-form comments like `# No _pending_dispatch — thin harness`.

**Revised** (lines 258–275): Verification block now applies `_strip_py_comments_and_docstrings()` before token matching — stripping `#` line comments and triple-quoted strings. A comment like `# No _pending_dispatch — thin harness` would have its content removed before the token search, eliminating the false positive. **Genuine fix.**

---

## Thin-Harness Regression Check — ✅ NO REGRESSION

All eight negative tests (§5) remain intact. The fixes made them more precise, not weaker:

| Test | Change | Effect |
|------|--------|--------|
| TC-N1 | Added comment-stripping pre-filter | Eliminates false positives; still catches real code usage |
| TC-N6 | Switched to attribute-access patterns + pre-filter | Eliminates false positives; still catches real gating implementation |
| TC-N8 | New test for missing/empty role | Strengthens thin-harness enforcement — prevents garbage `AgentState(None)` |

No negative test was removed or weakened. The AC-8 requirements (no outbound emit, no event-stream alteration, no queue structures, no flush/replay) are all still covered by TC-N2 through TC-N7.

---

## One Minor Observation

**TC-I2** (line 198–205) uses the precondition "Roles `skill` and `qa` both configured" but does not explicitly require pre-seeded `AgentState` for `qa` the way TC-I1 now does for `skill`. Step 3 does `GET /agents/qa` and expects `bootup_complete: false`. If `qa` has no `AgentState` (only a config entry), this GET would return the `{"status": "unknown"}` response lacking a `bootup_complete` key — the same class of ambiguity that F2 flagged for TC-I1. This is **not a regression** (TC-I2 wasn't changed in the R1 revision), and the implementer can resolve it by pre-seeding both roles consistently with the TC-I1 fix pattern. I mention it only for completeness; it does not block sign-off.

---

**Overall verdict: The R1 fixes are real, correctly applied, and traceable. No thin-harness regression. The plan is clean.**

NO_FINDINGS