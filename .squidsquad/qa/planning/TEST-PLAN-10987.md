# TEST-PLAN-10987 — L4 parser rejects H3 sub-headings inside ## Soul / ## Identity prose slots

**Source**: GitHub issue #10987 (skill-lead post-#10981 finding) and skill-lead's two-commit fix on `skill/e6-v2-cutover-10685` (`a11f9262` initial fix, `876db8d9` DS-review follow-up).

## ACs (derived)

- **AC-1**: L4 parser accepts non-op-like `### <prose>` H3 headings inside any of the six slots, treating them as content. Behavior is uniform across slots (not slot-gated).
- **AC-2**: Op-like H3 headings (matching `_OP_LIKE_RE` — `append|replace|insert-before|insert-after`) still parse strictly via the existing `_OP_RE`. Malformed op forms still raise `L4ParseError("malformed H3 op …")`.
- **AC-3**: At every `## <Slot>` boundary, an implicit `append` op opens. Empty-body suppression prevents no-op implicits from manifesting. (DS Finding 4 — pre-fix the lazy-open for instructions silently dropped prose between `## Instructions` and the first H3.)
- **AC-4**: Explicit op followed by prose H3 commits the explicit op first, then opens a fresh implicit append. (DS Finding 3 — pre-fix, prose was silently absorbed into the prior explicit op.)
- **AC-5**: `link_stage_validator.R4` exempts implicit appends from the `→ run sub-skill:` reference requirement; explicit author appends without ref still raise. (DS Finding 1 — without this, dm/verifier/worker would parse cleanly but abort at R4.)
- **AC-6**: All four live `.squidsquad/project/{pm,dm,verifier,worker}.md` files parse end-to-end.
- **AC-7**: Regression tests in `tests/test_l4_parser_10987_prose_h3.py` (28 collected) cover all the above plus the live-file integration sanity checks.
- **AC-8**: Existing test `test_l4_parser.py::test_malformed_h3_rejected` updated: 3 obsolete prose-rejection cases removed; replaced with `test_non_op_like_h3_treated_as_prose` parametrized over 4 prose patterns.
- **AC-9**: No regression in broader L4 + compose + link-stage-validator + compose-10981 suites.

Out of scope (skill-lead's explicit carve-outs):
- pm.md still failing R4 due to bold-heading explicit `### append` with no `→ run sub-skill:` ref — pre-existing content issue independent of #10987; to be filed separately to PM since pm.md is PM's L4 content.
- DS Findings 2 + 5 (op-keyword punctuation typos, `current_op` reset semantics) dismissed as spurious by skill-lead, justified inline in cycle comment.

## Test Cases

### TC-1 (covers AC-1, AC-2): non-op-like H3 = prose; op-like-malformed still raises
- **Verification command**: `python -m pytest tests/test_l4_parser.py::test_non_op_like_h3_treated_as_prose tests/test_l4_parser.py::test_malformed_h3_rejected -v`
- **Expected**: all parametrized cases pass — 4 prose patterns recognized as content, 2 op-like-malformed cases raise.

### TC-2 (covers AC-3, AC-4, AC-5): implicit-append semantics + R4 exemption
- **Verification command**: `python -m pytest tests/test_l4_parser_10987_prose_h3.py::TestImplicitAppendExemptFromR4Validation tests/test_l4_parser_10987_prose_h3.py::TestNonOpH3UnderNonInstructionsSlot tests/test_l4_parser_10987_prose_h3.py::TestNonOpH3UnderInstructionsSlot -v`
- **Expected**: implicit-vs-explicit `_implicit` flag set correctly; R4 exempts implicit appends but still rejects explicit-without-ref; prose H3s flow into appropriate slot bodies; mixed prose+explicit captured as separate ops.

### TC-3 (covers AC-6): live `.squidsquad/project/<role>.md` files parse
- **Verification command**: `python -m pytest tests/test_l4_parser_10987_prose_h3.py::TestLiveProductionL4Files -v`
- **Expected**: pm/dm/verifier/worker live L4 files all parse without raising.

### TC-4 (covers AC-6 — direct empirical): parse each live L4 file from a fresh interpreter
- **Verification command**: `python -c "import sys; sys.path.insert(0, 'references/scripts'); from l4_parser import parse_l4_file; [print(role, len(parse_l4_file(f'.squidsquad/project/{role}.md').slots), 'slots') for role in ['pm', 'dm', 'verifier', 'worker']]"`
- **Expected**: zero `L4ParseError`; each role parses to a non-empty `L4Document` with the expected slots.

### TC-5 (covers AC-7): 28 regression tests in the new file
- **Verification command**: `python -m pytest tests/test_l4_parser_10987_prose_h3.py -v`
- **Expected**: 28 collected, 28 PASS.

### TC-6 (covers AC-8): obsolete `test_malformed_h3_rejected` cases removed
- **Verification command**: `grep -A6 "def test_malformed_h3_rejected" tests/test_l4_parser.py | head -12`
- **Expected**: parametrize list contains only the 2 truly-malformed cases (`### insert-before` no-target, `### replace step:cycle/foo extra` trailing-garbage). The 3 prose cases (`### Boot & Queue`, `### appendix`, `### insert-around step:cycle/foo`) are NO LONGER asserted as raises — they live in `test_non_op_like_h3_treated_as_prose` instead.

### TC-7 (covers AC-9): no regression in broader suites
- **Verification command**: `python -m pytest tests/test_l4_parser.py tests/test_l4_parser_10987_prose_h3.py tests/test_l4_removal_c9.py tests/test_link_stage_validator.py tests/test_compose.py tests/test_compose_10981_deploy_alias_v2_token_leaks.py`
- **Expected**: 0 failures; 200+ pass. (Acceptable failures: the same pre-existing-on-cutover failures noted in QA-RESULTS-10981 — `test_manifest.py::test_include_targets_exist`, `test_no_orphan_sub_skills`, 4 errors in `test_event_mode_fragments` — would appear if those files were included; they are not in this verification command's scope.)

## Coverage matrix

- AC-1 → TC-1
- AC-2 → TC-1
- AC-3 → TC-2
- AC-4 → TC-2
- AC-5 → TC-2
- AC-6 → TC-3, TC-4
- AC-7 → TC-5
- AC-8 → TC-6
- AC-9 → TC-7

## Comprehension Questions

Skipped — this is a pure-Python parser fix. The behavior change (non-op-like H3 = prose) is structural, not semantic to any LLM-consumed instruction file. No CLAUDE.md content is altered by this fix; only the compose-time parsing of upstream L4 source.
