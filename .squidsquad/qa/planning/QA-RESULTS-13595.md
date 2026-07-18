# QA-RESULTS-13595

## Summary
VERIFIED — PASS. All 5 self-derived ACs confirmed, including a live re-run of the exact original repro (from #12527's verification) that first surfaced this bug — the deprecation warning that revealed the leak no longer fires, and stderr is fully clean.

## AC Walk

| AC | Result | Evidence |
|----|--------|----------|
| AC1 | PASS | `config.config_path_override` (contextvar-backed context manager) redirects `_read_config()`/`get_field()` reads to a target's own config.md for the duration of a compose call |
| AC2 | PASS | Wired into both `deploy_alias_v2` and `deploy_role_v2` |
| AC3 | PASS | Single funnel point (`_read_config()`) covers all 9 previously-identified placeholder call sites — no per-field special-casing needed |
| AC4 | PASS | Own live re-run of the ORIGINAL repro (own script, not worker's fixture): the "Dev Agents:" warning that first revealed this bug is now GONE, stderr fully empty — diagnostic that the read source genuinely changed. Worker's own divergent-value tests (installing-clone marker absent, target's own value present) independently re-run and PASS in both compose entry points. |
| AC5 | PASS | `test_config_get_field_unaffected_outside_override` PASS + code-read: `target_root` defaults to `REPO_ROOT` for self-hosted calls, making the override path byte-identical to the default `CONFIG_PATH` — zero behavior change for normal operation |

## Additional checks
- `tests/test_13595_config_target_root_leak.py`: 3/3 PASS.
- `tests/test_compose*.py tests/test_config*.py`: 556/557 PASS — the 1 "failure" (`test_10360_cleanup_markers_preserved`) is the pre-existing, static-gate-excluded known-failure blocked on open #10360, unrelated to this diff.
- Side-fix verified: the stderr "ERROR: Field not found" noise on sparse fresh-scaffold configs is now silenced (confirmed empty stderr in my own live re-run) — matches `_read_config_value`'s own long-standing graceful-fallback contract (the exception was already caught; only the print was noise).
- Combined-state static gate: **5580/5580 PASS, 0 failures.**

## Zero-gap check
No gaps. This closes the loop on my own filed finding from #12527's verification.

## Verdict
PASS → pending-ship.
