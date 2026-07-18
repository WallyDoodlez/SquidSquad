# QA-RESULTS-13592 (re-verification pass 2)

## Summary
VERIFIED — PASS. AC2's gap is fully resolved with a well-reasoned fix (skip stack inference when `target_dir` already has an installed squad, rather than trying to distinguish "product dependency" from "incidental tooling dependency" from scan output alone). AC1/AC3 already confirmed PASS in pass 1, unaffected.

## What changed since pass 1
`generate_default_spec` gained an optional `target_dir` parameter; when `target_dir/.squidsquad/config.md` already exists, stack inference is skipped outright regardless of scan signal. Both real call sites (`cmd_generate_defaults`, `cmd_setup_yes`) now thread `target_dir=target_path` through. New test class `TestGenerateDefaultSpecAlreadyInstalled` (4 cases), including the exact regression test I requested: a REAL `repo_scan(str(REPO_ROOT))` against this repo, asserting `fastapi` is still detected (so the test fails loudly if the repro assumption ever goes stale) and the worker stays `skill`.

## Verification this pass
- **Decisive re-check (own script, not the worker's fixture)**: re-ran `repo_scan(".")` against this actual repo (confirmed `fastapi` still detected, repro assumption not stale), called `generate_default_spec(scan_data, repo_info, target_dir=".")` — worker correctly stays `skill`. Negative control (no `target_dir`) still infers `worker` as designed — confirms the skip is correctly gated on the already-installed check, not a blanket regression of AC1.
- Worker's own tests: 17/17 PASS (13 from pass 1 + 4 new `AlreadyInstalled` cases, including the live-repo-scan regression).
- Combined-state static gate: **5597/5597 PASS, 0 failures.**

## Zero-gap check
No gaps. All ACs now independently confirmed via live evidence.

## Verdict
PASS → pending-ship.
