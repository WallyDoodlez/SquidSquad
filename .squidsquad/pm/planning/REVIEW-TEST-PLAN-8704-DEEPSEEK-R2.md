## Second-Pass Verification: All 5 R1 Findings

I reviewed the revised `TEST-PLAN-8704.md` against each of the 5 required corrections. All are clean.

---

### ✅ F1 (error) — TC-U1b field completeness with type checks

**Lines 65–76**. TC-U1b now enumerates all 6 required fields (`number`, `title`, `role`, `status`, `priority`, `age`/`transitioned_at`) with explicit type assertions: `int`, `string` (×4), `ISO-8601 string`. Verification block (line 76) specifies:
- `all(k in item and item[k] is not None for k in REQUIRED_KEYS)` per item (presence + non-null)
- At least one seeded item checked for exact value match against seed data

No gaps. AC3 all-fields requirement is now covered by a dedicated unit test.

---

### ✅ F2 (error) — SM-4 covers AC12 backward-compat (Discussion + email-on-mention)

**Line 223**. SM-4 explicitly calls out:
- (a) item appears in `/human/queue` and TUI panel
- (b) assignee/mentioned user receives email notification (visual check in inbox or GitHub notification feed)
- (c) Discussion comment is visible via `gh issue view` and email-on-mention fires for `@user` mentions

Both notification surfaces named in AC12 — Discussion comments and email-on-mention — are covered. The test is correctly classified as manual smoke (§7), exempt from the automated gate.

---

### ✅ F3 (warning) — TC-I4 designer-as-worker is unconditional

**Lines 145–150**. TC-I4's precondition now seeds one `pending-human-*` issue per role for **all four roles** — `skill`, `qa`, `dm`, **AND `designer`** — with explicit language: "even if `designer` is not active in the current `config.md`, the test fixture seeds an issue." Expected result and verification (lines 149–150) require all four items present, designer item's `role` field equals `designer`, and a `grep` negative confirms no `role == "designer"` branching in `harness.py`.

The old conditional ("if a designer agent transitioned one") is gone. The test is now unconditionally exercised.

---

### ✅ F4 (warning) — Panel verification via stdout capture (not manual screenshot)

**Lines 119, 126**. TC-I1 now explicitly states: "Panel rendered output is captured via **stdout capture** (the panel must support a test mode that prints panel state to stdout on each refresh, or use `httpretty`/`responses`-equivalent HTTP mocking with a headless render harness)." Verification (line 126) clarifies "No screenshot inspection — assertions run via string match on captured stdout." TC-I2 (lines 130, 136) follows the same pattern.

Panel content is now asserted programmatically via stdout string matching. The integration tests are fully automatable for the zero-gap gate.

---

### ✅ F5 (warning) — Zero-gap gate exempts §7 manual smoke

**Line 19**. The gate definition now reads: "any **automated** TC failure (unit, integration, negative, TUI integration in §3–§6) routes the task back to dev. … **Manual smoke tests in §7 are EXEMPT from the automated gate** (review F5) — they are executed once by a human at ship-review time." SM-4 (line 223) also reiterates: "This test is exempt from the automated zero-gap gate." The §2 Test Categories Map (line 52) labels §7 as "Manual smoke (gate-exempt)."

No ambiguity remains about gate scope.

---

### Bonus: No regressions from revision

- **TC-T1** (lines 195–200): Precondition, Expected, and Verification all explicitly state TUI is a **separate process** from `harness.py`, with process listing verification (two distinct PIDs). ✓
- **SM-1/SM-2** (lines 220–221): Both note "Precondition: TUI started as a separate process (PM Gap 1)." ✓
- **Overview line 21**: Reiterates "The TUI runs as a **separate process** consuming harness HTTP endpoints." ✓
- **Overview line 17**: The phrase "harness-served TUI process" could be read ambiguously, but line 21 immediately clarifies with the separate-process statement. No contradiction.

---

## Conclusion

`NO_FINDINGS` — the revised test plan cleanly resolves all 5 R1 findings. TC-U1b covers all 6 fields with type checks, SM-4 covers AC12 Discussion + email-on-mention, TC-I4 designer-as-worker is unconditional, TC-T1 enforces separate-process TUI, and the zero-gap gate explicitly exempts §7 manual smoke.