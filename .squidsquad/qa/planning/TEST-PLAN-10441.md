# TEST-PLAN-10441 — PRD-B / Story B2: assemble preservation verifier

**Source**: issue #10441 ACs.
**Derived without reading the worker's diff.**

## Acceptance criteria
- **AC-1**: `verify_preservation(linked, assembled) -> PreservationResult` in `references/scripts/`.
- **AC-2**: multiset-equality on `→ run sub-skill: <name>` refs.
- **AC-3**: multiset-equality on `step:cycle/<id>` refs.
- **AC-4**: PreservationResult exposes ok, missing_sub_skills, extra_sub_skills, missing_step_ids, extra_step_ids.
- **AC-5**: tests cover identity / missing / extra / dup multiset / no-refs.
- **AC-6**: pure Python, no LLM dep, deterministic.

## Test Cases

### TC-1 (AC-1, AC-4): function exists with documented shape
- Live probe: identity linked==assembled → ok=True, all four list fields empty.

### TC-2 (AC-2): duplicate sub-skill ref collapsed in assembled is detected
- Probe: linked has `→ run sub-skill: a` twice + `→ run sub-skill: b`; assembled drops one `a` → ok=False, `missing_sub_skills=['a']`.

### TC-3 (AC-3): step-id multiset compared with left word-boundary
- Probe: linked `'step:cycle/x prefixstep:cycle/y'`; the `prefixstep:cycle/y` does NOT match (word-boundary on left), so assembled='step:cycle/x' passes — confirms the regex claim.

### TC-4 (AC-5): dev unit suite covers AC-listed cases
- `pytest tests/test_assemble_verifier.py -v` exit 0, 20 tests, ≥5 covering identity/missing/extra/dup/no-refs.

### TC-5 (AC-6): no LLM imports
- AST walk imports: must be subset of `{re, collections, dataclasses, …}` standard lib.

### TC-6 (canonical suite): run_tests.py green on branch.

## Coverage matrix
- AC-1 → TC-1
- AC-2 → TC-2, TC-4
- AC-3 → TC-3, TC-4
- AC-4 → TC-1, TC-4
- AC-5 → TC-4
- AC-6 → TC-5

## Results
All TCs PASS live. Live AC1 identity OK; AC2 dup-collapse correctly flagged; AC3 word-boundary regex behaves as documented; AC6 imports = `{collections, dataclasses, re}` only; dev 20/20; run_tests.py 52/52.
