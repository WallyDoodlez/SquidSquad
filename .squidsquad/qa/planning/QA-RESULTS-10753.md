# QA-RESULTS-10753 — PRD-C audit findings (1 ERROR + 3 WARNINGS)

**Verified**: 2026-06-02 10:40
**Branch**: `skill/issue-10753-prd-c-audit` @ `52d8c77f`
**PR**: #10758
**Verifier**: qa-lead
**Result**: **PASS**

## Audit Finding Resolution

| Finding | Disposition | Evidence |
|---|---|---|
| **ERROR** — C8 Gate 0 prompt template not registered in `model_router.template_map` | **FIXED** | `model_router.py:543-553` now registers `"l4-conflict-preempt": "l4-conflict-preempt.md.j2"`. **Live verify**: `model_router._load_prompt_template('l4-conflict-preempt')` returns the actual template (begins "You are a strict reviewer running a CONFLICT PRE-EMPTION check..."). Gate 0 was running in DEGRADED MODE since C8 shipped — falling back to bare generic prompt and stripping the contradiction-vocabulary + sub-skill exemption + step-id locality rules. This is fixed at the source. |
| **W1** — Gate-count drift in `l4-curation.md` ("four" vs "three" vs "six" gates) | **FIXED** | `l4-curation.md` now reads: "the **six safety gates** (Gate 0 conflict pre-emption → Gate 1 DeepSeek audit → Gate 2 mini-CQ → Gate 3 compose dry-run → Gate 4 atomic write/commit/push → Gate 5 recompose recovery)". Step 8 explicitly enumerates Gate 0. `docs/prd/compose-l4-customization.md` reconciled to match. v1 goldens regenerated (PM/DM/verifier/worker each +18 lines absorbing the reconciled prose). |
| **W2** — `wait_for_recompose` returns `status="failure"` on missing config (orchestrator returns `"skip"`) | **FIXED** | Standalone path now returns `"skip"` symmetrically. `tests/test_l4_recompose_recovery_c7.py +28` adds the regression coverage. Contract is now uniform across direct + orchestrated callers. |
| **W3** — C4 mini-CQ head-token allowlist gap; "do it now"/"ship it please"/"y please" classified ambiguous | **FIXED** | Approval-prefix-with-negation-in-rest guard: an approval token at the prefix is honored unless the rest contains an explicit negation/dismissal. Tests pin all three originally-flagged phrases + DS-caught false-positives (`go away`, `go back`, `y not`, `do it not`, `ok never`, `yes not really`) so the relaxation cannot over-fire. |

## DS Review Catches

Skill ran DS review per `feedback_ds_review_per_change` and DS surfaced 3 additional findings, all fixed pre-commit:

- **`go away` / `go back`** — "go" is a one-word approval prefix; the dismissal word in the rest must demote to ambiguous
- **`y not` / `do it not` / `ok never` / `yes not really`** — approval prefix followed by negation → must NOT approve
- **Dead param** (third DS finding, fixed) — refactor cleanup

These would have shipped silently — DS-review-per-change caught them. Regression tests pin all three failure modes.

## Live ERROR Verification

`python -c "import model_router; print(bool(model_router._load_prompt_template('l4-conflict-preempt')))"`
- BEFORE fix: returns `False` → Gate 0 falls back to bare generic prompt → DEGRADED MODE
- AFTER fix: returns `True` + template content begins with "You are a strict reviewer running a CONFLICT PRE-EMPTION check..."

Gate 0 now runs with its authored prompt as intended since C8 (#10657).

## v1 Coexistence

§9a v1 byte-stability gate: regenerated to absorb the reconciled gate-count prose in `l4-curation.md` (the prose change is per-role inherited; goldens +18 lines for pm/dm/verifier, +36 for worker per role-fanout). The gate stays GREEN against the new baseline — confirming the prose reconciliation is the ONLY v1-visible change.

## Test Execution

`pytest tests/test_model_router.py tests/test_l4_mini_cq_c4.py tests/test_l4_recompose_recovery_c7.py tests/test_v1_byte_stability_9a.py -q` on `52d8c77f` → **224 passed**.

Skill reported "268 tests pass in scope, 358 wider" — my 224-pass cut covers the core fix surface (model_router + mini_cq + recompose_recovery + §9a).

## E6 Gate Status

Per issue body + PM's PT comment: "**Gate**: ERROR (C8 Gate 0 template not registered) MUST be resolved before E6 #10685 V2 CUTOVER — Gate 0 in degraded mode is unsafe for cutover." → **gate cleared by this PR**.

## Scope Discipline

All 4 findings fixed in-PR; no deferrals to follow-ups. DS-caught regressions baked in pre-commit. Goldens regenerated to keep §9a accurate. v1 byte-stability gate intentionally re-baselined for the prose reconciliation (legitimate evolution, not a regression — the prose was internally inconsistent BEFORE, consistent NOW).

## Outcome

ERROR fixed (Gate 0 degraded mode resolved) + all 3 warnings fixed + DS-caught secondary bugs all pre-shipped with regression coverage. E6 hard-gate cleared. **Transitioning #10753: pending-test → pending-ship.**
