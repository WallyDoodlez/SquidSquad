## Review Summary

After thorough analysis of both files, I find the implementation **correct and complete** against the acceptance criteria. The design is cause-agnostic and fail-closed — exactly as required. Below are the specific areas scrutinized and why each passes.

---

### 1. Correctness against AC1 (gate non-zero on any failure)

- `_static_gate_verdict` returns `False` for: missing junit, malformed XML, zero tests, failures/errors > 0, non-zero returncode. All paths lead to `run_static_tests()` returning `False` → `main()` returns `1`.
- Test coverage confirms each path: `test_verdict_fails_on_recorded_failures`, `test_verdict_fails_on_recorded_errors`, `test_verdict_fails_on_nonzero_returncode_with_clean_junit`.

### 2. Correctness against AC3 (gate fails on incomplete run)

- Missing junit (canonical hard-exit signature) → `"INCOMPLETE RUN"`. Tested by `test_verdict_fails_on_missing_junit_even_with_returncode_zero`.
- Malformed/truncated junit → caught via `ET.ParseError`. Tested by `test_verdict_fails_on_malformed_junit`.
- Zero tests recorded → `"0 tests"`. Tested by `test_verdict_fails_on_zero_tests`.
- End-to-end hard-exit simulation: `test_gate_fails_when_pytest_hard_exits_false_green` monkeypatches `subprocess.run` to return rc=0 with no junit written, and verifies `run_static_tests()` returns `False`.

### 3. Edge cases in XML parsing — all handled

| Edge case | Mechanism | Test |
|---|---|---|
| `<testsuites>` root (xunit2 default) | `root.findall("testsuite")` | `test_verdict_passes_on_complete_clean_junit` |
| Bare `<testsuite>` root (xunit1) | `suites = [root]` | `test_verdict_handles_bare_testsuite_root` |
| Unknown root element | fallback `root.findall(".//testsuite")` | Safe: if no suites found → total=0 → fail |
| Missing attribute on a `<testsuite>` | `s.get("tests", "0")` defaults to `"0"` | Built-in |
| Multiple `<testsuite>` elements | `sum(...)` across all suites | General case |
| Empty junit / parse error | `ET.ParseError` caught | `test_verdict_fails_on_malformed_junit` |
| File exists but is not junit (e.g., `<html>`) | fallback finds 0 `<testsuite>` → total=0 → fail | Covered by structure |

### 4. No behavioral regressions

- **Old**: `run_static_tests()` returned `returncode == 0`.
- **New**: returns `True` only with clean junit (≥1 test, 0 failures, 0 errors) AND returncode 0.
- All legitimate pytest sessions that previously passed (returncode 0, junit written, tests passed) continue to pass.
- The empty-modules guard (lines 122-128 of `run_tests.py`) prevents pytest from falling back to recursive auto-discovery, which was an existing safety mechanism preserved in this change.
- Module discovery (`discover_static_modules`) and exclusions (`KNOWN_NON_STATIC`, `KNOWN_FAILURES`, `LIVE_SUFFIX`) are unchanged.

### 5. Integration points — sound

- Temp file lifecycle: `mkstemp` → close → unlink → pytest creates it → verdict reads it → `finally` unlinks. Clean in all paths (success, failure, exception). Verified by `test_gate_cleans_up_its_junit_temp_file`.
- `--junit-xml` flag is verifiably passed to pytest. Verified by `test_gate_requests_junit_from_pytest`.
- `run_static_tests()` and `run_integration_tests()` remain separate code paths in `main()`; no cross-contamination.

---

## Conclusion

```
NO_FINDINGS
```

The implementation satisfies all acceptance criteria, handles every XML edge case explicitly, has comprehensive regression tests, and introduces no behavioral regressions. The fail-closed design is cause-agnostic and robust against the full class of mid-run hard-exit bugs.