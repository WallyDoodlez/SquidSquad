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

## Verdict (original PR shape): PASS — but the PR failed to merge

The exact 3 failures this issue reported are gone; the combined-state static
gate is fully green (0/5501), confirming this closes cleanly against current
main including #13556's just-shipped fix. The adjacent `_is_launcher_script`
allow-list fix is independently verified correct and precisely scoped (exact
match, no `.bak`/path false positives).

**However**: DM's `pr_merge` refused PR #13578 post-approval: `"PR carries
out-of-scope state/vault changes"`. Root-caused live: `_pr_state_scope_violations`
(the #13554 merge-gate) evaluates `_is_launcher_script` against **main-tip's
current** code, not the PR branch's own version — by design (a branch cannot
be trusted to exempt itself). PR #13578 both modified
`.squidsquad/inject-permissions.ps1`'s content AND extended
`_is_launcher_script` to cover that exact path in the same PR — main doesn't
recognize the new exemption yet, so the gate correctly refuses. Confirmed live:
`_pr_state_scope_violations(13578)` on then-current main returned exactly
`['.squidsquad/inject-permissions.ps1']`. DM self-corrected (`pending-ship →
in-progress`), no data loss. Filed the root-cause + a concrete 2-PR-split
remediation as a Discussion comment on #13577 (not a separate issue — squarely
part of this issue's own fix landing).

## RE-VERIFICATION (PR #13578 reworked — split per the diagnosed remediation)

Skill implemented exactly the recommended split: **PR 1 of 2** (this PR, final
shape) = `start.ps1`'s em-dash fix + the `_is_launcher_script` allow-list
extension + tests + a new docstring on `_pr_state_scope_violations`
documenting the bootstrap-sequencing constraint (my remediation suggestion,
applied verbatim) — `inject-permissions.ps1`'s content is **reverted back to
main's current (still-broken) state** in the final commit, deferring its fix
to **PR 2 of 2** once this merges.

| TC | Check | Result |
|----|-------|--------|
| TC7 | Live re-run of `_pr_state_scope_violations(13578)` against the reworked PR | **`[]` — 0 violations, merge-gate now passes** |
| TC8 | `.squidsquad/inject-permissions.ps1` on the reworked branch vs current main | **Byte-identical after CRLF normalization — confirmed clean revert, no content drift** |
| TC9 | `test_launcher_ascii_safe.py` + `test_13318_consolidated_launcher.py` on combined state | **17/18 PASS** — the 1 failure is `inject-permissions.ps1`'s ascii test, exactly the pre-existing, disclosed, deliberately-deferred residual (not a regression) |
| TC10 | Full `test_git_ops.py` on combined state | **259/259 PASS**, 0 regressions from the allow-list/docstring change |
| TC11 | Full static gate on combined state | **1 failure, 0 errors, 5511 gated** (down from 3) — exactly the expected, disclosed residual |

### Scope-completeness call (zero-gap gate)

Issue #13577 as originally filed named **both** files. This PR only closes
the `start.ps1` half — `inject-permissions.ps1`'s identical defect remains
live on main, deferred by a genuine architectural constraint (not a worker
shortcut). Shipping/closing #13577 now without tracking the residual would
let a known gap go silently unrecorded. **Filed #13582** (the `inject-permissions.ps1`
follow-up, PR 2 of 2, with the exact 2-hunk fix already proven correct in this
PR's earlier, reverted commit) before transitioning, so nothing is lost.

## Final Verdict: PASS (scoped to PR #13578's own delivered content)

`start.ps1` fix + `_is_launcher_script` extension + bootstrap-sequencing
docstring are correct, tested, and merge-gate-clean. The `inject-permissions.ps1`
residual is real, disclosed, and now tracked under #13582 — not a silent gap.
