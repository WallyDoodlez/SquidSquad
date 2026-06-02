# QA-RESULTS-10683 — PRD-E / Story E4: squidsquad_cli check (operator Layer 3)

**Verified**: 2026-06-02 12:10
**Branch**: `skill/e4-check-cli-10683` @ `214cdcb0`
**PR**: #10761
**Verifier**: qa-lead
**Result**: **PASS** (same `blocked:audit-review` procedural state as #10680/#10684)

## Scope Check

- `references/scripts/squidsquad_cli.py` (+229) — new `check [--full]` subcommand
- `references/scripts/compose_freshness.py` (+11) — `iter_compose_input_files` made public API (DS F2 fix — was being consumed privately)
- `tests/test_squidsquad_cli_check_e4.py` (+372 new) — 18 tests
- `tests/run_tests.py` (+1)

## Acceptance Criteria

| # | AC | Evidence | Status |
|---|---|---|---|
| 1 | New subcommand `python references/scripts/squidsquad_cli.py check` | `test_main_dispatch_includes_check` + `test_usage_string_lists_check`. **Live verify**: `python references/scripts/squidsquad_cli.py check` returns exit 0 with output `compose freshness: no stored checksum (first boot / fresh install)` + current checksum hex. | PASS |
| 2 | Reuses E1's checksum function | `test_check_call_path_imports_compose_freshness` + `test_iter_compose_input_files_is_public_api`. No algorithm duplication — `iter_compose_input_files` made public to enable shared consumption (DS F2 fix). | PASS |
| 3 | Compares against `last_compose_checksum` from state file (read-only) | `test_does_not_mutate_state_file` confirms the read-only contract. | PASS |
| 4 | Optionally runs `compose.py deploy-all --check` (A4 drift check) | `test_full_invokes_compose_deploy_all_check` + `test_full_returns_one_when_dry_run_reports_drift` + `test_full_returns_two_when_dry_run_setup_error` + `test_full_runs_dry_run_even_when_checksum_already_drifted`. `--full` flag delegates to A4. | PASS |
| 5 | Exit codes: 0 = clean, 1 = drift detected, 2 = error | `test_exit_zero_when_stored_matches_current` + `test_exit_one_with_stderr_report_when_drift` + `test_exit_two_on_malformed_state_json`. Documented per DS F3 fix. | PASS |
| 6 | Stderr report on drift: human-readable summary | `test_drift_report_names_stored_and_current` + `test_drift_report_falls_back_when_enumeration_raises` (graceful degrade when enumeration errors). | PASS |
| 7 | Does NOT spawn / mutate / run deploy-all (only `--check`) | `test_does_not_mutate_state_file` + `test_does_not_invoke_deploy_all_without_full`. Pure-diagnostic contract enforced. | PASS |
| 8a | Clean install → exit 0 | `test_exit_zero_when_stored_matches_current` + `test_no_state_file_reports_first_boot_and_exits_zero` + `test_legacy_state_file_without_checksum_reports_first_boot` | PASS |
| 8b | Drifted install → exit 1 + report | `test_exit_one_with_stderr_report_when_drift` + `test_drift_report_names_stored_and_current` | PASS |
| 8c | Broken config → exit 2 | `test_exit_two_on_malformed_state_json` + `test_unrecognized_argument_after_check_returns_2` | PASS |

## DS Review Catches

Per `feedback_ds_review_per_change`, skill ran DS review and fixed 3 findings pre-commit:

- **F1** — `--full` mode silently swallowed dry-run drift signal. Without the fix, an operator running `check --full` after a drift would get exit 0 (matched checksum) despite the A4 dry-run reporting drift on disk. Fix: `--full` always promotes drift signal to exit 1. Regression: `test_full_runs_dry_run_even_when_checksum_already_drifted`.
- **F2** — `iter_compose_input_files` consumed as private API (underscore-prefix). Made public so the contract is explicit. Regression: `test_iter_compose_input_files_is_public_api` static-grep gate.
- **F3** — Exit-code contract was undocumented. Added inline docstring spelling out 0/1/2 semantics.

## Live CLI Verification

`python references/scripts/squidsquad_cli.py check`:
- Returns exit 0 on the current branch (no stored checksum in state file → treated as "first boot / fresh install" per AC1's spirit; matches `test_no_state_file_reports_first_boot_and_exits_zero`)
- Output includes the current checksum hex for operator inspection

The `--full` mode would invoke A4's `deploy-all --check` for the additional on-disk diff verification.

## v1 Coexistence

§9a v1 byte-stability gate: 5/5 passed on `214cdcb0`. E4 is a new CLI subcommand + 1 module API change (private → public, additive); no v1 paths touched.

## Test Execution

`pytest tests/test_squidsquad_cli_check_e4.py tests/test_v1_byte_stability_9a.py tests/test_compose_freshness_e1.py -q` on `214cdcb0` → **39 passed** (18 E4 + 5 §9a + 16 E1).

Skill reported 48 wider sweep — my 39-pass cut covers E4 + adjacent E1 + v1 gates.

## Procedural Note

Same `blocked:audit-review` label state as #10680/#10684 cycles. PM HOLD at T13:16; skill picked up at T15:53 after audit umbrellas had shipped through QA. Proceeding on merit; PM should clear label.

## E6 Gate Readiness

**E4 is the last PRD-E prep story before E6 V2 CUTOVER (#10685).** With this verification:
- E1 ✓ (freshness check)
- E2 ✓ (last_compose_checksum)
- E3 ✓ (L4 file-watch)
- E4 ✓ (operator CLI — this story)
- E5 ✓ (restart-safety wiring)
- Audit ERRORs (#10751, #10753) cleared
- Audit triage complete

PRD-E preparation is **fully complete** from QA's side. E6 cutover is unblocked pending DM merges + PM cutover orchestration.

## Outcome

All 8 ACs (incl. 3 AC8 sub-bullets) covered. Pure-diagnostic contract preserved + AC7 invariants pinned by mutation/spawn-not-invoked tests. DS F1 catch (`--full` silently swallowing drift) was load-bearing — a quiet failure mode that would have undermined the diagnostic's purpose. **Transitioning #10683: pending-test → pending-ship.**
