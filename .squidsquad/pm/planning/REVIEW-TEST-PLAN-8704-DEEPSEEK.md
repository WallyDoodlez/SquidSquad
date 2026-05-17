I've reviewed TEST-PLAN-8704.md against CONTEXT.md §5.6 acceptance criteria, §3.8 HITL design, §5.7 TUI architecture, and the stated review criteria. Here are my findings:

---

### Finding 1

- **File**: .squidsquad/pm/planning/TEST-PLAN-8704.md
- **Line**: 40–42 (AC3), 44–46 (AC6), and all of §3–§4
- **Severity**: error
- **Issue**: No test verifies the full set of required response fields per AC3/AC6. AC3 mandates "issue number, title, role that transitioned to human, status label, priority label, and the timestamp of transition." AC6 mandates the panel renders "number, title, role-that-transitioned, transition timestamp." Across all unit and integration tests, only issue numbers are systematically verified.
- **Evidence**:
  - TC-U1 (line 63): verification checks only `i['number']` — no assertions on `title`, `status`, `priority`, `role`, or `timestamp`.
  - TC-U2 (line 70): verification checks ordering only, not field presence.
  - TC-I1 (line 107): mentions role and timestamp in the *expected* narrative but the *verification* step says "panel screenshot (or text capture) lists the issue with role `skill` and a transition timestamp" — no programmatic assertion on JSON field completeness.
  - No test anywhere parses the JSON response and asserts `all(k in item for k in ('number','title','role','status','priority','transitioned_at'))` or equivalent.
- **Suggested fix**: Add a dedicated unit test (e.g., TC-U1b or expand TC-U1) that asserts each returned item contains all six fields with non-null values, and at least one item is checked for correct field *values* (title matches seed data, status matches the specific `pending-human-*` label, priority matches seed, timestamp is ISO-8601 parseable).

---

### Finding 2

- **File**: .squidsquad/pm/planning/TEST-PLAN-8704.md
- **Line**: 48 (AC12) and the entirety of §3–§7
- **Severity**: error
- **Issue**: AC12 — "existing per-issue notification surfaces (Discussion comments, email-on-mention) continue to function alongside the new queue" — has zero test coverage. No unit, integration, negative, TUI, or manual smoke test verifies this backward-compatibility requirement.
- **Evidence**:
  - Scanning all test sections (§3 Unit, §4 Integration, §5 Negative, §6 TUI, §7 Manual smoke): no test mentions Discussion comments, email-on-mention, or notification surfaces.
  - The AC is listed verbatim at line 48 but never referenced again.
  - The "zero-gap gate" (line 19) states "any TC failure routes the task back to dev. No 'noted for follow-up' exceptions." An acceptance criterion with zero test coverage violates this gate by definition — it cannot fail because it is never exercised.
- **Suggested fix**: Add a test (likely manual smoke, since email-on-mention is a GitHub platform behavior) that: (a) transitions an issue to `pending-human-*`, (b) verifies the item appears in `/human/queue` AND the assignee/mentioned user receives a notification (or at minimum, a Discussion comment is posted as part of the transition and is visible on the issue), (c) both surfaces are functional. If fully automated verification of email delivery is impractical, the test should at minimum verify the Discussion comment pathway works.

---

### Finding 3

- **File**: .squidsquad/pm/planning/TEST-PLAN-8704.md
- **Line**: 138–146 (TC-I4)
- **Severity**: warning
- **Issue**: The positive test for designer-as-ordinary-worker (the core behavioral claim of AC7 "HITL is role-agnostic" and AC9 "designer-loop special-casing removed") is conditional and may never execute. TC-I4's precondition says "Active dev agents in `config.md` include at minimum `skill`, `qa`" — designer is not required to be active. The expected result says "Designer role items appear **if** a designer agent transitioned one." If designer is not in the active role set, the test silently skips the designer case while still passing, creating a false sense of coverage.
- **Evidence**:
  - TC-I4 line 143: "Designer role items appear if a designer agent transitioned one (CONTEXT.md §3.8 — designer is just another worker)."
  - TC-N2 covers the *negative* case (design:needed alone doesn't surface), which is good.
  - But the *positive* case — that a `designer` role transition to `pending-human-*` surfaces identically to `skill`/`qa`/`dm` — is gated on an optional precondition.
  - CONTEXT.md §3.8 states unambiguously: "Designer is a worker role with the same lifecycle as skill / qa / dm" and AC7 says "including designer." The test plan should not make verifying this optional.
- **Suggested fix**: Either (a) change TC-I4's precondition to require `designer` as an active role (add it to the "at minimum" list), or (b) add a separate test (TC-I4b) that explicitly seeds a `pending-human-*` item transitioned by the `designer` role and verifies it appears in the queue with `role: designer` attribution. The latter is preferable as it isolates the designer case.

---

### Finding 4

- **File**: .squidsquad/pm/planning/TEST-PLAN-8704.md
- **Line**: 107–110 (TC-I1 verification)
- **Severity**: warning
- **Issue**: TC-I1's verification step relies on manual inspection ("panel screenshot (or text capture)") for what is classified as an Integration test (§4). The "zero-gap gate" (line 19) routes any TC failure back to dev, but a screenshot-based verification cannot be part of an automated gate — it requires human judgment on every run.
- **Evidence**:
  - Line 109: "Issue number present in JSON response; panel screenshot (or text capture) lists the issue with role `skill` and a transition timestamp."
  - The JSON response check is automatable. The panel content check is not — "text capture" is ambiguous (does it mean scraping the TUI output?).
  - TC-I2 (line 122) has the same pattern: "Item number absent in JSON; panel no longer renders it."
  - If the TUI renders to stdout/stderr, this could be automated with output capture. But the test plan doesn't specify how TUI output is captured programmatically, leaving the verification method unspecified.
- **Suggested fix**: Specify that TUI panel content is verified by capturing the TUI process's rendered output (e.g., via a test mode that dumps panel state to stdout as JSON or plaintext on each refresh tick). If the TUI cannot be driven headlessly, reclassify the panel-rendering portion as a manual smoke test and keep only the JSON endpoint assertions in the integration test.

---

### Finding 5

- **File**: .squidsquad/pm/planning/TEST-PLAN-8704.md
- **Line**: 19 ("Zero-gap gate"), 167–169 (§7 Manual Smoke Tests)
- **Severity**: warning
- **Issue**: The test plan declares a "zero-gap gate: any TC failure routes the task back to dev" but then classifies three tests as "Manual smoke" (§7) with no automation path. Manual tests cannot be part of a zero-gap automated gate — a human must run them, and "failure" is a human judgment call. This creates ambiguity about whether the gate is truly zero-gap or aspirational.
- **Evidence**:
  - Line 19: "Zero-gap gate: any TC failure routes the task back to dev. No 'noted for follow-up' exceptions."
  - SM-1 through SM-3 (lines 167–169): all require human observation ("Observe it appears," "Observe it disappears," "Observe TUI panel orders").
  - If the gate applies to all tests (TCMap §2 includes Manual smoke), these tests cannot be part of an automated gate. If the gate excludes manual tests, the test plan doesn't state this.
- **Suggested fix**: Clarify the scope of the zero-gap gate: either (a) state that manual smoke tests are exempt from the automated gate and are run once by a human at ship-review time, or (b) convert SM-1/SM-2/SM-3 to automatable integration tests (the "observe TUI panel" steps can use the same output-capture mechanism suggested for Finding 4). Option (a) is simpler and consistent with the manual nature of smoke tests.

---

### Summary

| # | Severity | Issue |
|---|----------|-------|
| 1 | error | AC3/AC6 field completeness: no test verifies all six required response fields are present and correct |
| 2 | error | AC12 backward compatibility: zero test coverage for Discussion comments / email-on-mention |
| 3 | warning | Designer-as-worker positive case is conditional in TC-I4; may silently skip the key AC7/AC9 behavioral claim |
| 4 | warning | TC-I1/I2 panel verification uses unspecified manual capture; undermines automated gate for §4 integration tests |
| 5 | warning | Zero-gap gate vs. manual smoke test classification creates ambiguity about gate scope |