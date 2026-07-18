# QA-RESULTS #13577 — non-ASCII em-dash in Windows launchers breaks PS 5.1 parsing

**Verdict: PASS → pending-ship, scoped to PR #13578's own delivered content (start.ps1 half). The inject-permissions.ps1 half is tracked separately as #13582 — see Scope note below.**

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

## Merge-gate failure, diagnosis, and scope split

The original PR shape (both files fixed in one PR) verified PASS but **failed
to merge**: DM's `pr_merge` refused with "PR carries out-of-scope state/vault
changes." Root-caused live: the #13554 merge-gate evaluates `_is_launcher_script`
against main-tip's *current* code, not the PR's own updated version (by
design — a branch can't be trusted to exempt itself from the guard). The PR
both modified `inject-permissions.ps1`'s content AND extended the allow-list
to cover it in the same PR, so main's not-yet-updated classifier correctly
refused it. DM self-corrected (`pending-ship → in-progress`), no data loss.
Posted the root cause + a concrete 2-PR-split remediation directly on #13577.

Skill reworked the PR into exactly that split: **PR 1 of 2** (verified here)
= `start.ps1` fix + the allow-list extension + a docstring documenting the
bootstrap constraint for future readers; `inject-permissions.ps1`'s content
was reverted back to main's still-broken state, deferred to **PR 2 of 2**.

Re-verified the reworked PR independently: live re-run of
`_pr_state_scope_violations(13578)` now returns `[]` (merge-gate clear);
confirmed `inject-permissions.ps1` is byte-identical to current main (clean
revert, no drift); `test_launcher_ascii_safe.py` + `test_13318_consolidated_launcher.py`
17/18 PASS (the 1 failure is the disclosed, deferred residual, not a
regression); full `test_git_ops.py` 259/259; full static gate 1 failure / 0
errors across 5511 gated tests (down from 3 — exactly the expected outcome).

**Scope-completeness call**: #13577 as filed named both files; this PR only
closes the `start.ps1` half. Shipping it without tracking the
`inject-permissions.ps1` residual would let a known, disclosed gap go
unrecorded. Filed **#13582** (severity high, exact fix already proven in this
PR's earlier reverted commit) before transitioning — the residual is real but
not silent.

## Records

- `TEST-PLAN-13577.md` — full AC derivation and evidence, both verification passes.
- Filed #13580 (merge-gate bootstrap-gap documentation, improvement-scan) and
  #13582 (`inject-permissions.ps1` follow-up, PR 2 of 2).
