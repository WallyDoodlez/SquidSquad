# FEAT-SKILL-442 Research: Rename feature/bug to task/issue

## Summary

Pure vocabulary rename across the entire SquidSquad codebase:
- `feature` -> `task` (in SquidSquad-specific context)
- `bug` -> `issue` (in SquidSquad-specific context)
- Labels: `type:feature` -> `type:task`, `type:bug` -> `type:issue`
- Commands: `create-bug` -> `create-issue`, `create-feature` -> `create-task`, `list-bugs` -> `list-issues`, `list-features` -> `list-tasks`
- Title prefixes: `FEAT:` -> `TASK:`, `BUG:` -> `ISSUE:`
- Branch convention: `squidsquad/feat-` -> `squidsquad/task-`, `squidsquad/bug-` -> `squidsquad/issue-`

This is a large-surface-area rename touching ~60+ files with ~500+ individual references. No lifecycle or architecture changes.

## Impact Analysis

### 1. Scripts (`references/scripts/`)

| File | Refs | Type | Notes |
|------|------|------|-------|
| `tracker.py` | ~30 | Code (variable names, function names, CLI commands, string literals) | **Heaviest code file.** `TYPE_LABELS` dict, `create_bug()`, `create_feature()`, `list-bugs`, `list-features`, `create-bug`, `create-feature` CLI commands, `BUG:`/`FEAT:` prefix logic, `type:bug`/`type:feature` label strings. `list_issues()` function already exists (generic) but `issue_type="bug"` default param needs rename. |
| `wizard.py` | ~4 | Code (label colors, label descriptions) | `type:bug`/`type:feature` in label color map and description map. `"severity"` label description says "Bug severity". |
| `cycle.py` | ~8 | Code (CLI params, template strings) | `--bugs`/`--features` CLI flags, `log_iteration()` params `bugs`/`features`, iteration template `**Bugs Fixed**`/`**Features Progressed**`. |
| `diagnostics.py` | ~6 | Prose + code | "Bug Report" template, `/squidsquad-bug` command reference. **TRICKY**: "bug report" here means upstream SquidSquad bug reporting, not the internal tracker concept. Consider whether this should stay as "bug report" (external-facing) or become "issue report". |
| `manifest.py` | 2 | Prose (comment) | Generic English usage: "walker bug, not a manifest bug" -- **DO NOT RENAME**, this is plain English. |

### 2. Sub-skills (`references/sub-skills/`)

| File | Refs | Type | Notes |
|------|------|------|-------|
| `common/bug-filing.md` | 3 | Code + prose | `create-bug` commands, "feature work" prose. **FILENAME RENAME**: `bug-filing.md` -> `issue-filing.md` |
| `common/file-conventions.md` | 2 | Prose + code | "bugs and features", `list-bugs/list-features` |
| `common/discussion-protocol.md` | 1 | Prose | "file the bug" |
| `common/git-commit.md` | 4 | Prose + code | "feature or bug fix", `FEAT/BUG-ID`, "feature/bug completion" |
| `common/improvement-scan.md` | 8 | Code + prose | "Bug gate", `list-bugs`, `create-bug`/`create-feature`, `type:bug`/`type:feature` labels, classification rules |
| `common/prohibitions.md` | 2 | Prose | "feature with status Pending", "bug Fixed or feature Pending Test" |
| `common/tracker-protocol.md` | 12 | Code + prose | `bug`/`feature` type definitions, `status:open` description, `list-features`/`list-bugs`/`create-bug`/`create-feature` commands, `BUG:`/`FEAT:` prefix docs |
| `common/working-state.md` | 1 | Prose | "bug fix or feature implementation" |
| `pm-specific/feature-intake.md` | ~25 | Prose + code | **FILENAME RENAME**: `feature-intake.md` -> `task-intake.md`. Heavy with "feature" throughout. `create-feature` command, "Feature Lifecycle", "feature spec", etc. |
| `pm-specific/feature-approval.md` | ~5 | Prose | **FILENAME RENAME**: `feature-approval.md` -> `task-approval.md`. "Feature Approval Gate", "approve a feature" |
| `pm-specific/bug-filing.md` | 1 | Prose | **FILENAME RENAME**: `bug-filing.md` -> `issue-filing.md`. "Bug Filing Protocol" heading |
| `pm-specific/delivery-fallback.md` | ~8 | Prose | "feature just marked Pending Ship", "feature's Discussion", "delivery:skip", "Mark Shipped", "bug trackers" |
| `pm-specific/github-issues.md` | 2 | Code + prose | "bug or feature request", `type:[bug|feature]` |
| `pm-specific/pr-flow.md` | 2 | Prose | "feature/bug ID from PR title" |
| `pm-specific/prohibitions.md` | 3 | Prose | "approve a feature", "file to bug or feature tracker" |
| `pm-specific/file-conventions.md` | 1 | Prose | `type:bug`/`type:feature` |
| `qa-specific/bug-filing.md` | 2 | Prose | **FILENAME RENAME**: `bug-filing.md` -> `issue-filing.md`. "Bug Filing Protocol", "file as bug" |
| `qa-specific/verification.md` | ~10 | Code + prose | `type:bug`, `create-bug`, `list-bugs`, `list-features`, "bug" vs "feature" verification flows |
| `qa-specific/prohibitions.md` | 1 | Prose | "mark a bug Verified" |
| `dm-specific/bug-filing.md` | 2 | Prose | **FILENAME RENAME**: `bug-filing.md` -> `issue-filing.md`. "Filing Bugs and Features" |
| `dm-specific/bug-triage.md` | ~8 | Code + prose | **FILENAME RENAME**: `bug-triage.md` -> `issue-triage.md`. `list-bugs`, `create-bug`, "bug details", "Fix the bug" |
| `dm-specific/delivery-packaging.md` | ~6 | Prose | "feature ID", "feature description", "feature's Discussion", "delivery: skip" |
| `dm-specific/file-conventions.md` | 2 | Prose | `type:bug`/`type:feature`, `features/`/`bugs/` directories |
| `dm-specific/version-bumps.md` | 1 | Prose | "bug trackers" |
| `designer-specific/bug-filing.md` | 0 | N/A | **FILENAME RENAME**: `bug-filing.md` -> `issue-filing.md`. (Content references checked via role-specific overlay) |
| `designer-specific/design-session.md` | ~10 | Code + prose | `type:feature`, "design-needed feature", "feature ID", "feature's acceptance criteria" |
| `designer-specific/file-conventions.md` | 2 | Code + prose | `type:bug`/`type:feature`, `list-features` |
| `manifest.md` | ~20 | Prose | Sub-skill names, file tree, changelog entries referencing "bug-filing", "feature-intake", "feature-approval" |

### 3. Role templates (`references/roles/`)

| File | Refs | Type | Notes |
|------|------|------|-------|
| `dev/CLAUDE.md` | ~25 | Code + prose | "list-bugs", "list-features", "create-bug", "Bug gate", "feature work", "Implement Features" step heading |
| `dev/SOUL.md` | ~5 | Prose | "implementing a feature", "Filed BUG-PM-012", "file a bug" |
| `dev/manifest.yaml` | 1 | Prose | "Implements features and fixes bugs" |
| `pm/CLAUDE.md` | ~35 | Code + prose | Heaviest role file. "list-bugs", "list-features", "feature intake", "Bug Discussion Flow", `feature-intake` sub-skill name in status examples |
| `pm/SOUL.md` | ~12 | Prose | "feature spec", "approve features", "file a bug", "Feature Intake Process" |
| `pm/manifest.yaml` | 0 | N/A | No direct references |
| `qa/CLAUDE.md` | ~5 | Code + prose | "verify features", "filing bugs", `bug-filing` include |
| `qa/SOUL.md` | ~8 | Prose | "approve features", "shipped features", "feature ships", "QA-rejected features" |
| `qa/manifest.yaml` | 2 | Prose | "feature's acceptance criteria", "future feature" (generic English, may keep) |
| `dm/CLAUDE.md` | ~8 | Code + prose | "features at Pending Ship", `bug-triage`/`bug-filing` includes |
| `dm/SOUL.md` | ~15 | Prose | "shipped feature", "feature perfectly but nobody knows", "user-facing features" |
| `dm/manifest.yaml` | 0 | N/A | |
| `designer/CLAUDE.md` | 3 | Prose | "file features", "approve features", `bug-filing` include |
| `designer/SOUL.md` | ~5 | Prose | "approve features", "features can be scoped", "existing features" |

### 4. Composed agent files (`.squidsquad/*/CLAUDE.md`)

| File | Refs | Type | Notes |
|------|------|------|-------|
| `.squidsquad/skill/CLAUDE.md` | ~60 | Code + prose | Composed dev agent. All tracker commands, type labels, step headings, prose. |
| `.squidsquad/dm/CLAUDE.md` | ~55 | Code + prose | Composed DM agent. Tracker commands, type labels, delivery flow, improvement scan. |
| `.squidsquad/pm/CLAUDE.md` | ~40+ | Code + prose | Composed PM agent. Tracker commands, verification flows, feature intake. |

**Note**: These are composed (generated) files. They will be regenerated after the reference files are updated, so they do not need manual editing -- the composition engine (`compose.py`) will rebuild them.

### 5. SOUL files (`.squidsquad/*/SOUL.md`)

| File | Refs | Type | Notes |
|------|------|------|-------|
| `.squidsquad/skill/SOUL.md` | ~4 | Prose | Same as `references/roles/dev/SOUL.md` |
| `.squidsquad/dm/SOUL.md` | ~15 | Prose | Same as `references/roles/dm/SOUL.md` |
| `.squidsquad/pm/SOUL.md` | ~12 | Prose | Same as `references/roles/pm/SOUL.md` |

**Note**: These are also composed/copied from references. Will be regenerated.

### 6. Config, SKILL.md, README, CHANGELOG, docs

| File | Refs | Type | Notes |
|------|------|------|-------|
| `SKILL.md` | ~40 | Prose + code | Label taxonomy, flows, feature lifecycle section, Ralph Loop descriptions, schema changelog, `/squidsquad-bug` command, status line commands. **TRICKY**: `/squidsquad-bug` slash command -- rename to `/squidsquad-issue`? |
| `README.md` | ~15 | Prose | "Key Features" section header (generic English -- keep), "bugs and features", "file bugs", "5-phase feature planning", mermaid diagram labels |
| `CHANGELOG.md` | ~25 | Prose | Historical entries. **TRICKY**: Should historical changelog entries be rewritten? Recommendation: NO -- they document what happened at the time. Only update the "Unreleased" section. |
| `CONTRIBUTING.md` | ~8 | Prose | "Reporting Bugs" section, "Proposing Features" section, `/squidsquad-bug` reference, issue template links |
| `docs/ARCHITECTURE.md` | ~20 | Prose + code | Mermaid diagrams, role descriptions, Ralph Loop summaries, label taxonomy table, `/squidsquad-bug` reference |
| `docs/sub-skill-guide.md` | ~3 | Prose | "bug-triage.md" example, "bug triage AND feature implementation" |
| `.squidsquad/config.md` | 0 | N/A | No references found |

### 7. Test files (`tests/`)

| File | Refs | Type | Notes |
|------|------|------|-------|
| `test_labels.py` | 2 | Code | `EXPECTED_TYPE_LABELS = {"type:bug", "type:feature"}` -- must update |
| `test_status_flow.py` | ~8 | Code + prose | `type:feature`/`type:bug` labels, "feature" in test names and docstrings |
| `test_harness.py` | 1 | Code | `type:bug` label in test issue creation |
| `test_tracker_authority.py` | ~5 | Code + prose | "DM bug triage", `test_dm_can_triage_own_bug` test names |
| `test_wizard.py` | 2 | Code | `type:bug`, `type:feature` in expected label sets |
| `test_git_ops.py` | 1 | Code | `"feature/test"` branch name -- generic git convention, **DO NOT RENAME** |

### 8. GitHub Issue templates (`.github/ISSUE_TEMPLATE/`)

| File | Refs | Type | Notes |
|------|------|------|-------|
| `bug-report.yml` | ~3 | Code + prose | **FILENAME RENAME**: `bug-report.yml` -> `issue-report.yml`. Title prefix `[Bug]:`, label `type:bug`, "report a bug" prose |
| `feature-request.yml` | ~3 | Code + prose | **FILENAME RENAME**: `feature-request.yml` -> `task-request.yml`. Title prefix `[Feature]:`, label `type:feature`, "suggest a feature" prose |

### 9. Other files

| File | Refs | Type | Notes |
|------|------|------|-------|
| `.squidsquad/statusline.sh` | ~16 | Code | `type:bug`, `type:feature` in `gh issue list` queries, `BUGS`/`FEATS` variable names, "Planning phase" feature comment |
| `.squidsquad/hints-dev.txt` | 2 | Prose | "file a bug or request a feature", "Checking bug tracker" |
| `.squidsquad/hints-dm.txt` | 1 | Prose | "drop a feature my way" |
| `.squidsquad/hints-pm.txt` | 5 | Prose | "feature or report a bug", "shipped features", "bug fixes", "feature intake" |
| `.squidsquad/hints-qa.txt` | 1 | Prose | "features to verify" |
| `.squidsquad/templates/dm-agent.md` | ~50 | Code + prose | Legacy template, mirrors composed DM. Has `BUG:` prefix, `type:bug`/`type:feature`, `features/INDEX.md` references |
| `references/agent-instructions.md` | ~50 | Code + prose | Base agent template with all tracker commands and type labels |
| `.squidsquad/skill/bugs/INDEX.md` | ~3 | Code | "Bug Index" heading, BUG-SKILL-XXX references |
| `.squidsquad/skill/features/INDEX.md` | varies | Code | FEAT-SKILL-XXX references |
| `.squidsquad/skill/bugs/*.md` | varies | Prose | Historical bug files (BUG-SKILL-039, 040, archived) |
| `.squidsquad/skill/features/*.md` | varies | Prose | Historical feature files (FEAT-SKILL-020, etc.) |
| `.squidsquad/dm/scan-history.md` | ~20 | Prose | Historical scan entries referencing bugs/features |
| `.squidsquad/dm/iterations/*.md` | ~30 | Prose | Historical: "Features Delivered", "open bug" |
| `.squidsquad/skill/iterations/*.md` | ~5 | Prose | Historical: "Bugs Fixed", "Features Progressed" |

### 10. GitHub Labels (repo-level)

| Current Label | New Label | Issues Affected |
|--------------|-----------|-----------------|
| `type:bug` | `type:issue` | 114 total (3 open, 111 closed) |
| `type:feature` | `type:task` | 56 total (31 open, 25 closed) |
| `bug` (GitHub default) | Remove or rename to `issue` | Unknown count |

### 11. GitHub Issue Titles

| Current Prefix | New Prefix | Count |
|---------------|------------|-------|
| `FEAT:` | `TASK:` | 38 issues |
| `BUG:` | `ISSUE:` | 110 issues |

## Sub-skill Filename Renames Required

These files must be renamed (not just content-edited):

| Current Path | New Path |
|-------------|----------|
| `references/sub-skills/common/bug-filing.md` | `references/sub-skills/common/issue-filing.md` |
| `references/sub-skills/pm-specific/bug-filing.md` | `references/sub-skills/pm-specific/issue-filing.md` |
| `references/sub-skills/qa-specific/bug-filing.md` | `references/sub-skills/qa-specific/issue-filing.md` |
| `references/sub-skills/dm-specific/bug-filing.md` | `references/sub-skills/dm-specific/issue-filing.md` |
| `references/sub-skills/designer-specific/bug-filing.md` | `references/sub-skills/designer-specific/issue-filing.md` |
| `references/sub-skills/dm-specific/bug-triage.md` | `references/sub-skills/dm-specific/issue-triage.md` |
| `references/sub-skills/pm-specific/feature-intake.md` | `references/sub-skills/pm-specific/task-intake.md` |
| `references/sub-skills/pm-specific/feature-approval.md` | `references/sub-skills/pm-specific/task-approval.md` |
| `.github/ISSUE_TEMPLATE/bug-report.yml` | `.github/ISSUE_TEMPLATE/issue-report.yml` |
| `.github/ISSUE_TEMPLATE/feature-request.yml` | `.github/ISSUE_TEMPLATE/task-request.yml` |

All `{{include:}}` directives in role CLAUDE.md files must be updated to match new filenames.

## Side Effects

### What could break?

1. **Existing GitHub Issues**: 170 issues (114 bug + 56 feature) have `type:bug` or `type:feature` labels. Label rename on GitHub will propagate to all existing issues automatically (GitHub label rename is in-place, not create+delete).

2. **Active agent sessions**: Any running agent reading labels will break mid-cycle if labels are renamed while agents are running. **Mitigation**: Stop all agents before deploying.

3. **Statusline script**: `.squidsquad/statusline.sh` hardcodes `type:bug` and `type:feature` in `gh issue list` queries. Will silently return 0 results if labels are renamed before script is updated.

4. **External consumers**: The `/squidsquad-bug` slash command files issues to the upstream repo with `[Bug]:` prefix. External users who have memorized this command will need to learn `/squidsquad-issue`. However, the old command could be kept as an alias during transition.

5. **Git branch naming**: `squidsquad/feat-*` and `squidsquad/bug-*` branches may exist. Existing branches are fine (they are ephemeral), but the convention in SKILL.md needs updating.

6. **Planning artifact filenames**: Files like `FEAT-SKILL-442-RESEARCH.md` use the `FEAT-` prefix. These are local planning files, not tracked in the label system. The naming convention in templates (`FEAT-[ROLE_UPPER]-XXX-*`) would become `TASK-[ROLE_UPPER]-XXX-*`. **Existing artifacts should NOT be renamed** -- they are historical.

7. **Iteration log templates**: `cycle.py` uses `--bugs`/`--features` CLI flags and generates `**Bugs Fixed**`/`**Features Progressed**` in iteration logs. All existing iteration logs have this format. **Existing logs should NOT be rewritten** -- they are historical.

## Edge Cases

### 1. Generic English usage -- DO NOT RENAME

These uses of "feature" and "bug" are plain English, not SquidSquad-specific vocabulary:

- `manifest.py` line 37: "walker bug, not a manifest bug" -- generic programming usage
- `README.md` "Key Features" section heading -- generic English
- `test_git_ops.py`: `"feature/test"` -- git branch naming convention
- `dm/SOUL.md`: "A feature that works perfectly but that no one knows about" -- this IS SquidSquad vocabulary in context, rename to "task"
- `qa/manifest.yaml`: "A future feature (#347)" -- this IS SquidSquad vocabulary, rename
- Various SOUL.md files: "feature" used in philosophical/behavioral context -- these ARE SquidSquad vocabulary, rename

### 2. Sub-skill name `feature-intake`

The sub-skill name appears in:
- Status line phase strings: `planning|feature-intake`, `researching|feature-intake`
- File names: `feature-intake.md`
- `{{include: pm-specific/feature-intake}}`
- Manifest.md listings

All must be renamed to `task-intake`.

### 3. Sub-skill name `bug-filing`

Appears in every role's CLAUDE.md as `{{include: **/bug-filing}}` and in manifest.md. All must be renamed to `issue-filing`.

### 4. Planning artifact naming convention (`FEAT-SKILL-XXX`)

The convention `FEAT-[ROLE]-XXX` appears in templates and is used to name planning files. This becomes `TASK-[ROLE]-XXX`. Existing files (e.g., `FEAT-SKILL-442-RESEARCH.md` -- this very file) should NOT be renamed. Only the template/convention documentation changes.

### 5. The `severity` label

Currently `severity:high/medium/low` is described as "Bug severity" in wizard.py. Under the new vocabulary, it becomes "Issue severity". The severity labels themselves do not need renaming, just the description.

### 6. `/squidsquad-bug` command

This slash command in SKILL.md is for reporting bugs to the **upstream** SquidSquad repo. Options:
- **Option A**: Rename to `/squidsquad-issue` (consistent with new vocabulary)
- **Option B**: Keep as `/squidsquad-bug` (it is about reporting bugs to a GitHub repo, not about internal tracking)
- **Recommendation**: Rename to `/squidsquad-issue` for consistency. The command body and GitHub Issue template also need updating.

### 7. `diagnostics.py` "Bug Report"

The `diagnostics.py` generates a "Bug Report" template for upstream reporting. This should probably become "Issue Report" for consistency, but it is a self-contained external-facing feature.

### 8. Historical data (CHANGELOG, iterations, scan-history, archived bugs/features)

Historical records should NOT be rewritten. They document what happened using the vocabulary of the time. Only forward-looking documentation and templates change.

## Integration Risks

### Overlap with #401 (Capability sub-skills -- replace tool concept)

**#401 status**: `status:approved`, `role:skill` -- approved but not yet started by dev.

**Overlap analysis**: #401 renames "tools" to "capabilities" in sub-skills. #442 renames "feature/bug" to "task/issue" in the same files. The overlap is in:
- Sub-skill files (both rename different words in the same files)
- Role CLAUDE.md templates (both touch the same sections)
- `references/agent-instructions.md` (both modify this file)
- SKILL.md (both modify this file)

**Recommendation**: #442 should land BEFORE #401. Rationale:
1. #442 is a pure vocabulary rename with no structural changes -- it is a clean search-and-replace.
2. #401 involves structural changes (renaming concepts, possibly reorganizing sub-skills).
3. If #401 lands first, #442's research becomes partially stale (file locations may change).
4. If #442 lands first, #401's research is still valid (the words changed but the structure didn't).
5. Both are medium priority, but #442 is lower risk and can be completed faster.

### Composition engine

The `compose.py` script reads `{{include: path}}` directives. After renaming sub-skill files:
- `{{include: common/bug-filing}}` must become `{{include: common/issue-filing}}`
- `{{include: pm-specific/feature-intake}}` must become `{{include: pm-specific/task-intake}}`
- etc.

If any include path is wrong after rename, composition will fail loudly (file not found). This is a safety net.

### Test suite

Tests that assert label values (`test_labels.py`, `test_wizard.py`, `test_status_flow.py`) will fail until updated. Run full test suite after rename.

## Upgrade & Migration

### For existing installs

1. **Label rename script**: Need a script or `gh` commands to rename labels on existing repos:
   ```bash
   gh label edit "type:bug" --name "type:issue" --repo OWNER/REPO
   gh label edit "type:feature" --name "type:task" --repo OWNER/REPO
   ```
   GitHub label rename is in-place -- all existing issues with the old label automatically get the new label. No issue-by-issue relabeling needed.

2. **Issue title prefixes**: 148 existing issues have `FEAT:` or `BUG:` prefixes. Options:
   - **Option A**: Batch rename all titles via `gh issue edit`. Disruptive but consistent.
   - **Option B**: Leave existing titles, only new issues get new prefixes. Inconsistent but non-disruptive.
   - **Recommendation**: Option A for open issues (34 total), Option B for closed issues (114 total). Closed issues are historical.

3. **Composed agent files**: Must be recomposed after reference files are updated. The wizard/setup flow handles this, but existing installs need to run `squidsquad-upgrade` or manually recompose.

4. **Wizard label creation**: `wizard.py` creates labels during setup. The label maps must be updated so new installs get the correct labels.

5. **Existing planning artifacts**: Files like `FEAT-SKILL-XXX-*.md` in `.squidsquad/*/planning/` keep their names. Only the template convention changes for future files.

6. **Migration script**: Add to `wizard.py` upgrade flow:
   - Rename labels on the repo
   - Rename open issue titles (FEAT: -> TASK:, BUG: -> ISSUE:)
   - Recompose agent CLAUDE.md files
   - Log migration

### What breaks if an existing install does NOT upgrade?

- Agents will look for `type:feature`/`type:bug` labels that no longer exist (if labels were renamed on the repo)
- If labels were NOT renamed on the repo, the old install continues working fine but is out of sync with the latest templates
- Graceful degradation: agents will simply find no matching issues and idle

## Open Questions

1. **`/squidsquad-bug` command**: Rename to `/squidsquad-issue` or keep for external-facing bug reporting? (Recommendation: rename for consistency)

2. **Historical CHANGELOG entries**: Leave as-is or rewrite? (Recommendation: leave as-is, they are historical records)

3. **Closed GitHub Issue titles**: Batch rename or leave? (Recommendation: leave, they are historical)

4. **`severity` labels**: These are currently "bug severity". Under the new vocabulary, they apply to issues. Keep the `severity:` prefix or rename? (Recommendation: keep `severity:` unchanged -- it still makes sense for issues)

5. **Feature directory names**: `.squidsquad/skill/features/` and `.squidsquad/skill/bugs/` directories exist with legacy files. Rename directories? (Recommendation: these are legacy artifacts from pre-GitHub-Issues era. Leave as-is, they are not actively used.)

6. **The `bug` default GitHub label**: GitHub adds a `bug` label by default. Remove it or rename to `issue`? (Recommendation: remove it -- SquidSquad uses `type:issue` not bare `issue`)

## Recommendation

**Proceed with implementation.** This is a clean vocabulary rename with well-defined scope:

1. **Order**: Land #442 BEFORE #401 to avoid merge conflicts.
2. **Approach**:
   - Phase 1: Update all reference files (scripts, sub-skills, role templates, agent-instructions.md)
   - Phase 2: Rename sub-skill files (10 files)
   - Phase 3: Update include directives and manifest
   - Phase 4: Update SKILL.md, README.md, CONTRIBUTING.md, docs/
   - Phase 5: Update test files
   - Phase 6: Update GitHub Issue templates
   - Phase 7: Update statusline.sh and hints files
   - Phase 8: Recompose agent CLAUDE.md files
   - Phase 9: Run full test suite
   - Phase 10: GitHub label rename + open issue title rename (via script)
3. **Do NOT touch**: Historical CHANGELOG entries, closed issue titles, `manifest.py` generic English, existing planning artifact filenames, legacy `bugs/`/`features/` directories.
4. **Agent downtime**: Stop all agents before deploying. Restart after recomposition.
5. **Estimated scope**: ~60 files, ~500 individual text replacements, 10 file renames, 2 label renames, ~34 issue title renames.
