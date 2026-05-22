# QA Results — #9905 (Windows tasklist 26s wedge — harness inoperative)

**Verifier**: qa-lead
**Timestamp**: 2026-05-22 09:31 cycle 727
**Fix commit**: e7a47737 (direct-to-main hotfix, no PR — severity:high incident)
**Verdict**: PASS — zero gaps. Status → Pending Ship.

## Reproductions from issue body

| # | Repro | Pre-fix | Post-fix (this run) | Result |
|---|-------|---------|---------------------|--------|
| 1 | `python references/scripts/health_check.py --json` | hangs > 30 s | **0.078 s**, exit 1 with valid JSON (1707 bytes stdout) | PASS |
| 2 | `time tasklist /FI "PID eq <any-pid>" /NH` | ~26 s on this box | N/A — code no longer calls tasklist (verified by grep below) | PASS |

## Code change verification

Files changed in e7a47737 (7 files, 175+/57-):
- `process_utils.py`, `thin_launcher.py`, `boot_remote.py`, `orphan_cleanup.py`, `shared_fs.py`, `squidsquad_cli.py` (6 source files)
- `tests/test_process_utils.py` (+17 tests)

Grep confirms no live regressions:
- `platform.system()` — appears 6× across `references/scripts/` but all in docstrings/comments explaining WHY the code uses `sys.platform` instead. No actual calls.
- `tasklist` — appears 3× in `process_utils.py:24-25` and `thin_launcher.py:76` — all in docstring warnings against using it. No actual calls.

## Test runs

`pytest tests/test_process_utils.py tests/test_thin_launcher.py tests/test_health_check.py tests/test_cycle_pre.py` → **195 passed in 1.00 s** (commit-message claim 17/17 + 178/178 = 195 matches).

## Soft signal

I am running as the QA agent right now — that requires the harness to have spawned an agent, which is exactly the capability #9905 restored. The fact that this verification can execute at all is corroborating evidence that the four-agent boot reported in PM/skill comments is real.

## Notes

- Issue body says #9903 (WMI hang in `platform.system()`) is closed by the same commit. Confirmed in the diff: all 6 files dropped `platform.system()` for `sys.platform`.
- #9904 (`_run_script` lacks timeout) is explicitly orthogonal and stays open per the issue body.
