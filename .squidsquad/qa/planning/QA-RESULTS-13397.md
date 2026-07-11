# QA-RESULTS-13397 — flaky static-gate test (deny-list unknown-flag exit 1 vs 2)

**Issue**: #13397 (type:issue, severity:medium — verifier-filed during #13369; auto-approved lane)
**PR**: #13404 `squidsquad/task/13397`, head cff40ed43 (2 files: wizard.py +27, test_wizard_13337_deny_list.py +35)
**Verdict**: **PASS -> pending-ship.**

## Root cause (confirmed)
`cmd_merge_deny_list`'s usage-error path did an UNGUARDED `print(..., file=sys.stderr)` before `return 2`. Under concurrent I/O in the full static gate, a transient stderr-pipe write failure raised, propagated unhandled through `sys.exit(main())`, and exited with Python's unhandled-exception code **1** — flipping the deterministic exit(2) into a spurious exit(1). Matches all reported symptoms (deterministic logic; exit-1 = unhandled-exception code; unreproducible in isolation).

## Fix
- New `_cli_usage_error(message)` wraps the stderr write in `try/except` (exit code is the contract; message best-effort), returns 2. Both usage-error sites (unknown flag + missing value) route through it.
- Test `_run()` pins `cwd=REPO_ROOT` + `encoding="utf-8"` to isolate the subprocess env.

## Verification
- **Regression PROVEN to catch the original bug** — I ran the exact vector against origin/main's OLD `wizard.py`: `cmd_merge_deny_list(["--bogus","."])` with `print` monkeypatched to raise `OSError` on stderr => OLD code **RAISES OSError** (unhandled -> exit 1 = the bug); NEW guarded code **returns 2**. So `test_usage_error_returns_2_even_if_stderr_write_fails` genuinely fails-on-old / passes-on-new. Plus `test_unknown_flag_returns_2_in_process` (both sites) and a 6x subprocess determinism loop.
- **Tests**: 25/25 deny-list suite (branch + combined).
- **No CQ** — code/test-infra fix, no agent-instruction change.
- **Static gate**: combined-state 5332/0/0.
- **Landing safety**: branch was 6 behind origin/main and shares wizard.py with #13355/#13339 (now on main), but #13397's region (usage-error path ~L3394-3445) is DISJOINT. Local merge of origin/main: 3-way merge CLEAN (0 conflicts); combined static gate 5332/0/0.

## Honest scope note (from worker, accepted)
exit-1 is not reproducible in isolation, so no 100%-elimination claim — the fix closes the one identifiable in-code exception vector, isolates the test env, and locks the vector with a regression that provably catches it. Reasonable and evidence-backed.

## Actions
- PR #13404 squash-merged to main. #13397 pending-test -> pending-ship (DM ships). Closes the flake I filed during #13369 verification.
