Now I have all the information needed. Let me compile my findings.

---

### Finding 1

- **File**: tests/run_tests.py
- **Line**: 151-155
- **Severity**: error
- **Issue**: When `discover_static_modules()` returns an empty list (all `test_*.py` files are excluded via dicts + `_live` suffix), the subprocess command becomes `python -m pytest -v --tb=short` with **zero file arguments**. Pytest then auto-discovers recursively from `cwd` (the repo root, line 154) and runs **every** test file — including all `_live` tests, all `KNOWN_FAILURES` tests, all `KNOWN_NON_STATIC` tests, and all `tests/integration/test_*.py` integration tests. This silently defeats the entire exclusion mechanism.

- **Evidence**: 
  - Line 153: `+ [str(TESTS_DIR / f"{mod}.py") for mod in modules]` produces an empty list when `modules` is empty
  - There is no `pyproject.toml`, `pytest.ini`, or `setup.cfg` in the repo to constrain `testpaths` — confirmed by glob search returning no matches
  - Pytest's documented default behavior with no file/directory arguments is to discover `test_*.py` recursively from the current directory
  - The `test_no_silent_ungating` invariant test (test_11394_static_discovery.py, line 33-45) cannot catch this: it verifies every file is *accounted for*, which would still pass when gated is empty but all files are in exclusion dicts. The `test_gate_survives_a_deleted_gated_file` test (line 108) asserts `gated` is non-empty, but that is a single test assertion, not a runtime guard in `run_tests.py`.

- **Suggested fix**: Add a guard at the top of `run_static_tests()` (after line 137) that checks for empty modules and either fails fast or skips with a warning, rather than falling through to a bare `pytest` invocation. For example:
  ```python
  if not modules:
      print("ERROR: No static test modules discovered — gate configuration may be broken.")
      return False
  ```

---

### Finding 2

- **File**: tests/run_tests.py
- **Line**: 142-150
- **Severity**: warning
- **Issue**: The NOTICE block that prints exclusion information is gated solely on `if excluded:` (line 142), where `excluded` is built *only* from `KNOWN_NON_STATIC` and `KNOWN_FAILURES` dict entries. If both dicts are empty but `*_live.py` files exist, `excluded` is `[]` (falsy) and the entire NOTICE block is skipped — even though `_live` files are still excluded. This contradicts the stated design that "NOTICE prints exclusions each run."

- **Evidence**:
  - Line 138-141: `excluded` is constructed exclusively from `KNOWN_NON_STATIC.items()` and `KNOWN_FAILURES.items()`. The `_live` suffix exclusion (the third exclusion layer) is only counted as `live_n` *inside* the `if excluded:` block (line 143).
  - If both `KNOWN_NON_STATIC` and `KNOWN_FAILURES` are empty (e.g., after all tracked failures are resolved), `excluded = []`, the `if` body never executes, and no exclusion notice is printed.
  - The `_live` exclusion is a first-class exclusion mechanism (documented at line 47–49 of the module docstring), so omitting it from the NOTICE when it's the sole active exclusion is inconsistent.

- **Suggested fix**: Restructure the condition so the NOTICE prints whenever there is anything to report. For example, compute `live_n` before the condition and use `if excluded or live_n:`:
  ```python
  live_n = sum(1 for p in TESTS_DIR.glob(f"test_*{LIVE_SUFFIX}.py"))
  if excluded or live_n:
      print(
          f"NOTICE: gating {len(modules)} static test file(s); "
          f"{len(excluded)} excluded by allowlist + {live_n} *_live (run separately):"
      )
      for name, kind, reason in excluded:
          print(f"  - {name} [{kind}]: {reason}")
      print()
  ```

---

### Finding 3

- **File**: tests/test_11394_static_discovery.py
- **Line**: 102
- **Severity**: warning
- **Issue**: The statement `import run_tests` inside `test_gate_survives_a_deleted_gated_file` is dead code. The module `run_tests` is already imported at the top of the file (line 21–26), and the local `import` is not used anywhere in the function body (no attribute access on `run_tests`). The function uses `discover_static_modules`, `TESTS_DIR`, `type(TESTS_DIR)`, and `monkeypatch` — none of which require the re-import.

- **Evidence**: 
  - Line 21-26: `from run_tests import (LIVE_SUFFIX, KNOWN_NON_STATIC, KNOWN_FAILURES, discover_static_modules)` already imports `discover_static_modules` at module level.
  - Line 102: `import run_tests` — the name `run_tests` is never referenced again in the function (lines 99–120).
  - This has no runtime impact (Python caches the module), but it's misleading and suggests the import was accidentally left from an earlier revision.

- **Suggested fix**: Remove line 102 (`import run_tests`).