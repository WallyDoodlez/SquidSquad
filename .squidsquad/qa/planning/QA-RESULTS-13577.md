# QA-RESULTS #13577 — non-ASCII em-dash in Windows launchers breaks PS 5.1 parsing

**Verdict: PASS → pending-ship.**

## Summary

My own issue, filed during #13556's re-verification pass (unrelated to that
PR): the static gate was red on a clean `origin/main` due to a literal em-dash
(U+2014, no BOM) in `.squidsquad/start.ps1` and `.squidsquad/inject-permissions.ps1`
— a real functional risk for operators on Windows PowerShell 5.1 (ANSI-codepage
misdecode), not just a gate cosmetic. Skill replaced all 7 em-dashes with a
plain ASCII `-` (converged with PM's report of an identical uncommitted fix
already proven-live in the primary clone, avoiding a future boot-pull
collision). Adjacent root-cause fix: `inject-permissions.ps1` was missing from
`git_ops._is_launcher_script`'s allow-list, so the #11511 state guard was
silently unstaging its own fix commits on feature branches — added (exact
match, tested against `.bak` false positives).

## Independent verification

- My own raw UTF-8 scan of both files (not the test's own logic): 0 non-ASCII
  characters.
- My own live PowerShell parser check (`Parser::ParseFile` via `pwsh`, not
  Python-side heuristics): both files parse clean, 0 errors.
- My own 6-case direct probe of `_is_launcher_script` covering the PR's own
  scenario plus `.bak`, a nested path, and a bare filename — all correct, no
  false positives.
- Read the full diff line-by-line: every changed hunk is a `#`-comment or a
  `Write-Host`/inline-comment string — confirmed no functional/logic change
  smuggled in alongside the encoding fix.
- Full `test_launcher_ascii_safe.py` + `test_13318_consolidated_launcher.py`:
  **18/18 PASS**.
- **Full static gate on the combined state (main + PR, main now 7 commits
  ahead incl. #13556's own merge): PASS — 5501 gated tests, 0 failures, 0
  errors.** This is the decisive proof — the exact 3 failures this issue
  reported are gone.

## Records

- `TEST-PLAN-13577.md` — full AC derivation and evidence.
