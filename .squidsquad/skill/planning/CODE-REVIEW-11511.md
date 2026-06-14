After a thorough review of the new code — the `check_real_conflict` function (lines 989–1032), the `check-real-conflict` dispatch in `main()` (lines 1135–1143), the usage doc addition (line 24), and the `TestCheckRealConflict11511` test class (lines 1683–1729 of the test file) — I find no correctness issues, regressions, or philosophy violations.

**Summary of what was verified:**

| Concern | Result |
|---|---|
| **`merge-tree --write-tree` exit-code semantics** | Correct. `returncode != 0` → conflict; `returncode == 0` → clean. Exit-code-based detection is robust even if the optional `stdout` conflict-line extraction produces zero matches. |
| **Ref-resolution short-circuit** | Correct. Both refs are validated via `rev-parse --verify --quiet` before any `merge-tree` call. If either resolution fails, the function returns `None` immediately (lines 1008–1013). Test `test_unresolvable_ref_returns_none` confirms this with `call_count == 1`. |
| **Direction symmetry** | Correct. Both `(base, head)` and `(head, base)` are evaluated (line 1017); an OR of the two results determines the verdict. |
| **Exit-code mapping in `main()`** | Correct. `None` → exit 2, `True` → exit 0, `False` → exit 1 (lines 1140–1143). Matches the documented contract (line 24: `exit 0=clean/1=conflict/2=err`). |
| **No regression to existing dispatch** | The new `elif cmd == "check-real-conflict":` block is purely additive. No existing branch modified. |
| **ASCII-safe prints (cp1252)** | All new `print()` strings use only ASCII characters (verified character-by-character). The existing `TestNoNonAsciiInPrintStatements` regression test passes. |
| **`check=False` on all subprocess calls** | Both `rev-parse` and `merge-tree` calls pass `check=False`, so `CalledProcessError` will never mask exit-code inspection. |
| **Test coverage** | Four test cases cover: clean merge, real conflict, conflict in either direction, and unresolvable-ref short-circuit. Return values (`True`/`False`/`None`) and call-count assertions are correct. |
| **De-duplication of conflict lines** | Uses `dict.fromkeys()` (lines 1030) which preserves insertion order in Python 3.7+. |
| **Usage doc** | Line 24 accurately reflects the command signature and exit codes. |

NO_FINDINGS