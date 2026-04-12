# FEAT-SKILL-442 Test Plan — Rename feature/bug to task/issue

## Test Cases

### TC-1: tracker.py create-issue command works
- **Precondition**: GitHub CLI authenticated, repo has `type:issue` label
- **Steps**: Run `python references/scripts/tracker.py create-issue --title "Test issue" --body "desc" --role skill --severity low --reporter pm-lead`
- **Expected**: Issue created with `ISSUE:` title prefix, labels `type:issue`, `severity:low`, `role:skill`, `squidsquad`, `status:open`. Returns JSON with `number` and `url`.
- **Verification**: `gh issue view <NUMBER> --json title,labels` — title starts with `ISSUE:`, labels include `type:issue`

### TC-2: tracker.py create-task command works
- **Precondition**: GitHub CLI authenticated, repo has `type:task` label
- **Steps**: Run `python references/scripts/tracker.py create-task --title "Test task" --body "desc" --role skill --priority medium --reporter pm-lead`
- **Expected**: Issue created with `TASK:` title prefix, labels `type:task`, `priority:medium`, `role:skill`, `squidsquad`, `status:pending`. Returns JSON with `number` and `url`.
- **Verification**: `gh issue view <NUMBER> --json title,labels` — title starts with `TASK:`, labels include `type:task`

### TC-3: tracker.py list-issues command works
- **Precondition**: At least one open issue with `type:issue` and `role:skill` labels exists
- **Steps**: Run `python references/scripts/tracker.py list-issues skill`
- **Expected**: Returns list of issues with `type:issue` label filtered by role. Output includes issue numbers and titles.
- **Verification**: Compare output against `gh issue list --label "type:issue" --label "role:skill" --state open`

### TC-4: tracker.py list-tasks command works
- **Precondition**: At least one issue with `type:task` and `role:skill` labels exists
- **Steps**: Run `python references/scripts/tracker.py list-tasks skill --status approved`
- **Expected**: Returns list of issues with `type:task` label, filtered by role and status.
- **Verification**: Compare output against `gh issue list --label "type:task" --label "role:skill" --label "status:approved" --state open`

### TC-5: tracker.py list-all-open returns both types
- **Precondition**: At least one open issue and one open task exist
- **Steps**: Run `python references/scripts/tracker.py list-all-open`
- **Expected**: Returns all open issues regardless of type. Both `type:issue` and `type:task` items appear.
- **Verification**: Manually verify output includes items of both types

### TC-6: tracker.py transition works with new labels
- **Precondition**: An open issue (type:issue) exists at status `open`
- **Steps**: Run `python references/scripts/tracker.py transition <NUMBER> open in-progress --role skill-lead`
- **Expected**: Status label changes from `status:open` to `status:in-progress`. No errors.
- **Verification**: `python references/scripts/tracker.py get-labels <NUMBER>` — includes `status:in-progress` and `type:issue`

### TC-7: compose.py produces correct CLAUDE.md with renamed sub-skills
- **Precondition**: All sub-skill files renamed (issue-filing.md, task-intake.md, task-approval.md, issue-triage.md). All `{{include:}}` directives updated in role template files.
- **Steps**: Run `python references/scripts/compose.py` (or equivalent composition command)
- **Expected**: Composed CLAUDE.md files generated without errors. No "file not found" warnings. Output contains `create-issue`, `create-task`, `list-issues`, `list-tasks`, `type:issue`, `type:task` — not the old names.
- **Verification**: `grep -c "create-bug" .squidsquad/skill/CLAUDE.md` returns 0. `grep -c "create-issue" .squidsquad/skill/CLAUDE.md` returns > 0. Same checks for `.squidsquad/pm/CLAUDE.md` and `.squidsquad/dm/CLAUDE.md`.

### TC-8: GitHub labels renamed on repo
- **Precondition**: Repo currently has `type:bug` and `type:feature` labels
- **Steps**: Run `gh label edit "type:bug" --name "type:issue"` and `gh label edit "type:feature" --name "type:task"`
- **Expected**: Labels renamed in-place. All existing issues that had `type:bug` now have `type:issue`. All that had `type:feature` now have `type:task`.
- **Verification**: `gh label list --search "type:"` — shows `type:issue` and `type:task`, does NOT show `type:bug` or `type:feature`. `gh issue list --label "type:issue" --state all --limit 1` returns results.

### TC-9: Open issue titles renamed (FEAT: to TASK:, BUG: to ISSUE:)
- **Precondition**: Open issues exist with `FEAT:` and `BUG:` title prefixes
- **Steps**: Run title rename script/commands for all open issues (e.g., `gh issue edit <N> --title "TASK: ..."` for each open FEAT: issue, `gh issue edit <N> --title "ISSUE: ..."` for each open BUG: issue)
- **Expected**: All open issues have new prefixes. Closed issues are untouched.
- **Verification**: `gh issue list --state open --search "FEAT:" --limit 100` returns 0 results. `gh issue list --state open --search "BUG:" --limit 100` returns 0 results. `gh issue list --state open --search "TASK:" --limit 100` returns > 0. `gh issue list --state open --search "ISSUE:" --limit 100` returns > 0.

### TC-10: statusline.sh uses new label names
- **Precondition**: statusline.sh updated with `type:issue` and `type:task`
- **Steps**: Run `.squidsquad/statusline.sh` (or source it)
- **Expected**: Status line queries return correct counts using new labels. No zero-result queries caused by stale label names.
- **Verification**: `grep "type:bug" .squidsquad/statusline.sh` returns 0 matches. `grep "type:issue" .squidsquad/statusline.sh` returns > 0 matches. `grep "type:feature" .squidsquad/statusline.sh` returns 0 matches. `grep "type:task" .squidsquad/statusline.sh` returns > 0 matches.

### TC-11: Full test suite passes
- **Precondition**: All code and test file renames complete
- **Steps**: Run `python -m pytest tests/`
- **Expected**: All tests pass. Zero failures related to old label names.
- **Verification**: Exit code 0. No assertion errors mentioning `type:bug` or `type:feature`.

### TC-12: /squidsquad-issue command works (renamed from /squidsquad-bug)
- **Precondition**: SKILL.md updated with `/squidsquad-issue` command definition
- **Steps**: Invoke `/squidsquad-issue` in a Claude Code session (or verify the command definition in SKILL.md)
- **Expected**: Command files an issue to the upstream SquidSquad repo with `[Issue]:` prefix (or equivalent updated template). The old `/squidsquad-bug` name no longer appears in SKILL.md.
- **Verification**: `grep "/squidsquad-bug" SKILL.md` returns 0. `grep "/squidsquad-issue" SKILL.md` returns > 0.

---

## Edge Case Test Cases

### TC-13: Old commands create-bug / create-feature no longer work (or alias gracefully)
- **Precondition**: tracker.py updated, old function names removed or aliased
- **Steps**: Run `python references/scripts/tracker.py create-bug --title "test" --body "test" --role skill --severity low --reporter pm-lead`
- **Expected**: Either (a) command fails with a clear error message directing user to `create-issue`, or (b) command works as alias and creates the issue correctly with new labels. Dev discretion per CONTEXT.md.
- **Verification**: Check exit code. If aliased, verify labels are `type:issue` (not `type:bug`). If rejected, verify error message mentions `create-issue`.

### TC-14: Old commands list-bugs / list-features no longer work (or alias gracefully)
- **Precondition**: tracker.py updated
- **Steps**: Run `python references/scripts/tracker.py list-bugs skill` and `python references/scripts/tracker.py list-features skill`
- **Expected**: Same as TC-13 — either clear error or alias behavior.
- **Verification**: Check exit code and output labels.

### TC-15: Generic English "feature" and "bug" NOT renamed in manifest.py
- **Precondition**: manifest.py contains generic English uses of "bug" (e.g., "walker bug, not a manifest bug")
- **Steps**: Read manifest.py
- **Expected**: Generic English usage preserved exactly. No instances of "walker issue" or "manifest issue".
- **Verification**: `grep "walker bug" references/scripts/manifest.py` returns the original line. `grep "walker issue" references/scripts/manifest.py` returns 0.

### TC-16: Generic English "feature/test" branch NOT renamed in test_git_ops.py
- **Precondition**: test_git_ops.py uses `"feature/test"` as a git branch convention
- **Steps**: Read test_git_ops.py
- **Expected**: `"feature/test"` is preserved (generic git convention, not SquidSquad vocabulary).
- **Verification**: `grep "feature/test" tests/test_git_ops.py` returns the original reference.

### TC-17: Historical CHANGELOG entries untouched
- **Precondition**: CHANGELOG.md has historical entries referencing "bug", "feature", "FEAT:", "BUG:"
- **Steps**: Read CHANGELOG.md entries prior to the #442 change
- **Expected**: All historical entries preserved verbatim. No vocabulary replacement in past entries.
- **Verification**: `git diff HEAD -- CHANGELOG.md` shows changes only in the Unreleased section (if any), not in dated historical sections.

### TC-18: Closed GitHub Issue titles untouched
- **Precondition**: Closed issues exist with `FEAT:` and `BUG:` title prefixes
- **Steps**: Query closed issues
- **Expected**: Closed issues retain original `FEAT:` / `BUG:` title prefixes.
- **Verification**: `gh issue list --state closed --search "FEAT:" --limit 5` returns results (closed FEAT: issues still exist). `gh issue list --state closed --search "BUG:" --limit 5` returns results.

### TC-19: Planning artifacts keep FEAT- prefix in filenames
- **Precondition**: Files like `FEAT-SKILL-442-RESEARCH.md` exist in planning directories
- **Steps**: Check that existing planning artifacts were NOT renamed
- **Expected**: `FEAT-SKILL-442-RESEARCH.md`, `FEAT-SKILL-442-CONTEXT.md`, and this test plan all retain their `FEAT-` prefixed filenames.
- **Verification**: `ls .squidsquad/pm/planning/FEAT-SKILL-442-*` returns the existing files.

### TC-20: Severity label description updated
- **Precondition**: wizard.py previously described severity as "Bug severity"
- **Steps**: Read wizard.py severity label description
- **Expected**: Description reads "Issue severity" (not "Bug severity"). The `severity:high/medium/low` label names themselves are unchanged.
- **Verification**: `grep "Bug severity" references/scripts/wizard.py` returns 0. `grep "Issue severity" references/scripts/wizard.py` returns > 0. `grep "severity:high" references/scripts/wizard.py` returns > 0 (label name preserved).

### TC-21: diagnostics.py uses "Issue Report" (not "Bug Report")
- **Precondition**: diagnostics.py updated
- **Steps**: Read diagnostics.py template section
- **Expected**: Template heading reads "Issue Report" instead of "Bug Report".
- **Verification**: `grep "Bug Report" references/scripts/diagnostics.py` returns 0. `grep "Issue Report" references/scripts/diagnostics.py` returns > 0.

### TC-22: Sub-skill file renames complete — old files do not exist
- **Precondition**: All 10 file renames executed
- **Steps**: Check for existence of old filenames
- **Expected**: None of the old filenames exist. All new filenames exist.
- **Verification**:
  - `ls references/sub-skills/common/bug-filing.md` — file not found
  - `ls references/sub-skills/common/issue-filing.md` — exists
  - `ls references/sub-skills/pm-specific/bug-filing.md` — file not found
  - `ls references/sub-skills/pm-specific/issue-filing.md` — exists
  - `ls references/sub-skills/pm-specific/feature-intake.md` — file not found
  - `ls references/sub-skills/pm-specific/task-intake.md` — exists
  - `ls references/sub-skills/pm-specific/feature-approval.md` — file not found
  - `ls references/sub-skills/pm-specific/task-approval.md` — exists
  - `ls references/sub-skills/qa-specific/bug-filing.md` — file not found
  - `ls references/sub-skills/qa-specific/issue-filing.md` — exists
  - `ls references/sub-skills/dm-specific/bug-filing.md` — file not found
  - `ls references/sub-skills/dm-specific/issue-filing.md` — exists
  - `ls references/sub-skills/dm-specific/bug-triage.md` — file not found
  - `ls references/sub-skills/dm-specific/issue-triage.md` — exists
  - `ls references/sub-skills/designer-specific/bug-filing.md` — file not found
  - `ls references/sub-skills/designer-specific/issue-filing.md` — exists
  - `ls .github/ISSUE_TEMPLATE/bug-report.yml` — file not found
  - `ls .github/ISSUE_TEMPLATE/issue-report.yml` — exists
  - `ls .github/ISSUE_TEMPLATE/feature-request.yml` — file not found
  - `ls .github/ISSUE_TEMPLATE/task-request.yml` — exists

### TC-23: Include directives updated to match new filenames
- **Precondition**: Role CLAUDE.md template files updated
- **Steps**: Search all role CLAUDE.md templates for old include paths
- **Expected**: Zero references to old filenames in include directives.
- **Verification**:
  - `grep -r "include.*bug-filing" references/roles/` returns 0
  - `grep -r "include.*issue-filing" references/roles/` returns > 0
  - `grep -r "include.*feature-intake" references/roles/` returns 0
  - `grep -r "include.*task-intake" references/roles/` returns > 0
  - `grep -r "include.*feature-approval" references/roles/` returns 0
  - `grep -r "include.*task-approval" references/roles/` returns > 0
  - `grep -r "include.*bug-triage" references/roles/` returns 0
  - `grep -r "include.*issue-triage" references/roles/` returns > 0

### TC-24: cycle.py CLI flags and template strings updated
- **Precondition**: cycle.py updated
- **Steps**: Read cycle.py for `--bugs`, `--features`, `Bugs Fixed`, `Features Progressed`
- **Expected**: CLI flags renamed to `--issues`/`--tasks`. Template strings renamed to `Issues Fixed`/`Tasks Progressed` (or equivalent).
- **Verification**: `grep "\-\-bugs" references/scripts/cycle.py` returns 0. `grep "\-\-issues" references/scripts/cycle.py` returns > 0. `grep "Bugs Fixed" references/scripts/cycle.py` returns 0. `grep "Features Progressed" references/scripts/cycle.py` returns 0.

### TC-25: GitHub Issue templates updated
- **Precondition**: `.github/ISSUE_TEMPLATE/issue-report.yml` and `task-request.yml` exist
- **Steps**: Read the renamed template files
- **Expected**: `issue-report.yml` uses `[Issue]:` title prefix, `type:issue` label. `task-request.yml` uses `[Task]:` title prefix, `type:task` label.
- **Verification**: `grep "type:bug" .github/ISSUE_TEMPLATE/` returns 0 across all files. `grep "type:feature" .github/ISSUE_TEMPLATE/` returns 0. `grep "type:issue" .github/ISSUE_TEMPLATE/issue-report.yml` returns > 0. `grep "type:task" .github/ISSUE_TEMPLATE/task-request.yml` returns > 0.

---

## Side Effect Regression Tests

### TC-26: tracker.py check-gh still works
- **Precondition**: gh CLI authenticated
- **Steps**: Run `python references/scripts/tracker.py check-gh`
- **Expected**: Exit code 0. No regression from the rename.
- **Verification**: Exit code check.

### TC-27: tracker.py comment command unchanged
- **Precondition**: An open issue exists
- **Steps**: Run `python references/scripts/tracker.py comment <NUMBER> --role pm-lead --message "Test comment"`
- **Expected**: Comment appended successfully. Comment command is unaffected by the rename.
- **Verification**: `gh issue view <NUMBER> --json comments` — last comment contains "Test comment"

### TC-28: tracker.py get-labels / get-state still work
- **Precondition**: An issue exists with labels
- **Steps**: Run `python references/scripts/tracker.py get-labels <NUMBER>` and `python references/scripts/tracker.py get-state <NUMBER>`
- **Expected**: Returns correct labels and state. No regression.
- **Verification**: Output matches expected labels.

### TC-29: wizard.py label creation uses new names for fresh setup
- **Precondition**: Clean repo without SquidSquad labels
- **Steps**: Run wizard.py setup flow (or inspect label creation code)
- **Expected**: Creates `type:issue` and `type:task` labels (not `type:bug`/`type:feature`).
- **Verification**: `grep "type:bug" references/scripts/wizard.py` returns 0. `grep "type:issue" references/scripts/wizard.py` returns > 0. `grep "type:task" references/scripts/wizard.py` returns > 0.

### TC-30: git_ops.py unaffected
- **Precondition**: git_ops.py has no SquidSquad-specific bug/feature vocabulary
- **Steps**: Run `python references/scripts/git_ops.py pull`
- **Expected**: Works as before. No regression.
- **Verification**: Exit code 0.

### TC-31: Existing iteration logs not rewritten
- **Precondition**: Historical iteration logs exist in `.squidsquad/*/iterations/`
- **Steps**: Check that existing iter-*.md files were not modified
- **Expected**: Files retain original "Bugs Fixed" / "Features Progressed" headings.
- **Verification**: `git diff HEAD -- .squidsquad/skill/iterations/` shows no changes. `git diff HEAD -- .squidsquad/dm/iterations/` shows no changes.

### TC-32: scan-history.md not rewritten
- **Precondition**: `.squidsquad/dm/scan-history.md` contains historical references
- **Steps**: Check file was not modified
- **Expected**: Historical scan entries preserved verbatim.
- **Verification**: `git diff HEAD -- .squidsquad/dm/scan-history.md` shows no changes.

---

## Upgrade Verification Tests

### TC-33: Label rename propagates to all existing issues
- **Precondition**: Repo has issues labeled `type:bug` and `type:feature`
- **Steps**: Run `gh label edit "type:bug" --name "type:issue"` and `gh label edit "type:feature" --name "type:task"`
- **Expected**: GitHub's in-place label rename automatically propagates. All issues that had `type:bug` now show `type:issue`. No manual per-issue relabeling needed.
- **Verification**: `gh issue list --label "type:issue" --state all --limit 200 --json number | jq length` should match the count previously returned by `gh issue list --label "type:bug" --state all`

### TC-34: Recomposition after upgrade produces valid agent files
- **Precondition**: Reference files updated, sub-skills renamed
- **Steps**: Run composition (compose.py or equivalent). Compare composed output to expected content.
- **Expected**: Composed CLAUDE.md files contain only new vocabulary. No stale `bug-filing`, `feature-intake`, `create-bug`, `type:bug` references.
- **Verification**: `grep -r "type:bug\|type:feature\|create-bug\|create-feature\|list-bugs\|list-features\|bug-filing\|feature-intake\|feature-approval\|bug-triage" .squidsquad/skill/CLAUDE.md .squidsquad/pm/CLAUDE.md .squidsquad/dm/CLAUDE.md` returns 0 matches (excluding any generic English or historical references embedded in templates).

### TC-35: Non-upgraded install graceful degradation
- **Precondition**: A clone running old agent templates (pre-#442) against a repo where labels have been renamed
- **Steps**: Old agent runs `python references/scripts/tracker.py list-bugs skill` (old command referencing `type:bug`)
- **Expected**: Graceful degradation — returns empty results (no matching issues) rather than crashing. Agent idles rather than errors out.
- **Verification**: Exit code 0, empty result set, no stack trace.

### TC-36: Default GitHub "bug" label removed
- **Precondition**: Repo has the default `bug` label from GitHub
- **Steps**: Remove or verify removal of the bare `bug` label
- **Expected**: Only `type:issue` exists for issue classification. No bare `bug` label.
- **Verification**: `gh label list --search "bug"` — does NOT return a bare `bug` label (may return `type:issue` if search is substring-based, which is fine).

---

## Smoke Tests

- [ ] `python references/scripts/tracker.py create-issue --title "Smoke" --body "test" --role skill --severity low --reporter pm-lead` exits 0 and returns JSON
- [ ] `python references/scripts/tracker.py create-task --title "Smoke" --body "test" --role skill --priority low --reporter pm-lead` exits 0 and returns JSON
- [ ] `python references/scripts/tracker.py list-issues skill` exits 0
- [ ] `python references/scripts/tracker.py list-tasks skill` exits 0
- [ ] `grep -r "type:bug" references/scripts/` returns 0 matches
- [ ] `grep -r "type:feature" references/scripts/` returns 0 matches
- [ ] `grep -r "create-bug" references/sub-skills/` returns 0 matches
- [ ] `grep -r "create-feature" references/sub-skills/` returns 0 matches
- [ ] `grep -r "list-bugs" references/sub-skills/` returns 0 matches
- [ ] `grep -r "list-features" references/sub-skills/` returns 0 matches
- [ ] `grep -r "bug-filing" references/roles/` returns 0 matches (in include directives)
- [ ] `grep -r "feature-intake" references/roles/` returns 0 matches (in include directives)
- [ ] `python -m pytest tests/ -x` exits 0
- [ ] `grep "/squidsquad-bug" SKILL.md` returns 0 matches
- [ ] `grep "/squidsquad-issue" SKILL.md` returns > 0 matches
- [ ] `.squidsquad/statusline.sh` runs without error (if on a unix-like system)

## Regression Risks

- **Stale label queries returning empty results**: If statusline.sh, any agent template, or any script still references `type:bug`/`type:feature` after rename, queries will silently return zero results rather than erroring. This is the highest-risk silent failure mode. Mitigation: exhaustive grep of the entire codebase for old vocabulary after implementation.
- **Broken include directives**: If any `{{include:}}` path references an old filename (e.g., `bug-filing` instead of `issue-filing`), compose.py will fail loudly. This is a safety net but could block agent recomposition. Mitigation: update all includes before running compose.
- **Test file label assertions**: test_labels.py, test_wizard.py, test_status_flow.py all assert specific label values. If any test still expects `type:bug`/`type:feature`, the test suite will fail. Mitigation: update all test assertions as part of the rename.
- **Mid-cycle agent breakage**: If labels are renamed on GitHub while agents are running, queries will return stale results. Mitigation: stop all agents before deploying (per CONTEXT.md requirement).
- **External-facing /squidsquad-issue unfamiliarity**: Users who memorized `/squidsquad-bug` will not find it. Mitigation: mention rename in CHANGELOG and CONTRIBUTING.md.
- **Partial rename across 60+ files**: Missing a single file leaves an inconsistency that may not manifest until that code path runs. Mitigation: post-rename full-codebase grep for `type:bug`, `type:feature`, `create-bug`, `create-feature`, `list-bugs`, `list-features`, `bug-filing`, `feature-intake`, `feature-approval`, `bug-triage`, `/squidsquad-bug` — excluding CHANGELOG.md, closed planning artifacts, and files explicitly marked as generic English.
- **GitHub Issue template file renames**: If GitHub caches old template filenames, the issue creation form may not update immediately. Mitigation: verify by visiting the "New Issue" page after deployment.
- **cycle.py iteration log format change**: New iteration logs will use `Issues Fixed` / `Tasks Progressed` while historical logs use the old format. Any tooling that parses iteration logs must handle both. Mitigation: grep for hardcoded parsing of the old headings.
