After thorough analysis of the changed files, I find the code correctly implements the acceptance criteria:

- **`_result_cell` function** (lines 68-85): Correctly bounds result extraction to the Result cell using two `find("|", ...)` calls. The first offset (`match_end`) correctly skips the TC description cell; the second offset (`cell_start + 1`) enters the Result cell. Both 2-column terminated rows (`| TC-1 | PASS |`) and unterminated rows (`| TC-1 | PASS`) are handled correctly. When `cell_start == -1` (no closing pipe), returns `""` → `UNKNOWN`. ✓

- **`parse_tc_results` integration** (lines 123-127): Only table rows use `_result_cell`; heading rows retain the existing `i+1` skip logic. No regression to #2469 (heading titles with invalid words), #13944 (merged-cell `| TC1 -- desc |` and bold-bullet `- **TC1 ...**`), or #13737 (file discovery conventions). ✓

- **Test honesty**: All new tests in `TestResultCellOnly13990` exercise the exact scenarios claimed — evidence-column invalid words ignored, result-cell invalid words blocked, empty result cell → UNKNOWN, qualifier prose in result cell parsed. ✓

- **Edge cases**: Malformed rows without pipes, empty result cells, TC descriptions containing invalid vocabulary, and unterminated 2-column rows are all exercised by tests and behave correctly. ✓

No off-by-one errors, no regressions, no false test coverage.

NO_FINDINGS