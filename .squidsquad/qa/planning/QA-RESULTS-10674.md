# QA-RESULTS-10674 — PRD-D / Story D3: Catalog gate at v2 compose time

**Verified**: 2026-06-02 08:40
**Branch**: `skill/d3-catalog-gate-10674` @ `40291e4d`
**PR**: #10747
**Verifier**: qa-lead
**Result**: **PASS**

## Scope Check

- `references/scripts/v2_catalog_gate.py` (+191 new) — `validate_v2_compose()` + `GateResult` / `GateIssue` dataclasses + `CatalogGateError` exception + `find_references()` regex helper
- `references/scripts/compose.py` (+25) — gate invocation in `deploy_alias_v2` AFTER `emit_v2_linked` and BEFORE the file write (preserves A2f atomic-write contract)
- `tests/test_v2_catalog_gate_d3.py` (+358 new) — 15 tests
- `tests/run_tests.py` (+1) — STATIC_TEST_MODULES registration
- `.squidsquad/skill/planning/ds-d3-review.md` (DS review log — NO_FINDINGS)

## Acceptance Criteria

| # | AC | Evidence | Status |
|---|---|---|---|
| 1 | v2 compose, when emitting `→ run sub-skill: <name>`, calls D1's parser to look up `<name>` → `source-path` | `validate_v2_compose` calls `catalog_parser.parse_catalog(catalog_path)` and looks up each extracted name. Wired into `deploy_alias_v2` at line 1670-1694. Lazy `import v2_catalog_gate as _v2_gate` inside the v2 branch keeps v1 deploy paths gate-cost-free. | PASS |
| 2 | Unresolved reference → abort with structured diagnostic naming role-class, slot, unresolved reference name | `kind="unresolved"` issue → multi-line report under `"Unresolved sub-skill references (no catalog row):"` header. `CatalogGateError.__init__` prepends `"catalog gate FAILED for alias '<alias>':"` so the alias context is in the abort message. Tests: `test_single_unresolved_aborts`, `test_multiple_unresolved_all_reported`. | PASS |
| 3 | Resolved reference where source-path file does NOT exist → abort with diagnostic | `kind="missing-file"` issue → separate report section `"Catalog row resolves but source file missing on disk:"` with `name -> path` per row. Tests: `test_resolved_but_file_missing_aborts`. | PASS |
| 4 | Multiple unresolved references → report ALL, not just first | Loop in `validate_v2_compose` accumulates issues; dedup via `seen_unresolved` + `seen_missing` sets so N references to same broken name produce ONE issue line. `test_multiple_unresolved_all_reported` + `test_duplicate_unresolved_reference_collapses_to_one_issue` + `test_clean_plus_unresolved_plus_missing_all_reported`. | PASS |
| 5 | v1 compose path untouched | `git diff` shows v1 compose code path unchanged — the new gate code is wired ONLY inside `deploy_alias_v2` (the v2 branch). `test_only_v2_dispatch_imports_gate` static-grep gate confirms compose.py imports `v2_catalog_gate` only inside `deploy_alias_v2`, not at module scope. §9a v1 byte-stability gate **5/5 green**. | PASS |
| 6a | Clean compose, all refs resolved → no abort | `test_all_refs_resolved_returns_clean` + `test_no_references_at_all_returns_clean` | PASS |
| 6b | Single unresolved → abort | `test_single_unresolved_aborts` | PASS |
| 6c | Multiple unresolved → all reported | `test_multiple_unresolved_all_reported` | PASS |
| 6d | Resolved but file-missing → abort | `test_resolved_but_file_missing_aborts` | PASS |

## Defense-in-Depth

- **`_REF_RE` regex** allows slash-bearing names (e.g. `roles/dm/events/pr-merge-wait`) per D1's catalog convention — `test_finds_slash_bearing_name` locks this in. Wouldn't be obvious from the AC list alone but is critical for the actual catalog content.
- **Issue dedup** — `seen_unresolved` and `seen_missing` sets ensure a name referenced N times produces ONE line in the abort report, not N. `test_duplicate_unresolved_reference_collapses_to_one_issue` pins this.
- **Mixed-issue report ordering is stable** — `format()` sorts unresolved and missing-file sections so reviewer diffs and test assertions are deterministic. `test_clean_plus_unresolved_plus_missing_all_reported` exercises the multi-kind ordering.
- **Atomic-write contract preserved** — gate runs BEFORE `output_path.parent.mkdir` and before any write, so a drift produces ZERO partial artifacts. Consistent with PRD-A A2f contract.
- **Catalog parse errors bubble through unchanged** — gate explicitly does not silently absorb upstream catalog defects (e.g. D1's known `#10687` duplicate); operators see the real cause. Per docstring: "A catalog parse error bubbles through unchanged — that is a D1/parser concern and not a D3 finding."

## DS Review

Skill ran DS review → **NO_FINDINGS**. Module is small (~190 LOC) and follows D4's structural shape closely (`Result` + `Issue` + `Error` + helper + scanner). Per `feedback_ds_review_per_change`, DS review was still required because D3 is on the v2 compose code path (mid-blast-radius); zero findings is the cleanest possible outcome.

## v1 Coexistence

§9a v1 byte-stability gate: **5/5 passed** on `40291e4d`. v1 compose code path is byte-identical pre/post-D3. Per AC5 + PRD: "v1 compose inlines bodies and has no `→ run sub-skill:` references in its output, so calling the gate on v1 output would always pass; we intentionally don't wire it there."

## Test Execution

`pytest tests/test_v2_catalog_gate_d3.py tests/test_v1_byte_stability_9a.py tests/test_d2_link_stage_references.py -q` on `40291e4d` → **37 passed** (15 D3 + 5 §9a + 17 D2 regression).

## Outcome

All 6 ACs covered + DS review clean + 5 defense-in-depth pinned behaviors (slash-bearing names, dedup, stable ordering, atomic-write preservation, parse-error pass-through). Clean integration into `deploy_alias_v2` at the right boundary. **Transitioning #10674: pending-test → pending-ship.**
