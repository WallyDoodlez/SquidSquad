# TEST-PLAN-13589 — bounded retry + diagnostics for the empty-output CLI subprocess flake

**Source**: GitHub issue #13589 body (Observation + Suggested direction, bug-report shape).
**Derived without reading the diff first.**

## Acceptance Criteria (derived from the issue's stated problems + skill's implemented scope)

- **AC1**: `TestCli._run` detects the exact flake signature (`returncode != 0` AND both stdout and stderr empty) and retries the identical subprocess call exactly once.
- **AC2**: A retry that produces real output (`returncode == 0` or non-empty stdout/stderr) is treated as the confirmed transient flake and returned as-is.
- **AC3**: A retry that ALSO returns the empty signature is NOT treated as the known flake — diagnostics (cmd, cwd, sys.executable, whether wizard.py exists) are appended to stderr so a real regression stays actionable, not silently retried away.
- **AC4**: Scoped to the shared `_run` helper, covering every `TestCli` subprocess-spawning test, not just the originally-reported one.
- **AC5**: Every retry occurrence is logged (WARNING/INFO to stderr) — never silently papers over.
- **AC6 (non-regression)**: A real, non-empty-output failure is NOT retried — fails immediately as before.

## Test Cases

### TC-1 (covers AC1-AC3, AC6): Worker's own regression suite
- **Steps**: `TestCliRunRetryDiagnostics13589` — 4 cases covering transient-flake retry, no-retry-on-real-failure, diagnostics-on-persistent-empty, no-retry-on-first-try-success.
- **Result**: PASS, 4/4.

### TC-2 (covers AC4, decisive): Real (unmocked) CLI path unaffected
- **Steps**: Ran the FULL `test_wizard_13337_deny_list.py` suite, including `test_cli_happy_path_envelope` and all sibling `TestCli` tests — these exercise the real, unmocked `_run` → real `subprocess.run` → real `wizard.py merge-deny-list` CLI invocation (only the new `TestCliRunRetryDiagnostics13589` class uses monkeypatched `subprocess.run`).
- **Expected**: All pass on the real (non-flaking, this run) CLI path — confirms the retry wrapper doesn't interfere with normal successful invocations.
- **Result**: PASS, 29/29 (all `TestCli` tests + new retry-diagnostics tests).

### TC-3 (covers AC5): Logging present
- **Steps**: Code read — confirmed WARNING print on first-flake-detected, INFO print on confirmed-transient, diagnostic print + stderr-append on persistent failure.
- **Result**: PASS.

### TC-4: Full regression + static gate
- **Steps**: Combined-state static gate (branch merged with current main).
- **Result**: pending at write time.

## Coverage matrix
- AC1 → TC-1
- AC2 → TC-1
- AC3 → TC-1
- AC4 → TC-2
- AC5 → TC-3
- AC6 → TC-1
