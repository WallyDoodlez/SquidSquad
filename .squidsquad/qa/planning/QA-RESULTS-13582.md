# QA-RESULTS #13582 — inject-permissions.ps1 em-dash (2 of 2, follow-up to #13577)

**Verdict: PASS → pending-ship.**

## Summary

My own follow-up issue (filed to track the residual left by #13577's
merge-gate-driven PR split). Skill applied the exact 2-hunk em-dash → `-`
content fix already proven correct in PR #13578's earlier, reverted commit —
now merge-gate-clean since `_is_launcher_script` recognizes the path (PR-1
landed first). Also added a `.gitattributes` rule pinning `*.ps1`/`*.bat`/`*.cmd`
to CRLF line endings, preventing autocrlf settings from ever reintroducing
this class of encoding drift.

## Independent verification

- Own raw UTF-8 scan: 0 non-ASCII characters.
- Real PowerShell parser check (`Parser::ParseFile` via `pwsh`): parse clean.
- Full `test_launcher_ascii_safe.py` + `test_13318_consolidated_launcher.py`:
  **18/18 PASS** (was 17/18 with this exact residual — now closed).
- **Full static gate on combined state: PASS — 5511 gated tests, 0 failures,
  0 errors.** This is the first fully-green static gate run this session —
  the entire #13577 class (both files) is now closed.
- Verified the `.gitattributes` addition caused no stray renormalization of
  other tracked files, and both launcher `.ps1` files are consistently CRLF
  with zero bare-LF bytes.

## Records

- `TEST-PLAN-13582.md` — full AC derivation and evidence.

This closes the #13577/#13580/#13582 chain: the original em-dash regression
(#13577), the merge-gate bootstrap-gap documentation (#13580), and this
residual fix (#13582) are all now resolved or tracked.
