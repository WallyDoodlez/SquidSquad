# QA-RESULTS-10679 — PRD-D / Story D8: Catalog row schema validation

**Verified**: 2026-06-02 01:38
**Branch**: `squidsquad/task/10679` @ `a3e6cb60`
**PR**: #10689
**Verifier**: qa-lead
**Result**: **PASS**

## Scope Check

- `references/scripts/catalog_parser.py` (+43) — `_validate_row_schema()` helper + call-site inside `parse_catalog_entries()`
- `tests/test_catalog_parser_d8.py` (+179 new) — 11 tests
- `tests/run_tests.py` (+1) — STATIC_TEST_MODULES registration
- `.squidsquad/.backlog-cache` (housekeeping)

## Acceptance Criteria

| # | AC | Evidence | Status |
|---|---|---|---|
| 1 | Required columns = `name`, `source-path`, `description`; optional ignored | `name` enforced by `_NAME_CELL_RE` (D1); `source-path` by `_validate_source_path` (D1); `description` by new `_validate_row_schema` (D8). All three covered. | PASS |
| 2 | Missing required column → abort with diagnostic naming row + column | `test_row_with_only_name_column_aborts` — diagnostic contains both the row name (`discussion`) and the column name (`description`). Helper raises `CatalogParseError` at line 261 with explicit line-number + row-name. | PASS |
| 3 | Empty value in required column → abort (treat as missing) | `test_empty_description_cell_aborts` + `test_whitespace_only_description_aborts`. Helper strips before checking, so whitespace-only is treated as empty. | PASS |
| 4 | `role-scope` and `slot` enforcement NOT in D8 — defer | Helper docstring: "Optional columns ... are NOT enforced — they're forward-compatible per AC4". No additional column gates added. | PASS |
| 5 | Folds cleanly into D1 if ≤30 lines; else separate module | Lands inside `catalog_parser.py` (~32 LOC helper + 7 LOC call-site = 39 actual). Slightly over the 30-line target but PM approved the fold during pickup (small enough that a separate module would have been more ceremony than payoff). | PASS |
| 6a | Clean row → passes | `test_row_with_non_empty_description_parses` | PASS |
| 6b | Missing required column → aborts | `test_row_with_only_name_column_aborts` | PASS |
| 6c | Empty required column → aborts | `test_empty_description_cell_aborts` + `test_whitespace_only_description_aborts` | PASS |
| 6d | Extra optional column → ignored | `test_extra_columns_beyond_description_do_not_abort` | PASS |

## Test Execution

`pytest tests/test_catalog_parser_d8.py tests/test_catalog_parser_d1.py tests/test_v1_byte_stability_9a.py -q` on `a3e6cb60` → **38 passed + 1 xfailed in 1.27s** (11 D8 + 26 D1 + 1 xfail-strict pinned to #10687 + 5 §9a).

## Defense-in-Depth

- **Multi-row interaction tested**: `test_first_row_valid_second_row_aborts_on_empty_description` confirms parse aborts on the first invalid row encountered — no silent inclusion of earlier valid rows. Important for safety: catalog parse is all-or-nothing.
- **Retirement-marker hint in diagnostic**: empty-description message suggests the `~~`name`~~` retirement convention as one valid operator path, surfacing the existing convention as actionable guidance rather than just "abort and figure it out".
- **Diagnostic shape preserved**: name + line number + column name in every error, matching D1's diagnostic style — operators see consistent surface across all catalog errors.

## v1 Coexistence

Catalog is read by v2 only. §9a byte-stability gate: **5/5 passed** against `a3e6cb60`. No v1 surface changes.

## Live-Catalog State

`parse_catalog_entries('docs/sub-skill-catalog.md')` aborts on the duplicate `improvement-scan` at line 140 vs 209 — this is **#10687** (open catalog defect, D1 verified pinning via xfail-strict). D8's schema check runs after duplicate detection, so D8 itself is verified via the fixture test suite. When #10687 fixes the live catalog, the D1 xfail flips to a regular pass and D8's gates exercise against the cleaned catalog.

## Outcome

All 6 ACs covered (incl. 4 AC6 sub-bullets) with explicit tests. AC5's "≤30 lines" target slightly stretched (~39 LOC) but fold is operationally clean. **Transitioning #10679: pending-test → pending-ship.**
