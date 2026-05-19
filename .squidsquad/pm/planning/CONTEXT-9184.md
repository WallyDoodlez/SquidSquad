# CONTEXT-9184 — Restructure planning + verification

**Issue**: #9184
**Owner**: skill (implementation), QA (new responsibility), PM (reduced scope)
**Status**: planning → planned (this cycle)
**Planning lead**: pm-lead (cycle 1496, 2026-05-19)

> **AUTHORITATIVE SCOPE**: the GitHub issue body for #9184 is the authoritative scope. This file documents locked decisions and grounded file references — it does not redefine the ACs.

---

## 1. Locked Decisions (human, 2026-05-19)

1. **PM produces no test artifacts.** Task intake stops at the GitHub issue body + RESEARCH.md + CONTEXT.md. No `TEST-PLAN-<N>.md` under `.squidsquad/pm/planning/` for new tasks.
2. **QA owns AC-derived TEST-PLAN** under `.squidsquad/qa/planning/TEST-PLAN-<N>.md`. QA test plan derives from the issue body's AC list, not from dev's diff.
3. **QA owns CQ specs** for any task touching LLM-consumed instructions. CQs live in QA's test plan + `tests/comprehension/<N>_spec.json`.
4. **Dev writes unit tests** as part of the implementation PR — dev's own correctness check, not the verification contract.
5. **QA executes against a real live test instance** — actual harness, actual tracker, actual filesystem. Running dev's unit tests is a sanity check only; the gate is QA's live execution.
6. **Dogfooded**: this task itself is filed under the new workflow (no PM-side TEST-PLAN-9184.md).

## 2. Grounded File References

Body's affected files confirmed by grep:

### PM — remove test plan production
- `references/sub-skills/roles/pm/task-intake.md`
  - Phase 3 (test plan subagent) — lines 5, 21, 235–236, 273–351 reference TEST-PLAN production
  - Phase 5 (QA subagent) — lines 367, 384–388 spawn QA against PM's TEST-PLAN
  - Remove both phases. Phase 1 (Research) and Phase 2 (CONTEXT) remain.
  - AskUserQuestion at line 235 ("Ready to proceed to test planning?") must change: proceed to "Planned" directly after CONTEXT, no test-plan gate.

### Dev — read AC list from issue body + CONTEXT, write own unit tests
- `references/sub-skills/roles/dev/implement-tasks.md`
  - Line 18 — "TEST-PLAN-<NUMBER>.md (acceptance criteria + comprehension tests)" → remove; AC source is the issue body.
  - Line 21 — "planning artifact is the authoritative scope … `TEST-PLAN-<NUMBER>.md` acceptance criteria in full" → rescope to CONTEXT.md only.
  - Line 36 — "Run smoke tests from TEST-PLAN.md (if it exists)" → drop the TEST-PLAN reference; smoke tests become dev's responsibility, derived from AC.
  - Line 53–57 — "Locate planning artifacts … FEAT-PM-<NUMBER>-TEST-PLAN.md and new TEST-PLAN-<NUMBER>.md" → narrow to CONTEXT-only.
  - Line 73 — model_router context string referencing TEST-PLAN-* → drop.
  - **Add**: explicit step instructing dev to write unit tests covering the implementation, committed in the same PR. (No new step number — append to the existing implementation step.)

### QA — produce TEST-PLAN under qa/planning, execute live
- `references/sub-skills/roles/qa/verification.md`
  - **Add**: AC-1 of QA — read GitHub issue body, derive test plan, write to `.squidsquad/qa/planning/TEST-PLAN-<N>.md` before exercising the implementation. CQ section included when the task touches LLM-consumed instructions.
  - Line 147–168 — "If a TEST-PLAN.md exists in the PM's planning directory" → invert: QA now owns this artifact. The spawn-subagent block becomes "QA executes its own TEST-PLAN against a live instance."
  - Line 178–188 — comprehension testing block → keep, but source CQs from QA's own test plan, not PM's.
  - Line 190 — coverage check on dev's unit tests stays (sanity check).
  - Line 194–204 — AC walk: locate the TEST-PLAN in `.squidsquad/qa/planning/` (new convention) before `.squidsquad/pm/planning/` (legacy). Glob both, prefer qa-side. AC walk itself unchanged.
  - Line 231 — PR comment template "Test Plan: FEAT-…-TEST-PLAN.md" → reference qa-side path.

### #8950 patch (AC-4) — defense-in-depth fragment
- Same `references/sub-skills/roles/qa/verification.md` lines 194–204 implement the #8950 AC-walk gate. The patch is the qa-side path resolution change. No separate file edit.

### L3 PM directive — CQs move to QA
- L3 PM CLAUDE.md fragment currently says "any task adding/changing agent instructions must include comprehension test specs" — need to locate and rewrite to direct QA. Search will be required during implementation (the body cites the memory note `feedback_comprehension_tests_required.md` but the directive itself is in an L3 fragment).

## 3. Sequencing

- **#8916 (CONTEXT.md mandate)** — SHIPPED in main per commit `22061f54` (cycle 1157). The "read CONTEXT.md" portion is now baseline; this task drops the "read TEST-PLAN" portion only.
- **#8917 (body sync on rewrites)** — SHIPPED per commit `c41a6b4c`. Compatible: AUTHORITATIVE SCOPE banner still points at CONTEXT.md.
- **#8950 (defense-in-depth)** — SHIPPED. AC-4 patch rides this task's PR.
- **#8997 (autonomous L4 writes)** — pending, orthogonal. Compatible.

Sequencing constraint satisfied. No external dependencies block this task from picking up immediately on approval.

## 4. Out of Scope (locked)

- Migration of in-flight tasks (`#8999`, `#9243`, etc.) — they complete under the workflow they started in.
- Renaming `tests/comprehension/`.
- Changing tracker labels or status transitions.
- Deleting historical `TEST-PLAN-*.md` artifacts under `.squidsquad/pm/planning/`. They are the historical record.

## 5. Comprehension Test Coverage (owned by QA per the new rule, dogfooded)

When skill picks up implementation, QA will produce `tests/comprehension/9184_spec.json` covering:
- Q1: PM intake — does the new task-intake.md still produce a TEST-PLAN file? (Expected: no.)
- Q2: Dev — when implementing, where does the AC list live? (Expected: GitHub issue body + CONTEXT.md only.)
- Q3: QA — what artifact must QA produce before exercising the implementation? (Expected: `.squidsquad/qa/planning/TEST-PLAN-<N>.md`.)
- Q4: QA — where do CQ specs come from for instruction-touching tasks? (Expected: QA writes them as part of TEST-PLAN.)
- Q5: Dev — must dev write unit tests for the implementation? (Expected: yes, in same PR.)
- Q6: QA — must QA execute against a live system instance? (Expected: yes; dev's unit tests are sanity-check only.)
- Q7: AC-walk gate path resolution (#8950) — where does QA look for the TEST-PLAN? (Expected: `.squidsquad/qa/planning/` first, `.squidsquad/pm/planning/` fallback for legacy.)

(This list is a PM-side hand-off note for QA; QA will write the actual spec.)

## 6. Open Questions for Skill at Pickup

- Should the PM Phase-2 AskUserQuestion ("Approve — proceed to test plan") be replaced with a simpler "Approve — proceed to Planned status" prompt, or removed entirely (CONTEXT done = Planned auto-transition)? Either is acceptable per AC-1; pick one and document.
- Memory note `feedback_comprehension_tests_required.md` — update or delete? Recommend update to reflect the new ownership rather than delete (preserves the reasoning, just changes the actor).
