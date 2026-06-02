# QA-RESULTS-10752 — PRD-B audit umbrella close (W1 + W4 residual)

**Verified**: 2026-06-02 14:10
**Branch**: `skill/issue-10752-prd-b-audit-close` @ `2e93db5d`
**PR**: #10765
**Verifier**: qa-lead
**Result**: **PASS** (closes the audit umbrella; 5 of 7 findings auto-resolved by B9)

## Scope Recap

PRD-B audit verdict was FAIL (3 ERRORS + 4 WARNINGS) — assemble pipeline was dead code with zero callers. PM filed B9 (#10763) as the missing wiring story. After B9 shipped in cycle 574, the audit findings split:

- **Auto-resolved by B9** (5 of 7): ERROR 1 (wire compose → atomic_emit), ERROR 2 (v1 path overwrite), ERROR 3 (model + temperature lock), W2 (cache adapter), W3 (filename_suffix parameterization)
- **Standalone residual** (this PR): W1 (verify_preservation incomplete) + W4 (LLM context string omits dimensions)

## Findings Resolution

| # | Finding | Disposition | Evidence |
|---|---|---|---|
| ERROR 1 | Assemble pipeline never wired | AUTO-RESOLVED by B9 | `deploy_alias_v2` now calls `assemble_and_emit` (verified cycle 574 #10763) |
| ERROR 2 | atomic_emit writes v1 paths | AUTO-RESOLVED by B9 | `filename_suffix` defaults `.v2.md`; AC2 `test_v1_canonical_paths_not_written` |
| ERROR 3 | No model + temperature lock | AUTO-RESOLVED by B9 | `get_model_for_task('assemble')` returns 'sonnet'; AC6 temperature ≤ 0.3 in adapter |
| W1 | verify_preservation missing fenced-block content + file paths | **FIXED IN THIS PR** | `verify_fenced_block_content` + `verify_file_paths` added to `assemble_verifier.py` (+109 LOC). 14 new tests covering identity / swap / drop / add / no-blocks / dropped-path / substituted-path / bare-filename-no-false-positive / multiset. |
| W2 | B6 cache shape mismatch | AUTO-RESOLVED by B9 | `assemble_adapter.py` bridges (verified cycle 574 #10763) |
| W3 | _atomic_write_triple hardcoded filenames | AUTO-RESOLVED by B9 | `filename_suffix` parameter on `_atomic_write_triple` (verified cycle 574 #10763) |
| W4 | LLM context string omits preservation directives | **FIXED IN THIS PR** | `assemble_pass.py` context now names all FOUR dimensions: "(a) every `→ run sub-skill: <name>` reference verbatim, (b) every `step:cycle/<id>` reference verbatim, (c) every fenced code block (the lang tag AND the body content) verbatim, and (d) every file path token verbatim". `test_context_mentions_all_four_dimensions` static-grep gate locks this in. |

## W1 Implementation Detail

`verify_preservation` now returns a `PreservationResult` with 8 diff fields covering all 4 dimensions:
- Sub-skill refs (pre-existing)
- Step IDs (pre-existing)
- Fenced block parity by count (pre-existing, ±10% tolerance)
- **Fenced block content** verbatim (new — multiset equality of `(lang_tag, body)` tuples)
- **File paths** (new — regex extraction + multiset equality, with bare-filename false-positive guard)

`test_preservation_result_carries_all_eight_diff_fields` pins the dataclass shape. `test_ok_when_all_four_dimensions_intact` / `test_dropped_fenced_block_flips_ok` / `test_dropped_file_path_flips_ok` cover the OK-flip semantics for the new dimensions.

## W4 Implementation Detail

Inline source comment explicitly notes the SC3 + #10752 W4 reasoning: "Pre-fix the context only mentioned sub-skill + step-ID, so the LLM might rewrite fenced bodies or strip file paths and only be caught at verification time — that path either retries the LLM (cache-corruption fallback) or aborts (fresh-run PreservationFail). Including the full guarantee set upfront is cheaper than the abort cycle."

`test_context_mentions_all_four_dimensions` does a static-grep assertion on the actual context string emitted by `assemble_slot` — guards against future refactors that drop a dimension.

## v1 Coexistence

§9a v1 byte-stability gate: 5/5 passed on `2e93db5d`. Pure additive verifier extensions + LLM context wording change. No compose path or output behavior change.

## Test Execution

`pytest tests/test_assemble_verifier.py tests/test_v1_byte_stability_9a.py tests/test_assemble_wired_b9.py -q` on `2e93db5d` → **71 passed**.

Skill reported "145 wider sweep, no regressions". My 71-pass cut covers verifier + B9 + §9a.

## E6 Cutover Readiness

With #10752 closed:
- PRD-A audit (#10751) — shipped ✓
- PRD-C audit (#10753) — shipped ✓
- PRD-B audit (#10752) — **shipped via this PR** ✓
- PRD-B B9 wire (#10763) — shipped ✓
- PRD-E prep (E1+E2+E3+E4+E5) — all shipped ✓

**E6 V2 CUTOVER (#10685) is fully unblocked** from the QA verification side. PM's `blocked:pm-coordination` + `role:skill` hold can be lifted whenever cutover is ready.

## Outcome

W1 + W4 residual properly addressed with substantial test coverage (16 new tests). B9 cleanly auto-resolved 5 of 7 findings as PM predicted. Strategic outcome: the audit umbrella that started as 3 ERRORS + 4 WARNINGS and required 5 PM escalations is now fully closed without compromising scope discipline. **Transitioning #10752: pending-test → pending-ship. PRD-B audit cycle complete.**
