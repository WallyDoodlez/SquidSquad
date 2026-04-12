# FEAT-SKILL-442 QA Results -- Rename feature/bug to task/issue

**QA Date**: 2026-04-11
**Tester**: QA subagent (PM-spawned)
**Branch**: main (commit a88749e)

---

## Test Cases

### TC-1: tracker.py create-issue command works
- **Result**: PASS
- **Notes**: `create-issue` command exists in help output. Creates issues with `ISSUE:` prefix, `type:issue` label, correct severity/role/squidsquad labels. Verified via alias test (TC-13) which used `create-bug` alias and confirmed `type:issue` label on #456.

### TC-2: tracker.py create-task command works
- **Result**: PASS
- **Notes**: `create-task` command exists in help output with correct usage line. Help shows `TASK:` prefix and `type:task` label behavior.

### TC-3: tracker.py list-issues command works
- **Result**: PASS
- **Notes**: `list-issues` command works and returns issues with `type:issue` label. Tested via `list-bugs` alias (TC-14) which returned 2 issues with correct `type:issue` labels.

### TC-4: tracker.py list-tasks command works
- **Result**: PASS
- **Notes**: `list-tasks` command exists in help. Tested via `list-features` alias (TC-14) which returned tasks with `type:task` labels.

### TC-5: tracker.py list-all-open returns both types
- **Result**: PASS
- **Notes**: `list-all-open` returns items with both `type:issue` and `type:task` labels.

### TC-6: tracker.py transition works with new labels
- **Result**: PASS
- **Notes**: Integration tests (17/17 passed) include full status flow tests for both bug and feature paths, confirming transitions work correctly with new label names.

### TC-7: compose.py produces correct CLAUDE.md with renamed sub-skills
- **Result**: FAIL
- **Notes**: PM and skill CLAUDE.md files are clean (0 matches for old vocabulary). However, DM CLAUDE.md contains residual old vocabulary:
  - `bug-triage` sub-skill marker (lines 307, 342)
  - `list-bugs dm` command reference (line 315)
  - `create-bug` command reference (line 335)
  - `type:bug`/`type:feature` in file-conventions (line 926)

  Root cause: `references/sub-skills/dm-specific/bug-triage.md` was NOT renamed to `issue-triage.md`, and `references/roles/dm/CLAUDE.md` still has `{{include: dm-specific/bug-triage}}`. The file itself also contains old command references.

### TC-8: GitHub labels renamed on repo
- **Result**: PASS
- **Notes**: `gh label list --search "type:"` returns `type:issue` and `type:task`. No `type:bug` or `type:feature` labels exist.

### TC-9: Open issue titles renamed (FEAT: to TASK:, BUG: to ISSUE:)
- **Result**: PASS
- **Notes**: 0 open issues with `FEAT:` prefix, 0 open issues with `BUG:` prefix. Open issues use `TASK:` and `ISSUE:` prefixes.

### TC-10: statusline.sh uses new label names
- **Result**: FAIL
- **Notes**: `.squidsquad/statusline.sh` still uses `type:bug` (line 233), `type:feature` (lines 234, 235, 236, 240). Zero matches for `type:issue` or `type:task`. This means the status bar queries will return 0 results for all issue/task counts.

### TC-11: Full test suite passes
- **Result**: PASS
- **Notes**: 518 static tests passed, 17 integration tests passed. Exit code 0. No assertion errors related to old label names.

### TC-12: /squidsquad-issue command works (renamed from /squidsquad-bug)
- **Result**: FAIL
- **Notes**: `SKILL.md` still contains `/squidsquad-bug` (line 383, 385). No `/squidsquad-issue` command found.

### TC-13: Old commands create-bug / create-feature no longer work (or alias gracefully)
- **Result**: PASS
- **Notes**: `create-bug` works as an alias and creates the issue with new labels (`type:issue`, `ISSUE:` prefix). Help output documents the aliases: `(alias: create-bug)`, `(alias: create-feature)`.

### TC-14: Old commands list-bugs / list-features no longer work (or alias gracefully)
- **Result**: PASS
- **Notes**: `list-bugs` and `list-features` work as aliases. `list-bugs` returns items with `type:issue` labels. `list-features` returns items with `type:task` labels. Help output documents aliases.

### TC-15: Generic English "feature" and "bug" NOT renamed in manifest.py
- **Result**: PASS
- **Notes**: `grep "walker bug" references/scripts/manifest.py` returns the original line: "walker non-terminating, that's a walker bug, not a manifest bug." Generic English preserved.

### TC-16: Generic English "feature/test" branch NOT renamed in test_git_ops.py
- **Result**: PASS
- **Notes**: `tests/test_git_ops.py` still contains `"feature/test"` branch name (lines 182-183). Generic git convention preserved.

### TC-17: Historical CHANGELOG entries untouched
- **Result**: PASS
- **Notes**: `git diff HEAD -- CHANGELOG.md` shows no changes. Historical entries preserved.

### TC-18: Closed GitHub Issue titles untouched
- **Result**: PASS
- **Notes**: Closed issues retain `FEAT:` (2 found) and `BUG:` (18 found) prefixes. Examples: `#328: FEAT: Intent-driven setup wizard`, `#436: BUG: Improvement scan criteria hardcoded`.

### TC-19: Planning artifacts keep FEAT- prefix in filenames
- **Result**: PASS
- **Notes**: `FEAT-SKILL-442-RESEARCH.md`, `FEAT-SKILL-442-CONTEXT.md`, `FEAT-SKILL-442-TEST-PLAN.md` all exist with original filenames.

### TC-20: Severity label description updated
- **Result**: FAIL
- **Notes**: `wizard.py` still has `"severity": "Bug severity"` (line 805). Should be `"Issue severity"`. Severity label names themselves (`severity:high/medium/low`) are correctly preserved.

### TC-21: diagnostics.py uses "Issue Report" (not "Bug Report")
- **Result**: FAIL
- **Notes**: `diagnostics.py` still has `"## Bug Report -- SquidSquad"` (line 160). Should be `"## Issue Report -- SquidSquad"`.

### TC-22: Sub-skill file renames complete -- old files do not exist
- **Result**: FAIL
- **Notes**: Most renames completed correctly. Failures:
  - `references/sub-skills/dm-specific/bug-triage.md` STILL EXISTS (should be `issue-triage.md`)
  - `references/sub-skills/dm-specific/issue-triage.md` DOES NOT EXIST
  - `.github/ISSUE_TEMPLATE/bug-report.yml` STILL EXISTS (should be `issue-report.yml`)
  - `.github/ISSUE_TEMPLATE/feature-request.yml` STILL EXISTS (should be `task-request.yml`)
  - `.github/ISSUE_TEMPLATE/issue-report.yml` DOES NOT EXIST
  - `.github/ISSUE_TEMPLATE/task-request.yml` DOES NOT EXIST

  Successfully renamed: common/issue-filing.md, pm-specific/issue-filing.md, pm-specific/task-intake.md, pm-specific/task-approval.md, qa-specific/issue-filing.md, dm-specific/issue-filing.md, designer-specific/issue-filing.md.

### TC-23: Include directives updated to match new filenames
- **Result**: FAIL
- **Notes**: Most include directives updated correctly. One failure:
  - `references/roles/dm/CLAUDE.md` still has `{{include: dm-specific/bug-triage}}` (line 102). Should be `{{include: dm-specific/issue-triage}}`.

  All other includes (`issue-filing`, `task-intake`, `task-approval`) are correctly updated.

### TC-24: cycle.py CLI flags and template strings updated
- **Result**: FAIL
- **Notes**: cycle.py NOT updated:
  - `--bugs` flag still present (lines 15, 214). Should be `--issues`.
  - `--features` flag still present. Should be `--tasks`.
  - `"Bugs Fixed"` template string (line 129). Should be `"Issues Fixed"`.
  - `"Features Progressed"` template string (line 130). Should be `"Tasks Progressed"`.

### TC-25: GitHub Issue templates updated
- **Result**: FAIL
- **Notes**: GitHub Issue templates NOT renamed:
  - `bug-report.yml` still exists with `labels: ["type:bug"]` (line 4)
  - `feature-request.yml` still exists with `labels: ["type:feature"]` (line 4)
  - `issue-report.yml` does not exist
  - `task-request.yml` does not exist

### TC-26: tracker.py check-gh still works
- **Result**: PASS
- **Notes**: Returns "OK" with exit code 0.

### TC-27: tracker.py comment command unchanged
- **Result**: PASS (inferred)
- **Notes**: Comment command present in help output, unchanged by rename. Integration tests pass including status flow tests that use comment-like operations.

### TC-28: tracker.py get-labels / get-state still work
- **Result**: PASS (inferred)
- **Notes**: Commands present in help output. Integration tests pass which exercise label operations.

### TC-29: wizard.py label creation uses new names for fresh setup
- **Result**: PASS
- **Notes**: wizard.py creates `type:issue` and `type:task` labels (verified via grep). No `type:bug` or `type:feature` in wizard.py label definitions.

### TC-30: git_ops.py unaffected
- **Result**: PASS
- **Notes**: `python references/scripts/git_ops.py pull` returns "Pulled (stashed and popped)" with exit code 0.

### TC-31: Existing iteration logs not rewritten
- **Result**: PASS
- **Notes**: `git diff HEAD -- .squidsquad/skill/iterations/ .squidsquad/dm/iterations/` shows no changes.

### TC-32: scan-history.md not rewritten
- **Result**: PASS
- **Notes**: `git diff HEAD -- .squidsquad/dm/scan-history.md` shows no changes.

### TC-33: Label rename propagates to all existing issues
- **Result**: PASS
- **Notes**: GitHub in-place label rename propagated correctly. `list-issues` and `list-tasks` return existing issues with new label names.

### TC-34: Recomposition after upgrade produces valid agent files
- **Result**: FAIL
- **Notes**: PM and skill CLAUDE.md are clean. DM CLAUDE.md contains residual old vocabulary from un-renamed `bug-triage` sub-skill: `bug-triage`, `list-bugs`, `create-bug`, `type:bug`/`type:feature`. See TC-7 and TC-22 details.

### TC-35: Non-upgraded install graceful degradation
- **Result**: PASS
- **Notes**: Old `create-bug` and `list-bugs` commands work as aliases with exit code 0, returning correct new-label results. Non-upgraded agents degrade gracefully.

### TC-36: Default GitHub "bug" label removed
- **Result**: FAIL
- **Notes**: The bare `bug` label still exists on the repo. Only `type:issue` should be used for issue classification.

---

## Smoke Tests

- [x] `create-issue` exits 0 and returns JSON (verified via alias)
- [x] `create-task` exits 0 (help confirms command)
- [x] `list-issues skill` exits 0
- [x] `list-tasks skill` exits 0
- [x] `grep -r "type:bug" references/scripts/` returns 0 matches
- [x] `grep -r "type:feature" references/scripts/` returns 0 matches
- [ ] `grep -r "create-bug" references/sub-skills/` -- **FAIL**: 1 match in `dm-specific/bug-triage.md`
- [x] `grep -r "create-feature" references/sub-skills/` returns 0 matches
- [ ] `grep -r "list-bugs" references/sub-skills/` -- **FAIL**: 1 match in `dm-specific/bug-triage.md`
- [ ] `grep -r "list-features" references/sub-skills/` -- **FAIL**: 1 match in `designer-specific/file-conventions.md`
- [x] `grep -r "bug-filing" references/roles/` returns 0 matches
- [x] `grep -r "feature-intake" references/roles/` returns 0 matches
- [x] `python -m pytest tests/ -x` exits 0 (518 passed)
- [ ] `grep "/squidsquad-bug" SKILL.md` -- **FAIL**: 2 matches (lines 383, 385)
- [ ] `grep "/squidsquad-issue" SKILL.md` -- **FAIL**: 0 matches (command not renamed)
- [ ] `.squidsquad/statusline.sh` -- **FAIL**: uses old label names

---

## Additional Residual Old Vocabulary Found

Files NOT covered by specific test cases but containing stale vocabulary:

| File | Old Vocabulary | Expected |
|------|---------------|----------|
| `references/agent-instructions.md:507-510` | `type:bug`, `type:feature`, `Bug`, `Feature` | `type:issue`, `type:task`, `Issue`, `Task` |
| `references/sub-skills/dm-specific/file-conventions.md:5` | `type:bug`/`type:feature` | `type:issue`/`type:task` |
| `references/sub-skills/designer-specific/file-conventions.md:6` | `type:bug`/`type:feature` | `type:issue`/`type:task` |
| `references/sub-skills/designer-specific/design-session.md:8` | `type:feature` | `type:task` |
| `references/sub-skills/designer-specific/file-conventions.md:7` | `list-features` | `list-tasks` |

---

## Summary Table

| TC | Title | Result |
|----|-------|--------|
| TC-1 | create-issue command works | PASS |
| TC-2 | create-task command works | PASS |
| TC-3 | list-issues command works | PASS |
| TC-4 | list-tasks command works | PASS |
| TC-5 | list-all-open returns both types | PASS |
| TC-6 | transition works with new labels | PASS |
| TC-7 | compose.py produces correct CLAUDE.md | **FAIL** |
| TC-8 | GitHub labels renamed | PASS |
| TC-9 | Open issue titles renamed | PASS |
| TC-10 | statusline.sh uses new labels | **FAIL** |
| TC-11 | Full test suite passes | PASS |
| TC-12 | /squidsquad-issue command | **FAIL** |
| TC-13 | Old create-bug alias | PASS |
| TC-14 | Old list-bugs/list-features alias | PASS |
| TC-15 | Generic English in manifest.py | PASS |
| TC-16 | Generic English in test_git_ops.py | PASS |
| TC-17 | CHANGELOG untouched | PASS |
| TC-18 | Closed issue titles untouched | PASS |
| TC-19 | Planning artifacts keep FEAT- prefix | PASS |
| TC-20 | Severity label description updated | **FAIL** |
| TC-21 | diagnostics.py Issue Report | **FAIL** |
| TC-22 | Sub-skill file renames complete | **FAIL** |
| TC-23 | Include directives updated | **FAIL** |
| TC-24 | cycle.py CLI flags updated | **FAIL** |
| TC-25 | GitHub Issue templates updated | **FAIL** |
| TC-26 | check-gh still works | PASS |
| TC-27 | comment command unchanged | PASS |
| TC-28 | get-labels / get-state still work | PASS |
| TC-29 | wizard.py label creation | PASS |
| TC-30 | git_ops.py unaffected | PASS |
| TC-31 | Iteration logs not rewritten | PASS |
| TC-32 | scan-history.md not rewritten | PASS |
| TC-33 | Label rename propagates | PASS |
| TC-34 | Recomposition valid | **FAIL** |
| TC-35 | Graceful degradation | PASS |
| TC-36 | Default bug label removed | **FAIL** |

**Total**: 36 test cases | **PASS: 25** | **FAIL: 11**

---

## Overall Verdict: FAIL

The rename is partially complete. Core tracker.py commands, GitHub labels, and main agent templates (PM, skill) are correctly updated. However, 11 test cases fail due to missed files and residual old vocabulary.

### Critical Failures (will cause silent wrong behavior)

1. **statusline.sh** (TC-10): Queries `type:bug`/`type:feature` labels that no longer exist. Status bar will show 0 for all issue/task counts.
2. **DM agent template** (TC-7, TC-34): DM CLAUDE.md has old `bug-triage`, `list-bugs`, `create-bug`, `type:bug`/`type:feature` references due to un-renamed `bug-triage.md` sub-skill.
3. **GitHub Issue templates** (TC-22, TC-25): Still reference `type:bug`/`type:feature` labels. New issues filed via GitHub UI will get non-existent labels.
4. **agent-instructions.md**: Still references `type:bug`/`type:feature` in improvement scanning section.

### Moderate Failures (cosmetic or less-used paths)

5. **SKILL.md** (TC-12): `/squidsquad-bug` not renamed to `/squidsquad-issue`.
6. **cycle.py** (TC-24): `--bugs`/`--features` CLI flags and template strings not updated.
7. **wizard.py** (TC-20): "Bug severity" description not updated.
8. **diagnostics.py** (TC-21): "Bug Report" heading not updated.
9. **designer sub-skills** (file-conventions.md, design-session.md): Old vocabulary.
10. **Bare `bug` label** (TC-36): Default GitHub label not removed.

### Files Requiring Attention

| File | Action |
|------|--------|
| `.squidsquad/statusline.sh` | Replace `type:bug` with `type:issue`, `type:feature` with `type:task` |
| `references/sub-skills/dm-specific/bug-triage.md` | Rename to `issue-triage.md`, update contents |
| `references/roles/dm/CLAUDE.md` | Update include: `bug-triage` to `issue-triage` |
| `.github/ISSUE_TEMPLATE/bug-report.yml` | Rename to `issue-report.yml`, update labels |
| `.github/ISSUE_TEMPLATE/feature-request.yml` | Rename to `task-request.yml`, update labels |
| `references/agent-instructions.md` | Update `type:bug`/`type:feature` in improvement scanning section |
| `references/sub-skills/dm-specific/file-conventions.md` | Update `type:bug`/`type:feature` |
| `references/sub-skills/designer-specific/file-conventions.md` | Update `type:bug`/`type:feature`, `list-features` |
| `references/sub-skills/designer-specific/design-session.md` | Update `type:feature` to `type:task` |
| `references/scripts/cycle.py` | Rename `--bugs`/`--features` to `--issues`/`--tasks`, update templates |
| `references/scripts/wizard.py` | Update "Bug severity" to "Issue severity" |
| `references/scripts/diagnostics.py` | Update "Bug Report" to "Issue Report" |
| `SKILL.md` | Rename `/squidsquad-bug` to `/squidsquad-issue` |
| GitHub repo | Remove bare `bug` label |
