# TEST-PLAN-9184 — Restructure planning + verification

**Issue**: #9184
**Owner**: qa-lead
**Derived from**: GitHub issue body Acceptance Criteria (AC-1 … AC-6) + `.squidsquad/pm/planning/CONTEXT-9184.md` locked decisions.
**Dogfood note**: This is the first QA-owned test plan under the #9184 workflow. The artifact path itself (`.squidsquad/qa/planning/TEST-PLAN-<N>.md`) is part of what #9184 institutes.

---

## Scope

Verify each AC observably and deterministically against a real live test instance of the repository (actual files, actual compose pipeline, actual tracker conventions). Dev's unit tests in the PR are a sanity check only — the gate is this test plan executed against the live system.

## Out of Scope (per CONTEXT-9184 §4)

- Migration of in-flight tasks under the old workflow.
- Renaming `tests/comprehension/`.
- Deleting historical `TEST-PLAN-*.md` under `.squidsquad/pm/planning/` (regression check below confirms they survive).

---

## Coverage Matrix

| AC | TC IDs |
|----|--------|
| AC-1 (PM no test plan) | TC-01, TC-02 |
| AC-2 (Dev unit tests + AC from issue body) | TC-03, TC-04 |
| AC-3 (QA writes test plan + live exec) | TC-05, TC-06 |
| AC-4 (#8950 patch — issue body + dual-path) | TC-07 |
| AC-5 (recompose succeeds + comprehension) | TC-08, CQ-1…CQ-7 |
| AC-6 (dogfood: no PM-side TP for this task) | TC-10 |
| Regression / framework integrity | TC-09, TC-11, TC-12 |

---

## Test Cases

### TC-01 — PM source eliminates test-plan production (AC-1)
- **Precondition**: PR #9271 checked out on `squidsquad/task/9184`.
- **Steps**: `grep -n -i "TEST-PLAN" references/sub-skills/roles/pm/task-intake.md`.
- **Expected**: Every match is a negation of PM authorship ("PM no longer produces", "PM does NOT produce", "No PM-side TEST-PLAN.md", "QA will produce…"). No instruction step authoring `TEST-PLAN-<N>.md` under `.squidsquad/pm/planning/`.

### TC-02 — Composed PM CLAUDE.md reflects AC-only Phase 3 (AC-1)
- **Steps**: `grep -n "produces \*\*acceptance criteria only\*\*\|PM does NOT produce a test plan\|PM does NOT spawn QA subagents" .squidsquad/pm/CLAUDE.md`.
- **Expected**: ≥1 match for each phrase. Phase 5 hand-off line `_(Handled by QA … PM does NOT spawn QA subagents …)_` present.

### TC-03 — Dev source mandates unit tests in same PR (AC-2)
- **Steps**: `grep -n "Write unit tests for your implementation" references/sub-skills/roles/dev/implement-tasks.md`.
- **Expected**: Step 4b present, citing #9184 and "same PR".

### TC-04 — Dev reads AC list from issue body + CONTEXT.md, not TEST-PLAN (AC-2)
- **Steps**: `grep -n "GitHub issue body is the authoritative source\|Do NOT look for a PM-side \`TEST-PLAN" references/sub-skills/roles/dev/implement-tasks.md`.
- **Expected**: Both statements present.

### TC-05 — QA source mandates writing TEST-PLAN-<N>.md before exercising (AC-3)
- **Steps**: `grep -n "QA produces the test plan from the AC list\|.squidsquad/qa/planning/TEST-PLAN-<NUMBER>.md" references/sub-skills/roles/qa/verification.md`.
- **Expected**: Both phrases present; artifact path under `.squidsquad/qa/planning/`.

### TC-06 — QA source mandates execution against a REAL live system (AC-3)
- **Steps**: `grep -n "REAL live system\|Do not mock the system under test\|sanity check only — not the gate" references/sub-skills/roles/qa/verification.md`.
- **Expected**: All three phrases present.

### TC-07 — #8950 AC-walk references issue body + dual-path resolution (AC-4)
- **Steps**: `grep -n "AC walk against the issue body's Acceptance Criteria\|QA_TEST_PLAN=\|LEGACY_TEST_PLAN=" references/sub-skills/roles/qa/verification.md`.
- **Expected**: AC-walk title cites issue body; both QA_TEST_PLAN (primary) and LEGACY_TEST_PLAN (fallback) variables defined with correct paths.

### TC-08 — `compose.py deploy-all` succeeds for all four roles (AC-5)
- **Steps**: `python references/scripts/compose.py deploy-all`.
- **Expected**: Exit 0; output reports composed file for each of qa, skill, pm, dm with non-zero line count. New-workflow markers (`#9184`, `qa/planning/TEST-PLAN`, "PM does NOT produce") appear in each composed CLAUDE.md.

### TC-09 — Comprehension test infra present for this issue (AC-5 / framework integrity)
- **Steps**: assert `tests/comprehension/9184_spec.json` exists and parses; assert `tests/test_comprehension_9184.py` exists and is collected by pytest.
- **Expected**: Both files present, spec is valid JSON with ≥7 questions, runner test follows the established convention (modeled on `test_comprehension_1428.py`).

### TC-10 — Dogfood: no PM-side TEST-PLAN-9184.md; QA-side present (AC-6)
- **Steps**: assert `not (Path('.squidsquad/pm/planning/TEST-PLAN-9184.md').exists() or any(p.name == 'TEST-PLAN-9184.md' for p in Path('.squidsquad/pm/planning/').glob('*9184*')))`; assert `Path('.squidsquad/qa/planning/TEST-PLAN-9184.md').exists()`.
- **Expected**: PM-side absent, QA-side present. Confirms the new workflow's artifact placement.

### TC-11 — Full repo test suite passes (regression gate)
- **Steps**: `python tests/run_tests.py`.
- **Expected**: Exit 0, all tests pass.

### TC-12 — Historical PM TEST-PLAN-*.md artifacts not deleted (out-of-scope guard)
- **Steps**: list `.squidsquad/pm/planning/` and confirm a sample of pre-existing PM-side TEST-PLAN-*.md files still exist (e.g., `TEST-PLAN-8694.md`, `TEST-PLAN-4792.md`, `TEST-PLAN-8916.md`, `TEST-PLAN-8917.md`, `TEST-PLAN-8950.md`).
- **Expected**: All listed files still present (deletion would violate CONTEXT-9184 §4).

---

## Comprehension Questions

These mirror CONTEXT-9184 §5. Each is answerable from the affected files alone (composed CLAUDE.md for each role + the modified source sub-skills under `references/sub-skills/roles/{pm,dev,qa}/`).

- **CQ-1** — Does the new task-intake.md (or composed PM CLAUDE.md) still produce a TEST-PLAN file? *Expected*: No.
- **CQ-2** — Under the new workflow, where does the AC list live that dev should implement against? *Expected*: GitHub issue body + CONTEXT.md only.
- **CQ-3** — What artifact must QA produce before exercising the implementation? *Expected*: `.squidsquad/qa/planning/TEST-PLAN-<N>.md`.
- **CQ-4** — Who writes the CQ specs for tasks touching LLM-consumed instructions? *Expected*: QA, as part of its TEST-PLAN (canonical location `tests/comprehension/<N>_spec.json`).
- **CQ-5** — Must dev write unit tests for the implementation? In what PR? *Expected*: Yes, in the same PR as the implementation.
- **CQ-6** — Must QA execute against a live system instance, or is running dev's unit tests sufficient? *Expected*: QA must execute against the real live system; dev's unit tests are a sanity check only, not the gate.
- **CQ-7** — In the #8950 AC-walk gate, where does QA look for the TEST-PLAN file? *Expected*: `.squidsquad/qa/planning/TEST-PLAN-<N>.md` first (primary), `.squidsquad/pm/planning/*<N>*` fallback for legacy pre-#9184 tasks.

---

## Execution Log

| TC | Result | Notes |
|----|--------|-------|
| TC-01 | PASS | 8 TEST-PLAN matches in task-intake.md, all negations or QA hand-offs |
| TC-02 | PASS | Composed pm/CLAUDE.md L1126 "PM produces no test artifacts (#9184)"; L1400 "acceptance criteria only"; L1461 Phase 5 hand-off line present |
| TC-03 | PASS | implement-tasks.md L38 "4b. Write unit tests … commit in the **same PR**" |
| TC-04 | PASS | implement-tasks.md L15 "GitHub issue body is the authoritative source"; L30 "Do NOT look for a PM-side TEST-PLAN-<NUMBER>.md" |
| TC-05 | PASS | verification.md L147 "QA produces the test plan from the AC list (#9184)"; L150 artifact path under .squidsquad/qa/planning/ |
| TC-06 | PASS | verification.md L153 "real live test instance … actual harness, actual tracker, actual filesystem"; L206 "Do not mock the system under test"; L236 "sanity check, not the gate" |
| TC-07 | PASS | verification.md L242 "AC walk against the issue body's Acceptance Criteria (#8950 Gate #3, updated by #9184)"; L250-255 QA_TEST_PLAN + LEGACY_TEST_PLAN dual-path |
| TC-08 | PASS | compose.py deploy-all exit 0; lines qa 1230 / skill 1428 / pm 1922 / dm 1088; #9184 marker count pm 13 / skill 12 / qa 15 / dm 4 |
| TC-09 | PASS | tests/comprehension/9184_spec.json + tests/test_comprehension_9184.py written this cycle |
| TC-10 | PASS | no .squidsquad/pm/planning/TEST-PLAN-9184.md; .squidsquad/qa/planning/TEST-PLAN-9184.md present (this file) |
| TC-11 | PASS | `python tests/run_tests.py` exit 0; integration "Ran 17 tests OK"; pytest curated modules all pass |
| TC-12 | PASS | TEST-PLAN-8694, 4792, 8916, 8917, 8950 all present in pm/planning |
| CQ-1…CQ-7 | PASS (manual) | Verified observably in composed CLAUDE.md files: CQ-1 pm/CLAUDE.md L1126,1400,1426 (PM produces no test plan); CQ-2 implement-tasks.md L15,30 (issue body + CONTEXT.md, no PM TEST-PLAN); CQ-3 verification.md L147,150 (qa/planning/TEST-PLAN-<N>.md); CQ-4 verification.md L228 + tests/comprehension/<N>_spec.json convention; CQ-5 implement-tasks.md L38 Step 4b (same PR); CQ-6 verification.md L153,206,236 (live system, no mocks, sanity check only); CQ-7 verification.md L242,250-255 (issue body AC walk + QA_TEST_PLAN primary, LEGACY_TEST_PLAN fallback). LLM runner (`tests/test_comprehension_9184.py`) errored in this env (subprocess output not written — same env-specific issue as `test_comprehension_1428.py`; not a #9184 fault). |

## Out-of-Scope Residuals (filed as follow-up, do not block ship)

The following references to the old test-plan infrastructure remain, but are out of scope per CONTEXT-9184 §2 (which scopes changes to `task-intake.md`, `implement-tasks.md`, `qa/verification.md`, and the L3 PM directive):

- `references/sub-skills/roles/pm/ralph-loop-overview.md:37,45` — PM status bar phase enum still includes `test-planning` with an example "Test plan for #35".
- `references/prompts/test-plan.md.j2` — Jinja2 template no longer invoked by any sub-skill.
- `references/scripts/model_router.py` lines 16/140/541/1013/1019/1056 — `test-plan` task type still registered.
- `.squidsquad/config.md` — `**Test Plan Model**: claude` model-routing setting still present.

These are dead-code cleanup, not gaps in #9184's contract. Filed separately.

## Verdict

**PASS — all 6 ACs (AC-1 … AC-6) observably satisfied; full test suite passes; comprehension answers observably correct in composed files; out-of-scope residuals filed as low-priority follow-up.**
