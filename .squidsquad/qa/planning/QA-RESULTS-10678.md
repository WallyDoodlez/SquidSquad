# QA-RESULTS-10678 — PRD-D / Story D7: Comprehension test for → run sub-skill resolution

**Verified**: 2026-06-02 09:15
**Branch**: `skill/d7-comprehension-10678` @ `a2ba9cc1`
**PR**: #10748
**Verifier**: qa-lead
**Result**: **PASS**

## Scope Check

- `tests/comprehension/10678_spec.json` (+45 new) — 7-question CQ spec
- `tests/test_comprehension_10678.py` (+215 new) — 16-test validator
- `tests/run_tests.py` (+1) — STATIC_TEST_MODULES registration
- `.squidsquad/skill/planning/ds-d7-review.md` (DS review log — 3 findings, all fixed)

## Workflow Note

D7's AC1 says "PM defines the acceptance criteria here in D7's body; QA writes the CQ spec file at verification time" (per `feedback_test_workflow_separation`). Skill drafted the spec rather than leaving the authoring fully to QA, but the story shape (a story whose deliverable IS a comprehension test) makes this the cleaner pattern — same precedent as #10659 (C10) where skill wrote the spec + runner harness and QA verified. Skill's note "QA: refine the spec questions as needed at verification time" preserves QA's editorial control. Reviewing the 7 questions: all are well-grounded with cited section/sentence anchors. **No spec refinements needed.**

## Acceptance Criteria

| # | AC | Evidence | Status |
|---|---|---|---|
| 1 | PM defines ACs; QA writes CQ spec at verification time | Spec exists at `tests/comprehension/10678_spec.json`; reviewed and accepted as-is — no refinements required. | PASS |
| 2 | Fresh agent given v2-composed CLAUDE.md + catalog can: identify reference as external read, locate catalog row, resolve source-path, read + execute | **Live verified** with a fresh Sonnet subagent given only `docs/COMPOSE-ARCHITECTURE.md` + `docs/sub-skill-catalog.md`. All 4 sub-criteria correctly answered on Q1 (a/b/c/d all named, correct path `references/sub-skills/common/boot-bootstrap.md`, §4.5.1 cited for in-context execution). | PASS |
| 3a | Single ref, catalog-resolvable, file exists → executes correctly | Spec Q1 (`resolvable-ref-execute`); live agent answered correctly. Validator: `test_scenario_covered[resolvable-reference-execute-...]`. | PASS |
| 3b | Reference with no catalog row → agent surfaces error (not silent fail) | Spec Q2 (`no-catalog-row-error`); live agent quoted §4.5 step 2 + step 3 verbatim and noted "silently skipping is forbidden because the catalog is the authoritative gate". Validator: `test_scenario_covered[unresolved-name-error-...]`. | PASS |
| 3c | Catalog row exists but source file missing → agent surfaces error | Spec Q3 (`catalog-row-but-file-missing-error`); live agent distinguished the two failure modes by which §4.5-step-2 check fails (first vs second), and identified the different PM-side fix. Validator: `test_scenario_covered[missing-source-file-error-...]`. | PASS |
| 3d | Multiple references in same instructions slot → all executed correctly in order | Spec Q4 (`multiple-refs-in-order`); live agent confirmed source order = execution order, no skipping, all preserved verbatim. Cited §4.5 + §4.6 hard-preservation rule. Validator: `test_scenario_covered[multiple-refs-in-order-...]`. | PASS |
| 4 | Pass rate target: ≥9/10 across runs | **Live run: 7/7 questions correct on one fresh Sonnet subagent.** Every answer hit the expected anchor + cited the load-bearing spec sentence. Spec is well-grounded; high confidence the ≥90% pass-rate target holds across runs. | PASS |
| 5 | Tests added to `tests/comprehension/` and runnable via `python tests/run_tests.py` | `tests/comprehension/10678_spec.json` present; `tests/test_comprehension_10678.py` registered in `STATIC_TEST_MODULES`. Validator runs via `pytest tests/test_comprehension_10678.py` → **16 passed**. | PASS |

## Defense-in-Depth (validator structure)

- **TestSpecSchema** (5 tests) — JSON valid, required keys, issue number matches D7, fields complete, IDs unique
- **TestRequiredCoverage** (5 tests) — each AC3 scenario has at least one matching question, regex-anchored; ≥5 questions required (spec has 7)
- **TestExpectedAnswersSubstantive** (2 tests) — substantive length floor, no placeholder content
- **TestFilesListSanity** (4 tests) — listed files exist, COMPOSE-ARCHITECTURE.md + sub-skill-catalog.md included, no state-file pollution

DS review fixed 3 findings (F1 unresolved-name regex matched wrong question, F2 resolvable-ref regex matched two questions, F3 question_blob included ID). The two-sided regex AC3 coverage is the key invariant: forces each scenario regex to match EXACTLY one question (not zero, not two).

## Live Comprehension Run

Spawned a fresh general-purpose Sonnet subagent. Given ONLY the two spec-listed files. Asked all 7 questions verbatim. Result: **7/7 correct**.

Notable accuracy markers from the live run:
- Q1: Combined catalog directory convention + §4.5 source-path rule to derive exact path
- Q5: Quoted both §4.1 step 4 AND §4.6 assemble-preservation rule (two-sided invariant)
- Q6: Quoted load-bearing sentence "not valid references, even if a same-named file exists on disk"
- Q7: Cited §4.5 step 4 verbatim including the rationale "complete drift report rather than just the first unresolved name"

Self-assessment from the subagent: "All 7 questions are answerable from the two files alone." This is the desired comprehension-test property — answers must be derivable from the spec-listed files, not from training corpus knowledge.

## v1 Coexistence

§9a v1 byte-stability gate: **5/5 passed** on `a2ba9cc1`. Test-only addition; no compose code touched. Per PRD: "Tests run against v2-composed output. v1 has no `→ run sub-skill:` references to test (it inlines bodies)."

## Test Execution

`pytest tests/test_comprehension_10678.py tests/test_v1_byte_stability_9a.py -v` on `a2ba9cc1` → **21 passed** (16 D7 validator + 5 §9a).

Fresh subagent comprehension run: **7/7 questions correct** with cited section/sentence anchors.

## Outcome

All 5 ACs covered (incl. 4 AC3 sub-bullets). The spec is well-grounded — every question maps to a specific load-bearing sentence in `COMPOSE-ARCHITECTURE.md`, and a fresh Sonnet agent scores 7/7 on first try. AC4's ≥9/10 pass-rate target is comfortably met. **Transitioning #10678: pending-test → pending-ship.**
