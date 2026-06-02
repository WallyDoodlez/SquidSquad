I now have all the information needed. Here are my findings:

---

### Finding 1

- **File**: `references/scripts/squidsquad_cli.py`
- **Line**: 557–559 (the `elif stored != current:` branch and its `return 1`)
- **Severity**: error
- **Issue**: When `stored != current` (checksum drift detected) **and** `--full` is passed, the compose.py dry-run **never executes**. The `return 1` at line 559 exits `cmd_check` before the `if not full:` guard at line 565 is reached. The `--full` flag is silently ignored.
- **Evidence**:
  - AC4 states `--full` **adds** the A4 drift check — the word "adds" implies it runs *in addition to* the checksum comparison, not only when the checksum matches.
  - The compose.py dry-run provides per-output-file detail about *which composed files* are stale. When checksums differ, the operator gets only the checksum-mismatch report (which says "something changed" but not *what composed outputs need regeneration*). The operator never sees the more detailed A4 diagnostics they explicitly requested.
  - All three `TestFullFlag` tests (lines 199, 218, 233) only exercise the path where checksums **match**. No test covers `full=True` + `stored != current`, which would have caught this.
  - Control-flow trace: line 557 `elif stored != current:` → line 559 `return 1` — function exits **before** line 564 `# AC4: --full adds the A4 drift check` and line 565 `if not full:`.

- **Suggested fix**: Defer the drift exit so `--full` always runs when passed. Replace the early `return 1` with a flag, then decide the exit code after the optional dry-run:

  ```python
  drift = False
  if stored is None:
      print("compose freshness: no stored checksum ...")
  elif stored != current:
      print(_format_drift_report(stored, current, repo_root), file=sys.stderr)
      drift = True
  else:
      print("compose freshness: clean")

  if not full:
      return 1 if drift else 0

  # --full: always run the dry-run ...
  # ... after dry-run, if it also returns 1, drift stays True
  # Final exit: return 1 if drift else 0 (or 2 on error)
  ```

---

### Finding 2

- **File**: `references/scripts/squidsquad_cli.py`
- **Line**: 480–489 (`_enumerate_drifted_paths`)
- **Severity**: warning
- **Issue**: The drift report enumerates **ALL** compose-input files (not just changed ones) by calling a **private** function `_cf._iter_compose_input_files` with **no error handling**. If that private function is renamed, removed, or raises an exception (e.g. permission error during `repo_root.glob()`), the exception propagates unhandled through `_format_drift_report` → `cmd_check`, causing a Python traceback instead of a clean exit 2.
- **Evidence**:
  - Line 482: `for path in _cf._iter_compose_input_files(repo_root):` — the underscore prefix marks this as a private API of `compose_freshness`. The public API is `compute_compose_checksum` (used correctly on line 544); `_iter_compose_input_files` is an implementation detail.
  - There is no `try`/`except` around this call. If `_iter_compose_input_files` is removed or its signature changes in a future compose_freshness refactor, the drift report crashes instead of surfacing exit 2.
  - Listing *all* files in a large repo (hundreds of paths) produces a noisy report. The docstring on line 471–478 acknowledges per-file hashes aren't stored, but the report still claims to help the operator diagnose "WHICH files changed" on line 504 — while actually listing every file rather than the diff.
- **Suggested fix**: Either:
  - (a) Wrap the enumeration call in `try`/`except` and on failure append a fallback line like `(could not enumerate input files: <reason>)` to the report instead of crashing; or
  - (b) Expose `_iter_compose_input_files` as a public function in `compose_freshness` (rename to `iter_compose_input_files`), making the dependency explicit and stable.

---

### Finding 3

- **File**: `references/scripts/squidsquad_cli.py`
- **Line**: 591–593
- **Severity**: warning
- **Issue**: The `--full` dry-run exit-code mapping trusts that `compose.py deploy-all --check` uses exit code 1 **exclusively** for "drift detected" and exit codes ≥2 for "error." If `compose.py` ever returns exit code 1 for a non-drift failure (e.g., an unhandled Python exception, which `sys.exit(1)` would produce), the CLI misreports it as "drift detected" (exit 1) instead of "error" (exit 2).
- **Evidence**:
  - The comment at line 592 says `# A4's drift exit. Map onto our exit 1` and line 594 says `# A4 maps unhandled errors to exit 2 / sys.exit`. This assumes compose.py strictly partitions exit codes: 0=clean, 1=drift, ≥2=error.
  - `compose_freshness.py` line 239 shows a different treatment: `if returncode != 0:` treats *any* non-zero from `compose.py deploy-all` (without `--check`) as failure. This demonstrates that compose.py exit code semantics vary by flag, making the mapping fragile.
  - A `compose.py` bug that triggers `sys.exit(1)` (the Python default for unhandled exceptions in some frameworks) would be reported as "drift" rather than "error," misleading the operator about the nature of the problem.
- **Suggested fix**: Capture and log the compose.py stderr regardless of exit code, and consider distinguishing "known drift" (exit 1 with parseable drift output) from "unexpected exit 1" (exit 1 with a traceback on stderr). At minimum, document the contract assumption explicitly so future compose.py maintainers know the exit code partition is load-bearing.

---

### No State Mutation Found (AC7)

I specifically traced every code path in `cmd_check`, `_load_state_checksum`, `_enumerate_drifted_paths`, `_format_drift_report`, and the subprocess invocation for AC7 violations. The code is genuinely read-only regarding project state:

- The state file is only **read** (line 461, `state_file.read_text`), never written.
- The subprocess always passes `--check` (line 574), never the mutating `deploy-all`.
- `sys.path.insert(0, ...)` at line 530 mutates global interpreter state (not project state files); it's a one-shot CLI process so accumulation is harmless.
- The drift report's advice text at line 503 (`Run ... compose.py deploy-all`) is purely informational — the CLI does not execute it.

The AC7 test at line 163–171 correctly confirms the state file is byte-identical before/after.