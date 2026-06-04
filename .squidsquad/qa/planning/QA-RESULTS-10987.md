# QA-RESULTS-10987

**Run**: 2026-06-03 22:17 (qa cycle 640)
**Branch**: `skill/e6-v2-cutover-10685` (commits `a11f9262` + `876db8d9`)
**PR**: none (will fold into E6 squash #10685)
**Verdict**: **PASS** — all 9 ACs satisfied; routing `pending-test → pending-ship`.

## AC walk

| AC | Statement | TC | Result |
|----|-----------|----|--------|
| 1 | Non-op-like `### <prose>` H3 = content, uniform across slots. | TC-1 | PASS — `test_non_op_like_h3_treated_as_prose` PASSES for all 4 prose patterns (`### Boot & Queue`, `### insert-around step:cycle/foo`, `### appendix`, `### Zero-gap gate`). Test asserts the heading line lands in `op.body_text`. |
| 2 | Op-like H3 still strictly parsed; malformed still raises. | TC-1 | PASS — `test_malformed_h3_rejected` still raises `L4ParseError("malformed H3 op …")` for `### insert-before` (no target) and `### replace step:cycle/foo extra` (trailing garbage). |
| 3 | Implicit `append` opens at every `## <Slot>` boundary; empty bodies suppressed. | TC-2 | PASS — `TestImplicitAppendExemptFromR4Validation::test_implicit_append_op_is_marked_implicit` PASS; `TestNonOpH3UnderNonInstructionsSlot` cases (3) cover prose, multi-subheading, empty-slot suppression. |
| 4 | Explicit op followed by prose H3 → commit explicit first, open fresh implicit append. | TC-2 | PASS — `TestNonOpH3UnderInstructionsSlot::test_mixed_prose_and_explicit_captured_as_separate_ops` covers this. |
| 5 | R4 in `link_stage_validator` exempts implicit appends; explicit-without-ref still raises. | TC-2 | PASS — `TestImplicitAppendExemptFromR4Validation` 4 tests cover both branches. |
| 6 | All 4 live `.squidsquad/project/<role>.md` files parse. | TC-3, TC-4 | PASS — `TestLiveProductionL4Files::test_live_l4_file_parses[pm/dm/verifier/worker]` all PASS; direct interpreter check confirms `parse_l4_file` succeeds for all 4 with slots `['identity', 'instructions', 'project-context', 'soul']`. |
| 7 | 28 regression tests in `tests/test_l4_parser_10987_prose_h3.py`. | TC-5 | PASS — 28 collected, 28 PASS. (Skill-lead's "22 + 4" math reflects parametrization in two ways; final collected count is 28 — close enough to claim.) |
| 8 | Obsolete cases removed from `test_malformed_h3_rejected`; replaced with `test_non_op_like_h3_treated_as_prose`. | TC-6 | PASS — `test_l4_parser.py:155-156` parametrize list contains only the 2 truly-malformed cases; the 3 prose cases were lifted into the new prose test at L166-189. |
| 9 | No regression in broader L4 + compose + link-stage-validator + compose-10981 suites. | TC-7 | PASS — combined suite 209 passed in 0.96s, 0 failures. |

## Test runs

### TC-1 + TC-2 + TC-3 + TC-5 — new + updated L4 parser suite

```
$ python -m pytest tests/test_l4_parser_10987_prose_h3.py tests/test_l4_parser.py -v
…
63 passed in 0.25s
```

28 new (`test_l4_parser_10987_prose_h3.py`) + 35 existing (`test_l4_parser.py`, post-update) all pass.

### TC-4 — direct live-file parse from a fresh interpreter

```
$ python -c "from l4_parser import parse_l4_file; …"
pm: PARSE OK, slots: ['identity', 'instructions', 'project-context', 'soul']
dm: PARSE OK, slots: ['identity', 'instructions', 'project-context', 'soul']
verifier: PARSE OK, slots: ['identity', 'instructions', 'project-context', 'soul']
worker: PARSE OK, slots: ['identity', 'instructions', 'project-context', 'soul']
```

This is the direct empirical analogue of the original issue's reproduction command. Pre-fix: `L4ParseError: .squidsquad/project/dm.md:9: malformed H3 op heading '### User-first documentation framing'`. Post-fix: PARSE OK for all 4 roles. Definitive resolution of the symptom.

### TC-7 — broader suite regression

```
$ python -m pytest tests/test_l4_parser.py tests/test_l4_parser_10987_prose_h3.py tests/test_l4_removal_c9.py tests/test_link_stage_validator.py tests/test_compose.py tests/test_compose_10981_deploy_alias_v2_token_leaks.py
209 passed in 0.96s
```

Zero regressions in the affected surface (L4 parser + link-stage validator + compose + #10981's earlier fix).

### Test quality inspection

`test_non_op_like_h3_treated_as_prose` (test_l4_parser.py:175): asserts `op.op_type == "append"`, `op.target_step_id is None`, and that both the heading line and the following prose appear in `op.body_text`. Not vacuous — captures the exact regression class.

`TestImplicitAppendExemptFromR4Validation` (test_l4_parser_10987_prose_h3.py:226): tests both branches — `_implicit=True` exempts R4, but explicit-without-ref still raises. Closes the DS Finding 1 loop fully.

`TestLiveProductionL4Files` (test_l4_parser_10987_prose_h3.py): runs against the actual on-disk `.squidsquad/project/<role>.md`. Captures the end-to-end empirical for every future test run, replacing skill-lead's ad-hoc fix-time verification with a deterministic CI signal.

## Decision

All 9 ACs satisfied with zero gaps. Direct empirical evidence (TC-4) confirms the original symptom no longer reproduces against the live tree for any of the 4 production L4 files. DS code-review findings 1, 3, 4, 6 are all addressed in `876db8d9` with targeted tests (`TestImplicitAppendExemptFromR4Validation`); findings 2 and 5 were dismissed with justification.

Transitioning #10987 `pending-test → pending-ship`. The fix commits (`a11f9262`, `876db8d9`) sit on `skill/e6-v2-cutover-10685` and will fold into the E6 squash (#10685) alongside #10981. PM's Phase 8 readiness gate now has two of its pre-squash blockers resolved.

The pm.md R4 explicit-append-without-ref issue noted by skill-lead is correctly carved out as a pre-existing content concern owned by PM — separate filing in PM's lane.
