# TEST-PLAN #13582 — inject-permissions.ps1 em-dash (2 of 2, follow-up to #13577)

**Derived from my own issue body's contract — independent reading.**

## Acceptance Criteria (independent reading)

| AC | Contract |
|----|----------|
| AC1 | `.squidsquad/inject-permissions.ps1` has 0 non-ASCII characters |
| AC2 | File still parses cleanly as valid PowerShell |
| AC3 | `test_launcher_ascii_safe.py`'s previously-red `inject-permissions.ps1` test now passes |
| AC4 | Full static gate on combined state returns to 0 failures — main's gate is fully clean |
| AC5 | No unrelated content drift — the fix is byte-identical to the content already proven correct in PR #13578's earlier (reverted) commit |
| AC6 (unplanned addition, verify it's safe) | The PR also adds a `.gitattributes` CRLF-pinning rule for `*.ps1`/`*.bat`/`*.cmd` — verify it doesn't cause stray renormalization of other tracked files or break anything |

## Verification (branch squidsquad/task/13582, freshly fetched, merged with current origin/main — 5 commits ahead)

| TC | AC | Check | Result |
|----|----|-------|--------|
| TC1 | AC1 | My own raw UTF-8 scan | 0 non-ASCII chars |
| TC2 | AC2 | Real PowerShell parser (`Parser::ParseFile` via `pwsh`) | PARSE CLEAN |
| TC3 | AC3 | Full `test_launcher_ascii_safe.py` + `test_13318_consolidated_launcher.py` | **18/18 PASS** (was 17/18 with 1 known residual — now closed) |
| TC4 | AC4 | Full static gate on combined state | **PASS — 5511 gated tests, 0 failures, 0 errors** — main's gate is fully green |
| TC5 | AC5 | Diff review — the 2-hunk content change matches PR #13578's earlier reverted commit exactly | Confirmed identical |
| TC6 | AC6 | `git status --short` post-merge (no stray renormalized files), `file`/byte-level line-ending check on both `.ps1` files (consistent CRLF, 0 bare LF) | Clean — no unintended renormalization, both launcher files consistently CRLF |

## Verdict: PASS

Closes the #13577 class fully: both files now 0 non-ASCII, both parse clean,
main's static gate returns to fully green (0/5511) for the first time this
session. The `.gitattributes` CRLF-pinning addition is a reasonable defensive
measure (prevents autocrlf drift from reintroducing this class) and verified
not to have caused any collateral renormalization.
