# TEST-PLAN-13464 — verifier verdict forge-discoverability (verification.md ordering)

**Source**: GitHub issue #13464 Acceptance Criteria (AC1/AC2/AC3 authored by PM). Prose-only LLM-consumed instruction change.
**Derived without reading the worker diff.**

## Acceptance Criteria (from issue body)

- **AC1** — Functional ordering precondition: verification.md makes the forge-visible VERIFY verdict comment on the ISSUE a hard, ordered precondition of the pending-test -> pending-ship transition.
- **AC2** — Comprehension coverage (skill-CQ gate): a fresh verifier reading ONLY verification.md, having verified a task PASS, states the ordered next-actions (post verdict comment on the issue THEN the pending-ship transition), unprompted.
- **AC3** — Discoverability regression that would have caught #13373 (verdict landed after the transition -> not discoverable at DM ship-gate).

## Verification method

Prose-only instruction edit -> the comprehension test is the gate (no unit-test surface). Plus a direct read of the changed file for AC1/AC3.

## Test Cases

### TC-1 (AC1): step 5a present + mandatory + hard precondition
- Read verification.md; confirm a step ordering the issue verdict comment BEFORE promote/PR/merge/transition, worded MANDATORY and as a hard precondition of pending-ship.
- Result: PASS (L295-299).

### TC-2 (AC2): fresh-agent comprehension
- Spawn a fresh agent (sonnet), give ONLY verification.md, quiz the ordered post-PASS sequence.
- Result: PASS (4/4 CQs correct; see QA-RESULTS-13464.md + tests/comprehension/13464_spec.json).

### TC-3 (AC3): regression rationale
- Confirm the mandatory rule is exactly what would have surfaced #13373's post-transition verdict gap.
- Result: PASS.

## Coverage matrix
- AC1 -> TC-1
- AC2 -> TC-2
- AC3 -> TC-3

## Comprehension Questions
See tests/comprehension/13464_spec.json (CQ-1..CQ-4, all PASS). Files: references/sub-skills/roles/verifier/verification.md.
