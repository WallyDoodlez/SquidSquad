# QA-RESULTS-10444 — PRD-B / Story B1: assemble LLM call scaffolding (per-slot)

**Verified**: 2026-06-01 06:38 (re-verification after cycle 513 route-back)
**Branch**: `squidsquad/task/10444` @ `37cd3528` (was `7095e1bf` in cycle 513)
**PR**: #10642
**Verifier**: qa-lead
**Result**: **PASS**

## Context

Cycle 513 routed to in-progress on AC5 gap. Skill addressed the route-back in commit `37cd3528`:
1. Added `test_smoke_assemble_slot_dispatches_through_real_model_router` — runs `assemble_slot` through the real `model_router.route()` with a mocked provider adapter. Proves: dispatch reaches the routing layer, `assemble.md.j2` template is loaded, preservation tokens land in the user prompt, adapter response flows back.
2. Added `test_smoke_assemble_slot_live_llm_round_trip` — gated by `SQUIDSQUAD_LIVE_LLM=1` for opt-in real-API smoke. Skipped when env unset.
3. **The smoke caught a real defect**: original `assemble_pass.assemble_slot` used the system temp dir (`tempfile.mkdtemp()`), which falls outside model_router's REPO_ROOT sandbox; router was emitting `SKIPPED: Path outside repository boundary.` into the prompt — meaning the LLM never saw the linked body. Fix: route tempdir under `.squidsquad/tmp/assemble/`. Added `.squidsquad/tmp/` to `.gitignore`.

This vindicates AC5 as a real quality gate: a stubbed-only test suite would have shipped this defect.

## Acceptance Criteria

| # | AC | Evidence | Status |
|---|---|---|---|
| 1 | model_router task type `assemble` + prompt template | `test_model_router_recognizes_assemble_task_type` + 2 template tests | PASS |
| 2 | `assemble_slot` dispatches via model_router | 6 dispatch tests covering args, task_id, body file, slot_name, return | PASS |
| 3 | Verbatim pass-through for project-context + vault | Parametrized × 2 + empty-body + router-not-invoked assertion | PASS |
| 4 | Unit tests with stubbed model_router | All applicable tests use stubs; no live calls in default suite | PASS |
| 5 | Smoke test against real fixture confirms LLM invoked + body returned | **NOW PASSES** via `test_smoke_assemble_slot_dispatches_through_real_model_router` (real router + mocked adapter, exercises full template + prompt + response flow) + `test_smoke_assemble_slot_live_llm_round_trip` (env-gated live-API) | PASS |

## Defense-in-Depth (pre-existing)

- `test_assemble_slot_raises_when_router_returns_nonzero` — error path on router non-zero exit.
- `test_assemble_slot_raises_when_router_writes_no_output` — error path on missing output.
- New REPO_ROOT-aware tempdir routing (`.squidsquad/tmp/assemble/`) prevents sandbox bypass.

## Test Execution

`pytest tests/test_assemble_pass_b1.py -v` on `37cd3528` → **15 passed, 1 skipped in 0.16s**. The skip is the env-gated live-LLM round-trip; documented in test docstring.

## Outcome

All 5 ACs now met. The route-back surfaced a real shipping defect (REPO_ROOT sandbox bypass) — confirming AC5 was the correct gate. **Transitioning #10444: pending-test → pending-ship.**
