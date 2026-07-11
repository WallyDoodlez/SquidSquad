# Code Review — #13145 (repo_scan.py main() exit-2 contract)

**Documented self-review** (per the #12846 precedent). repo_scan.py is a
deterministic utility script — NOT base/role-shared instructions, the compose
pipeline, or a shared sub-skill — so it is not high-blast-radius, and a full
DeepSeek subagent review is disproportionate for two small guards that mirror
patterns already in the file. (The larger #13113 / #10540 harness/ship-path
changes this session did get the DS subagent.)

## Self-review

- **F2 correct** — `--path` is now matched unconditionally; the no-value case
  (`i + 1 >= len(args)`) prints `--path requires an argument` and returns 2,
  before any scan runs. The has-value path is unchanged (assigns `root`,
  then the existing not-exists → 2 guard). No behavior change for valid
  `--path <dir>`.
- **F1 correct** — the `mkdir` + `write_text` are wrapped in `try/except
  OSError` → `Cannot save to ...` + return 2. `FileExistsError`,
  `PermissionError`, and read-only-FS errors are all `OSError` subclasses, so
  all are caught. Mirrors the sibling `try/except OSError` guards in
  `_check_python_deps` / `_check_package_json_deps`.
- **Contract honored** — the module docstring already contracts `0 / 2`; both
  fixes bring `main()` into compliance. No new exit codes introduced.
- **No happy-path regression** — `--save` to a writable target still writes and
  returns 0 (`test_save_flag` still green); valid `--path` still scans and
  returns 0 (`test_outputs_json`).
- **Tests deterministic** — F2 via a bare `--path`; F1 via a `.squidsquad`
  that exists as a FILE so `mkdir(parents=True, exist_ok=True)` raises
  `FileExistsError` (no monkeypatch, cross-platform).

Full static gate: PASS 4858/0/0. Deterministic utility — no CQ, no manifest
(no new installer-tracked files).
