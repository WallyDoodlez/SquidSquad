# Iteration 222 — 2026-06-16 00:39 (POLLING) — IMPROVEMENT SCAN

**Pull**: up to date, no new commits. **PT scan (list-issues) → 0.**

**Improvement scan (fresh surface: #12475 tracker.py shipped):** investigated a cy221 discrepancy — `list-issues skill --status in-progress` returned only #10855, omitting #12460 (both status:in-progress + role:skill).

**Finding (QA-process gap, NOT a code bug):** `tracker.py list-issues <role>` defaults `issue_type="bug"` → filters **type:issue ONLY**; `list-tasks` filters **type:task ONLY** (disjoint). My PT scan loop has been `list-issues`-only — it catches only type:issue and would **silently miss any type:task in pending-test**. The entire upcoming queue (#12460 cutover, #12419/#12420/#12450/#12451 installer/status tasks) is type:task → gap was imminent (no item missed *yet* — all currently in-progress/approved, not pending-test).

**Verification of the gap:**
- `list-tasks <role> --status pending-test` → 0 (all roles) — nothing missed currently.
- `list-by-labels "status:pending-test"` → 0, **type-agnostic, all roles in one call** — adopting as canonical PT scan.
- `work-queue` is NOT a substitute (dev pickup queue; skips pending-test, tracker.py:676).

**Action:** adopted `list-by-labels "status:pending-test"` as the canonical PT scan going forward. Saved durable memory `feedback_pt_scan_must_be_type_agnostic`. tracker.py behavior is correct/documented — nothing to file against the codebase.

**Pickup:** 0 pending-test (confirmed type-agnostic). #12460 + #10855 in-progress at skill; #12419/#12420/#12450/#12451 approved.

**Outcome:** productive improvement-scan cycle. Quiet-cycle counter → 0.
