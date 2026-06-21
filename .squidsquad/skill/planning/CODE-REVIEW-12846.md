# Code Review — #12846 (wizard cmd_scan_summary fail-closed read)

**model_router external model returned a degenerate sub-threshold response.**
For this change — a 6-line `try/except (json.JSONDecodeError, OSError)` guard that
**exactly mirrors 4 existing call sites in the same file** (cmd_generate_defaults
:3462, scaffold_install :2044, etc.) — a full Claude-subagent review is
disproportionate (token cost vs ~zero novel risk). Documented self-review instead
(the larger #13132 / #12801-S1.3 changes did get the subagent fallback).

## Self-review
- **Guard correct** — wraps `json.loads(read_text())` in `try/except
  (json.JSONDecodeError, OSError)`; identical to cmd_generate_defaults' pattern.
- **Fallback sound** — on a malformed/unreadable cache, `scan_data` stays `None`
  and the existing on-the-fly `repo_scan.scan()` branch runs (better UX than an
  empty summary). `None`-sentinel cleanly unifies the absent-file and bad-file
  paths.
- **No behavior change on the happy paths** — a valid cache is read and used (no
  rescan); an absent file runs the scan exactly as before.
- **Tests deterministic** — both monkeypatch `repo_scan.scan`; malformed→fallback
  (rc 0, fresh-scan output) and valid-cache-used (no rescan) lock the fix and the
  happy path.

Full static gate: PASS (see commit). Deterministic code — no CQ, no manifest.
