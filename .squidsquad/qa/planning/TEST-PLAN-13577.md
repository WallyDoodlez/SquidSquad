# TEST-PLAN #13577 — non-ASCII em-dash in Windows launchers breaks PS 5.1 parsing

**Derived from the issue's own contract (my own filed issue from #13556's verify pass) — independent reading.**

## Acceptance Criteria (independent reading)

| AC | Contract |
|----|----------|
| AC1 | `.squidsquad/start.ps1` and `.squidsquad/inject-permissions.ps1` contain zero non-ASCII characters |
| AC2 | Both files still parse cleanly as valid PowerShell — the fix is a pure encoding swap, not a functional edit |
| AC3 | `test_launcher_ascii_safe.py`'s previously-red tests now pass; no new red |
| AC4 | Adjacent fix: `git_ops._is_launcher_script` allow-list includes `inject-permissions.ps1` (exact match only — no false-positive on `.bak`/nested paths) so its own bug-fix commits aren't silently stripped by the #11511 state guard |
| AC5 | Full static gate on the combined (main + PR) state is fully green — proves main's gate genuinely clears once merged |
| AC6 | No unrelated functional change smuggled in — diff is comment/string content only |

## Verification (branch squidsquad/task/13577, freshly fetched, merged with current origin/main — 7 commits ahead, included #13556's own merge landing on main)

| TC | AC | Check | Result |
|----|----|-------|--------|
| TC1 | AC1 | **My own** independent scan (not the test's own logic) — read both files as UTF-8, checked every char for `ord(ch) > 127` | **0 non-ASCII chars found** |
| TC2 | AC2 | **My own** live check using the real PowerShell parser (`[System.Management.Automation.Language.Parser]::ParseFile`) on both files via `pwsh` | **PARSE CLEAN — 0 errors, both files** |
| TC3 | AC3 | Full `tests/test_launcher_ascii_safe.py` + `tests/test_13318_consolidated_launcher.py` | **18/18 PASS** |
| TC4 | AC4 | **My own** direct probe of `git_ops._is_launcher_script` with 6 cases incl. the exact PR scenario, `.bak`, nested path, and bare filename | **All 6 match expected** — no false positives |
| TC5 | AC5 | Full static gate on combined state | **PASS — 5501 gated tests, 0 failures, 0 errors** (was 3 failures pre-fix; this is the decisive proof) |
| TC6 | AC6 | Read the full diff — every hunk is either a `#`-comment line or a `Write-Host`/inline-comment string; no logic lines touched | Confirmed comment/string-only |

## Verdict: PASS

The exact 3 failures this issue reported are gone; the combined-state static
gate is fully green (0/5501), confirming this closes cleanly against current
main including #13556's just-shipped fix. The adjacent `_is_launcher_script`
allow-list fix is independently verified correct and precisely scoped (exact
match, no `.bak`/path false positives).
