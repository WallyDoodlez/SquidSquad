# QA-RESULTS-10654 — PRD-C / Story C5: Compose dry-run gate (Gate 3)

**Verified**: 2026-06-01 17:08
**Branch**: `squidsquad/task/10654` @ `7fd29432`
**PR**: #10664
**Verifier**: qa-lead
**Result**: **PASS**

## Scope Check

- `references/scripts/l4_compose_dryrun.py` (+197 new module) — `dryrun_l4()`, `DryrunResult`, `DryrunFailure`, `format_failure_for_human()`
- `references/sub-skills/common/l4-curation.md` (+5) — Gate 3 prose
- `tests/test_l4_compose_dryrun_c5.py` (+279) — 16 tests
- `tests/run_tests.py` (+1)

## Acceptance Criteria

| # | AC | Evidence | Status |
|---|---|---|---|
| 1 | Writes staged L4 to temp + invokes A4.5 per alias | `test_clean_l4_writes_staged_content_to_tempfile_under_repo_root` + `test_clean_l4_runs_check_for_every_alias_of_role_class`. Uses A4.5's `compose.check_alias_staged_l4` in-process (not subprocess) for determinism. | PASS |
| 2 | Non-zero exit: capture stderr, surface "Dry-run failed: <reason>", abort, re-prompt | `test_format_failure_for_human_single_alias_matches_ac2_phrasing` confirms exact phrasing match. Parametrized validation failure tests cover R1/R5/R6 paths. | PASS |
| 3 | Exit 0 for all aliases → proceed | `test_clean_l4_returns_passed_true` | PASS |
| 4 | `--staged-l4` doesn't replace on-disk; cross-alias validation | On-disk L4 NOT replaced per design (writes to `.squidsquad/tmp/l4-dryrun/`). Per-alias dispatch built in via `test_clean_l4_runs_check_for_every_alias_of_role_class`. Cross-alias test: `test_one_alias_fails_another_passes_returns_failed`. | PASS |
| 5a | Clean pass → proceed | `test_clean_l4_returns_passed_true` | PASS |
| 5b | Orphan step-ID target → abort | Parametrized: `[R5-L4 op references non-existent step-id `ghost`]` | PASS |
| 5c | Per-slot constraint violation → abort | Parametrized: `[R1-L4 file contains `## Vault` H2]` | PASS |
| 5d | Malformed H3 op → abort | Parametrized: `[R6-whole-slot replace mixed with other ops]` | PASS |
| 5e | One alias passes, another fails → abort | `test_one_alias_fails_another_passes_returns_failed` | PASS |

## Defense-in-Depth

- **REPO_ROOT-sandboxed tempdir** (`.squidsquad/tmp/l4-dryrun/`) — the lesson from #10444 is generalized; source comment notes "keeping tempfiles under REPO_ROOT prevents the [sandbox bypass]". Pattern now applied across Gate 1 (#10652) + Gate 3 here.
- **Never raises**: `dryrun_l4` always returns a `DryrunResult` (passed bool + failures list). Callers don't need to catch — they branch on `passed`. Combined with the Gate 1 typed-exception model, the safety pipeline has consistent error-handling discipline.
- Rule classification on `DryrunFailure`: R1-R7 (real rule), `<setup>` (config-time), `<other>` (unexpected). Lets the human-facing surface phrase failures intelligibly.
- `test_role_class_with_no_aliases_returns_setup_failure` — defensive path for misconfigured role-class.
- `test_format_failure_for_human_passed_returns_empty_string` — no spurious output on success.
- `test_format_failure_for_human_multi_alias_enumerates_each` — multi-alias failure surfacing is structured.
- `test_dryrun_result_default_failures_is_independent_list` + `test_dryrun_failure_has_all_three_fields` — dataclass hygiene.

## Test Execution

`pytest tests/test_l4_compose_dryrun_c5.py -q` on `7fd29432` → **16 passed in 0.09s**.

## Outcome

All 5 ACs (incl. 5 sub-bullets) covered + defense-in-depth (REPO_ROOT lesson now generalized across Gates, never-raises contract, rule classification, no-aliases safety). The 3-gate safety model (audit → mini-CQ → dry-run) is now complete with C3+C4+C5. **Transitioning #10654: pending-test → pending-ship.**
