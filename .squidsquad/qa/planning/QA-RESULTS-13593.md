# QA-RESULTS-13593

## Summary
VERIFIED — PASS. All 4 ACs confirmed via live, unmocked calls (own script, not the worker's fixture) — including proof the `cwd` mechanism genuinely redirects `gh` to a different repo, not just a plausible-looking no-op parameter.

## AC Walk

| AC | Result | Evidence |
|----|--------|----------|
| AC1 | PASS | Live `wizard._run(["gh","repo","view",...], cwd=".")` → this repo's real identity; `cwd=<empty temp dir>` → clean failure ("not a git repository"). Proves `cwd` genuinely changes resolution, not a silent no-op. |
| AC2 | PASS | Live `list_gh_labels(cwd=".")` → 50 real labels incl. `squidsquad`; `cwd=<no repo>` → empty set (graceful); `ensure_labels(dry_run=True, cwd=".")` → real existing-label count, zero side effects |
| AC3 | PASS | `cmd_ensure_labels` confirmed to call `ensure_labels(dry_run=dry)` with no `cwd` — defaults to `None`, ambient-CWD behavior unchanged |
| AC4 | PASS | Fallback-vs-fail-loudly reasoning holds: the graceful "no remote → directory name, empty repo" path is a genuinely distinct case from the original bug ("wrong remote, silently"). Scoping to `target_dir` means a missing remote now fails/falls back naturally instead of defaulting to whatever ambient repo happens to be there — the original bug class cannot recur under this design. |

## Additional checks
- Worker's own tests: `TestSetupYesGhScoping` 5/5 PASS.
- Combined-state static gate (branch auto-merged cleanly with #13592's concurrent wizard.py/test_wizard.py changes, 0 conflict markers): **5602/5602 PASS, 0 failures.**

## Zero-gap check
No gaps.

## Verdict
PASS → pending-ship.
