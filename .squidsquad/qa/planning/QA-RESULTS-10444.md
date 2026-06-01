# QA-RESULTS-10444 — PRD-B / Story B1: assemble LLM call scaffolding (per-slot)

**Verified**: 2026-06-01 06:08
**Branch**: `squidsquad/task/10444` @ `7095e1bf`
**PR**: #10642
**Verifier**: qa-lead
**Result**: **FAIL — AC5 gap; routing back to in-progress**

## Scope Check

Single feature commit `7095e1bf`:
- `references/prompts/assemble.md.j2` (new, +31)
- `references/scripts/assemble_pass.py` (new, +108)
- `references/scripts/model_router.py` (+1 — register `assemble` task type)
- `tests/test_assemble_pass_b1.py` (new, +179)
- `tests/run_tests.py` (+1)

## Acceptance Criteria

| # | AC | Evidence | Status |
|---|---|---|---|
| 1 | model_router task type `assemble` + prompt template at canonical path | `test_model_router_recognizes_assemble_task_type` + `test_assemble_template_exists_at_canonical_path` + `test_assemble_template_includes_required_preservation_directives` | PASS |
| 2 | `assemble_slot(slot_name, linked_body)` calls model_router | `test_assemble_slot_dispatches_to_router_for_normal_slots`, `test_assemble_slot_writes_linked_body_to_input_file_for_router`, `test_assemble_slot_passes_slot_name_into_router_context`, `test_assemble_slot_returns_router_output_verbatim`, custom-task-id variants | PASS |
| 3 | Verbatim pass-through for project-context + vault | `test_assemble_slot_returns_verbatim_for_special_slots` parametrized × 2 + `test_assemble_slot_verbatim_pass_through_with_empty_body` (also asserts router NOT invoked) | PASS |
| 4 | Unit tests with stubbed model_router (no live LLM in unit tests) | All 14 tests use stubbed `model_router`; test at line 54 explicitly asserts "verbatim slots must not invoke the router" | PASS |
| 5 | **Smoke test against a real fixture confirms LLM is invoked + body returned** | **MISSING.** Skill comment: "Live-LLM smoke test deferred (belongs in B2 integration / B8 golden-file)." | **FAIL** |

## Defense-in-Depth Extras (would be good if AC5 were met)

- `test_assemble_slot_raises_when_router_returns_nonzero` — error path on router non-zero exit.
- `test_assemble_slot_raises_when_router_writes_no_output` — error path on missing output.

## Gap Analysis (AC5)

AC5 text: "Smoke test against a real fixture confirms LLM is invoked + body returned." This is distinct from AC4 ("Unit tests with stubbed model_router"). The AC explicitly calls out a fixture-based smoke test, not just dispatch-shape unit coverage. Skill's deferral to "B2 integration / B8 golden-file" is a scope-shift to other not-yet-shipped stories; it does not satisfy this story's AC.

Per [[feedback_no_ship_with_gaps]] (any QA gap = back to dev, not "noted for follow-up") and [[feedback_no_ship_failed_tc]] (any TC failure = back to dev). The fact that AC4 passes does not cover AC5 — they are distinct ACs.

## Suggested Remediation Paths (dev's choice)

1. Add a smoke test that exercises `assemble_slot` against a real model_router with a small fixture body — could be `pytest.mark.live_llm` and gated on an env flag or API-key presence, so it doesn't run in CI by default but exists in the repo and can be manually invoked. Document in test docstring how to run it.
2. Or, get PM approval to scope-shift AC5 to a downstream story explicitly in this issue's body (not just a skill-side defer comment), then re-route pending-test.

## Test Execution

`pytest tests/test_assemble_pass_b1.py -q` on `7095e1bf` → **14 passed in 0.11s** (AC1-AC4 confirmed; AC5 has no test).

## Outcome

AC1-AC4 PASS. AC5 has no implementation in this PR. Routing **#10444: pending-test → in-progress** for AC5 remediation.
