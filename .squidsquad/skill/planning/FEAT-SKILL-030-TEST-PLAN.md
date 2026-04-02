# FEAT-SKILL-030 Test Plan — Sub-skill Architecture

## Overview

This test plan covers Phase A of the sub-skill architecture: decomposing `references/agent-instructions.md` into composable sub-skill source files under `references/sub-skills/`, with build-time composition producing the same templates agents read today. The plan validates correctness of composition, safety of upgrade migration, preservation of all existing behavior, and support for all team shapes.

**Key invariant**: After composition, agents must receive functionally identical instructions to what they receive today. The only permitted differences are section marker comments (`<!-- sub-skill: [name] -->`) and the `Architecture Version` field in config.md.

---

## Test Cases

### TC-1: Sub-skill source files exist and are complete
- **Precondition**: FEAT-SKILL-030 implementation is complete; `references/sub-skills/` directory tree exists.
- **Steps**:
  1. List all files under `references/sub-skills/common/`, `references/sub-skills/roles/`, and all `*-specific/` directories.
  2. Verify each file listed in the RESEARCH.md "New files" section exists.
  3. Verify each file has non-empty content and valid markdown structure.
- **Expected**: All planned sub-skill source files exist with meaningful content. No empty or placeholder files.
- **Verification**: `find references/sub-skills/ -name "*.md" | sort` produces the expected file list; `wc -l references/sub-skills/**/*.md` shows non-zero line counts for all files.

### TC-2: Composed dev-agent template matches monolithic template (diff-verified)
- **Precondition**: Sub-skill source files exist. Current monolithic `references/agent-instructions.md` is unchanged from pre-implementation baseline.
- **Steps**:
  1. Extract Template 1 (Dev Agent) from the current monolithic `references/agent-instructions.md` (lines between `## Template 1:` and `## Template 2:`).
  2. Read the composed dev-agent output from `references/agent-instructions.md` (now generated) or from a test composition run.
  3. Strip all `<!-- sub-skill: ... -->` marker lines from the composed output.
  4. Diff the stripped composed output against the extracted monolithic template.
- **Expected**: Zero meaningful differences. Only permitted differences: whitespace normalization, section markers (already stripped), and the "DO NOT EDIT" header.
- **Verification**: `diff <(grep -v '<!-- sub-skill:' composed-dev.md) <(cat baseline-dev.md)` returns empty or only shows the "DO NOT EDIT" header line.

### TC-3: Composed PM template matches monolithic template (diff-verified)
- **Precondition**: Same as TC-2.
- **Steps**:
  1. Extract Template 2 (PM/QA) from monolithic `references/agent-instructions.md`.
  2. Read the composed PM output.
  3. Strip section markers.
  4. Diff against monolithic baseline.
- **Expected**: Zero meaningful differences (same rules as TC-2).
- **Verification**: Same diff approach as TC-2, applied to PM template.

### TC-4: Composed DM template matches monolithic template (diff-verified)
- **Precondition**: Same as TC-2.
- **Steps**:
  1. Extract Template 3 (DM) from monolithic `references/agent-instructions.md`.
  2. Read the composed DM output.
  3. Strip section markers.
  4. Diff against monolithic baseline.
- **Expected**: Zero meaningful differences.
- **Verification**: Same diff approach as TC-2, applied to DM template.

### TC-5: Section markers are present and well-formed in composed output
- **Precondition**: Composition has run, producing `references/agent-instructions.md` (generated).
- **Steps**:
  1. Read the composed `references/agent-instructions.md`.
  2. Search for all `<!-- sub-skill: ... -->` markers.
  3. Verify each marker names a sub-skill that exists as a source file under `references/sub-skills/`.
  4. Verify markers appear in a logical order (common sub-skills before role-specific ones).
  5. Verify no nested or duplicate markers for the same sub-skill within a single template.
- **Expected**: Every composed template section has a corresponding marker. Every marker references a real sub-skill file. No orphaned markers.
- **Verification**: `grep -o '<!-- sub-skill: [^ ]*' references/agent-instructions.md | sort -u` lists only valid sub-skill names; cross-check against `ls references/sub-skills/**/*.md`.

### TC-6: agent-instructions.md has "DO NOT EDIT" header
- **Precondition**: Composition has run.
- **Steps**:
  1. Read the first 5 lines of `references/agent-instructions.md`.
  2. Check for a "DO NOT EDIT" or equivalent auto-generated warning.
- **Expected**: A clear header indicating the file is generated and should not be edited directly, with a pointer to `references/sub-skills/` as the source of truth.
- **Verification**: `head -5 references/agent-instructions.md` contains "DO NOT EDIT" or "auto-generated".

### TC-7: Placeholder substitution works after composition
- **Precondition**: Sub-skill composition produces a template with `[ROLE]`, `[ROLE_UPPER]`, `[ROLE_TEST_CMD]`, `[OTHER_ROLES]`, `[INTERVAL]` placeholders intact.
- **Steps**:
  1. Run setup or upgrade with config: Dev Agents = `skill`, Interval = 30, test cmd = `echo "test"`.
  2. Read the generated `.squidsquad/templates/dev-agent-skill.md`.
  3. Search for any remaining unsubstituted `[ROLE]`, `[ROLE_UPPER]`, `[ROLE_TEST_CMD]`, `[OTHER_ROLES]`, `[INTERVAL]` placeholders.
- **Expected**: Zero unsubstituted placeholders remain. All `[ROLE]` replaced with `skill`, `[ROLE_UPPER]` with `SKILL`, etc.
- **Verification**: `grep -c '\[ROLE\]\|\[ROLE_UPPER\]\|\[ROLE_TEST_CMD\]\|\[OTHER_ROLES\]\|\[INTERVAL\]' .squidsquad/templates/dev-agent-skill.md` returns 0.

### TC-8: Fresh install produces correct sub-skill structure
- **Precondition**: No `.squidsquad/` directory exists. SKILL.md contains sub-skill architecture.
- **Steps**:
  1. Run `/squidsquad` setup with: project name "TestProject", dev agents "be", test cmd "npm test", e2e "npm run e2e".
  2. Verify `references/sub-skills/` directory exists with all source files.
  3. Verify `.squidsquad/templates/dev-agent-be.md` exists and contains composed content.
  4. Verify `.squidsquad/templates/pm-agent.md` exists and contains composed content.
  5. Verify `config.md` contains `Architecture Version: 1`.
  6. Verify `references/agent-instructions.md` has "DO NOT EDIT" header.
- **Expected**: Full sub-skill structure created. Templates are composed from sub-skills. Config tracks architecture version.
- **Verification**: File existence checks + content verification per above.

### TC-9: Upgrade from monolithic to sub-skill (migration path)
- **Precondition**: Existing install with monolithic `references/agent-instructions.md` (no `references/sub-skills/` directory). Config has no `Architecture Version` field.
- **Steps**:
  1. Verify `references/sub-skills/` does NOT exist (pre-upgrade state).
  2. Run `/squidsquad-upgrade`.
  3. Verify `references/sub-skills/` directory is created with all source files.
  4. Verify `references/agent-instructions.md` is replaced with composed/generated version.
  5. Verify `.squidsquad/templates/dev-agent-*.md` are regenerated from sub-skill composition.
  6. Verify `config.md` now has `Architecture Version: 1`.
  7. Verify upgrade commit message and single-commit atomicity.
- **Expected**: Clean migration. All templates regenerated. Config updated. Single atomic commit.
- **Verification**: `git log -1 --oneline` shows upgrade commit; `test -d references/sub-skills` succeeds; `grep "Architecture Version" .squidsquad/config.md` returns `1`.

### TC-10: Upgrade detects already-migrated install (sub-skill to sub-skill)
- **Precondition**: Install already has `references/sub-skills/` and `Architecture Version: 1` in config.
- **Steps**:
  1. Modify a sub-skill source file (simulate SKILL.md version bump with sub-skill content change).
  2. Run `/squidsquad-upgrade`.
  3. Verify templates are regenerated from updated sub-skill sources.
  4. Verify sub-skill source files are updated (not re-created from scratch).
- **Expected**: Incremental upgrade. Templates reflect updated sub-skill content. No duplicate sub-skill directories.
- **Verification**: Diff templates before/after shows expected content change propagated.

### TC-11: Architecture Version field added to config.md
- **Precondition**: Existing `config.md` with no `Architecture Version` field.
- **Steps**:
  1. Run upgrade.
  2. Read `config.md`.
  3. Verify `Architecture Version: 1` is present.
  4. Verify existing fields (SquidSquad Version, Tracker Schema, Agents, etc.) are unchanged.
- **Expected**: New field added without disrupting existing config structure.
- **Verification**: `grep "Architecture Version" .squidsquad/config.md` returns `Architecture Version: 1`; diff config pre/post shows only the new field and version bump.

### TC-12: Multi-dev agent team shape (fe, be)
- **Precondition**: Config has `Dev Agents: fe, be`.
- **Steps**:
  1. Run setup or upgrade.
  2. Verify `references/sub-skills/` contains role source files usable for both fe and be.
  3. Verify `.squidsquad/templates/dev-agent-fe.md` is generated with `[ROLE]=fe`, `[OTHER_ROLES]=be`.
  4. Verify `.squidsquad/templates/dev-agent-be.md` is generated with `[ROLE]=be`, `[OTHER_ROLES]=fe`.
  5. Verify cross-filing bug instructions reference the other role correctly.
- **Expected**: Each dev agent gets a correctly substituted template. Cross-filing references are accurate.
- **Verification**: `grep "OTHER_ROLES" .squidsquad/templates/dev-agent-fe.md` returns 0 (all substituted); content mentions `be` as the other role.

### TC-13: Single dev agent team shape
- **Precondition**: Config has `Dev Agents: skill` (single dev, like SquidSquad itself).
- **Steps**:
  1. Run setup or upgrade.
  2. Verify `.squidsquad/templates/dev-agent-skill.md` is generated.
  3. Verify `[OTHER_ROLES]` is substituted as empty (no other dev agents).
  4. Verify cross-filing bug section handles the empty-other-roles case gracefully.
- **Expected**: Template works correctly for solo dev agent. No broken references to nonexistent other roles.
- **Verification**: Read template, verify no "file to [OTHER_ROLE]" instructions remain with empty role names.

### TC-14: DM present team shape
- **Precondition**: `.squidsquad/dm/` directory exists (DM opted in).
- **Steps**:
  1. Run upgrade.
  2. Verify `.squidsquad/templates/dm-agent.md` is regenerated from sub-skill composition.
  3. Verify DM template includes DM-specific sub-skills (delivery-packaging, version-bumps).
  4. Verify PM template does NOT include DM fallback delivery logic (since DM is present).
- **Expected**: DM gets its own composed template. PM template reflects DM-present configuration.
- **Verification**: `test -f .squidsquad/templates/dm-agent.md` succeeds; template content includes delivery sections.

### TC-15: DM absent team shape (PM handles delivery)
- **Precondition**: No `.squidsquad/dm/` directory.
- **Steps**:
  1. Run upgrade.
  2. Verify NO `.squidsquad/templates/dm-agent.md` is created.
  3. Verify PM template includes delivery fallback logic (Step 6d equivalent).
- **Expected**: DM artifacts are not created. PM retains delivery fallback capability.
- **Verification**: `test ! -f .squidsquad/templates/dm-agent.md`; PM template contains delivery fallback section.

### TC-16: Missing sub-skill source file fails composition early
- **Precondition**: Sub-skill architecture is installed. One sub-skill source file is deleted (e.g., `references/sub-skills/common/ralph-loop-core.md`).
- **Steps**:
  1. Delete `references/sub-skills/common/ralph-loop-core.md`.
  2. Run `/squidsquad-upgrade`.
  3. Observe error behavior.
- **Expected**: Composition fails early with a clear error message naming the missing file. Existing templates in `.squidsquad/templates/` are NOT overwritten. Error message suggests running `/squidsquad-upgrade` after restoring the file (or `git checkout` to recover it).
- **Verification**: Upgrade exits with error; existing templates remain unchanged (diff shows no change).

### TC-17: Non-bootstrapper CLAUDE.md detection and backup
- **Precondition**: `.squidsquad/skill/CLAUDE.md` contains the full Ralph Loop inline (>50 lines, contains `## The Ralph Loop`), simulating a pre-bootstrapper install or manual edit.
- **Steps**:
  1. Verify CLAUDE.md is >50 lines and contains `## The Ralph Loop`.
  2. Run `/squidsquad-upgrade`.
  3. Verify the old CLAUDE.md is backed up (e.g., `CLAUDE.md.bak` or noted in Discussion).
  4. Verify the new CLAUDE.md is the bootstrapper format (~20 lines, Read instruction to template).
- **Expected**: Upgrade detects non-bootstrapper format, backs up the file, replaces with bootstrapper. No silent data loss.
- **Verification**: `wc -l .squidsquad/skill/CLAUDE.md` shows ~20 lines; backup file exists or Discussion entry notes the migration.

### TC-18: Composition order produces valid template structure
- **Precondition**: Sub-skill source files exist.
- **Steps**:
  1. Read a composed template (e.g., dev-agent).
  2. Verify the document flows logically: role intro -> responsibilities -> startup -> Ralph Loop (pull, context check, working state, interval sync, triage, implement, log, commit, done) -> discussion protocol -> filing bugs -> working state file -> file conventions -> status line -> prohibitions.
  3. Verify no sections are duplicated.
  4. Verify no sections are missing compared to the current monolithic template.
- **Expected**: Composed template has the same logical structure and section ordering as the current monolithic template.
- **Verification**: Compare section headers (## and ### lines) between composed and monolithic templates; they should match.

### TC-19: Template size does not exceed monolithic size (excluding markers)
- **Precondition**: Composition has run.
- **Steps**:
  1. Count lines in each composed template (excluding `<!-- sub-skill: ... -->` markers).
  2. Count lines in the corresponding monolithic template baseline.
  3. Compare.
- **Expected**: Composed templates are equal to or smaller than monolithic templates (sub-skill extraction eliminates duplication). PM template stays under ~600 lines.
- **Verification**: `grep -vc '<!-- sub-skill:' .squidsquad/templates/pm-agent.md` compared to baseline line count.

### TC-20: Atomic commit during upgrade
- **Precondition**: Monolithic install ready for upgrade.
- **Steps**:
  1. Run `/squidsquad-upgrade`.
  2. Check `git log -1 --stat` to see all files in the upgrade commit.
  3. Verify sub-skill source files, composed templates, config.md changes, and any boot script updates are ALL in the same commit.
- **Expected**: Single commit contains all changes. No intermediate commits that could leave the install in a partial state.
- **Verification**: `git log -1 --stat` shows all expected files; `git log --oneline -3` shows exactly one new commit for the upgrade.

### TC-21: Graceful degradation when user does not upgrade
- **Precondition**: SKILL.md has been updated to sub-skill architecture (new version). User's install is still monolithic (old version in config.md). User does NOT run upgrade.
- **Steps**:
  1. Verify existing `.squidsquad/templates/*.md` files are untouched (no external process modifies them).
  2. Boot a dev agent using the existing boot script.
  3. Verify the agent reads the old template and operates normally.
- **Expected**: Old templates continue to work. Agents are unaffected. The version mismatch is only detected when `/squidsquad-upgrade` is explicitly run.
- **Verification**: Agent boots successfully and can execute a Ralph Loop cycle with old templates.

### TC-22: Composed template placeholder ordering (compose then substitute)
- **Precondition**: Sub-skill source files contain raw `[ROLE]`, `[INTERVAL]` etc. placeholders.
- **Steps**:
  1. Read sub-skill source files and verify they contain placeholders (not hardcoded values).
  2. Run composition.
  3. Verify the intermediate composed template (before substitution) still has placeholders.
  4. After substitution, verify all placeholders are resolved.
- **Expected**: Composition preserves placeholders. Substitution happens as a second pass after composition. No premature substitution in source files.
- **Verification**: Sub-skill source files contain `[ROLE]` literals; final templates do not.

---

## Edge Case Test Cases

### TC-23: Sub-skill with conflicting section names
- **Precondition**: Two sub-skills define content for the same conceptual area (e.g., both tracker-protocol and git-protocol mention commit behavior).
- **Steps**:
  1. Read `references/sub-skills/common/tracker-protocol.md` and `references/sub-skills/common/git-protocol.md`.
  2. Verify they have clear ownership boundaries (tracker-protocol owns format, git-protocol owns push/pull mechanics).
  3. Verify no duplicated instructions in the composed output.
- **Expected**: Each sub-skill owns its domain cleanly. No contradictory or duplicated instructions in the composed template.
- **Verification**: Manual review of composed output for duplicate paragraphs or conflicting instructions.

### TC-24: Empty sub-skill source file
- **Precondition**: One sub-skill source file exists but is empty (0 bytes).
- **Steps**:
  1. Create an empty `references/sub-skills/common/test-empty.md`.
  2. If this sub-skill is referenced in composition, run composition.
- **Expected**: Composition either skips the empty file with a warning or fails with a clear error. Does not produce a template with missing sections.
- **Verification**: Composed output does not have an empty gap where the sub-skill content should be.

### TC-25: Windows path handling in sub-skill references
- **Precondition**: Running on Windows with Git Bash.
- **Steps**:
  1. Verify all file references in SKILL.md and sub-skill source files use forward slashes.
  2. Run composition on Windows.
  3. Verify all file paths in composed templates use forward slashes.
- **Expected**: Forward slashes used throughout. No backslash path separators introduced by composition.
- **Verification**: `grep '\\\\' .squidsquad/templates/*.md` returns no matches (no backslash paths).

### TC-26: Sub-skill source file with trailing whitespace or BOM
- **Precondition**: A sub-skill source file has a UTF-8 BOM or trailing whitespace on lines.
- **Steps**:
  1. Composition runs with the BOM/whitespace-containing file.
  2. Check composed output.
- **Expected**: BOM is not propagated into composed templates. Trailing whitespace does not cause diff failures against baseline.
- **Verification**: `file references/agent-instructions.md` does not show BOM; diff against baseline is clean.

---

## Side Effect Regression Tests

### TC-27: Boot scripts unchanged
- **Precondition**: Sub-skill architecture is installed.
- **Steps**:
  1. Read `.squidsquad/start-skill.sh` and `.squidsquad/start-skill.ps1`.
  2. Verify they still use `--append-system-prompt` with `SQUIDSQUAD_ROLE=skill`.
  3. Verify the boot chain: system prompt -> root CLAUDE.md -> `.squidsquad/skill/CLAUDE.md` -> Read template.
- **Expected**: Boot scripts are unchanged or functionally identical. The agent boot path is not affected by sub-skill architecture.
- **Verification**: Diff boot scripts before/after sub-skill implementation; changes (if any) are cosmetic only.

### TC-28: Statusline script unchanged
- **Precondition**: Sub-skill architecture is installed.
- **Steps**:
  1. Read `.squidsquad/statusline.sh`.
  2. Verify it still reads `current-state`, `config.md`, tracker `INDEX.md` files, `working-state.md`, and git log.
  3. Verify it does NOT reference `references/sub-skills/` or any sub-skill files.
- **Expected**: Statusline script is completely unaffected by sub-skill architecture.
- **Verification**: `grep -c 'sub-skill' .squidsquad/statusline.sh` returns 0.

### TC-29: Tracker Schema 3 format preserved
- **Precondition**: Sub-skill architecture is installed. Tracker files exist in Schema 3 format (individual files + INDEX.md).
- **Steps**:
  1. Read the tracker format documentation in the composed template (the section that was `tracker-protocol` sub-skill).
  2. Compare against the current tracker format in the monolithic template.
  3. Verify field names, status values, file naming conventions, INDEX.md format, and archival rules are identical.
- **Expected**: Zero differences in tracker format documentation. Agents will generate identical tracker files.
- **Verification**: Extract tracker sections from both monolithic and composed templates; diff shows no differences.

### TC-30: Config.md structure preserved (existing fields)
- **Precondition**: Existing config.md with all current fields.
- **Steps**:
  1. Run upgrade.
  2. Read config.md.
  3. Verify all existing fields are present and unchanged: SquidSquad Version, Tracker Schema, Agents, Project, Test Commands, ID Counters, Git Protocol, Iteration Interval, Context Pressure, PR Flow, GitHub Issues Ingestion, Auto Versioning.
  4. Verify only additions are: `Architecture Version` field and version bump.
- **Expected**: No existing fields removed or reformatted. Only additive changes.
- **Verification**: Diff config.md before/after; only `Architecture Version` line and version number change appear.

### TC-31: Permissions template unchanged
- **Precondition**: Sub-skill architecture is installed.
- **Steps**:
  1. Verify `.squidsquad/inject-permissions.sh` and `.squidsquad/permissions.template.json` are not modified by the sub-skill implementation.
- **Expected**: Permission injection is completely unaffected.
- **Verification**: `git diff .squidsquad/inject-permissions.sh .squidsquad/permissions.template.json` shows no changes.

### TC-32: Cross-clone health checks unaffected
- **Precondition**: `.squidsquad/.local-config` exists with cross-clone paths.
- **Steps**:
  1. Verify `.local-config` format is unchanged.
  2. Verify `current-state` file locations are unchanged (`.squidsquad/[role]/current-state`).
- **Expected**: Cross-clone health checks continue to work because they read runtime files, not templates or sub-skills.
- **Verification**: `.local-config` and `current-state` paths are identical before/after.

### TC-33: Working state file format unchanged
- **Precondition**: Agent has an active working state.
- **Steps**:
  1. Read the working state file format in the composed template.
  2. Compare against the monolithic template.
- **Expected**: Identical format. Agents can resume from working states created before the sub-skill migration.
- **Verification**: Working state section in composed template matches monolithic template exactly.

### TC-34: Discussion protocol unchanged
- **Precondition**: Sub-skill architecture installed.
- **Steps**:
  1. Read the Discussion protocol section in all composed templates.
  2. Verify format (`> [YYYY-MM-DD HH:MM] **role**: message`), append-only rule, and cross-agent communication rules are identical to monolithic.
- **Expected**: No changes to Discussion protocol.
- **Verification**: Extract Discussion protocol sections; diff against monolithic baseline.

### TC-35: Feature lifecycle statuses unchanged
- **Precondition**: Sub-skill architecture installed.
- **Steps**:
  1. Read feature status progression in composed templates.
  2. Verify: `Pending` -> `Planning` -> `Approved` -> `In Progress` -> `Pending Test` -> `Pending Ship` -> `Shipped`.
- **Expected**: Feature lifecycle is identical to Schema 2/3 definitions.
- **Verification**: Grep for status values in composed templates; all present in correct order.

---

## Upgrade Verification Tests

### TC-36: Upgrade from v0.8.0 monolithic to sub-skill architecture
- **Precondition**: Install at v0.8.0 with monolithic templates, Tracker Schema 3, no `Architecture Version` in config.
- **Steps**:
  1. Run `/squidsquad-upgrade`.
  2. Verify `references/sub-skills/` created.
  3. Verify `references/agent-instructions.md` regenerated with "DO NOT EDIT" header.
  4. Verify all templates in `.squidsquad/templates/` regenerated.
  5. Verify config.md updated: new version, `Architecture Version: 1`.
  6. Verify tracker files in `skill/bugs/`, `skill/features/` are NOT touched.
  7. Verify `pm/qa-log.md`, `pm/enhancements.md` are NOT touched.
- **Expected**: Clean upgrade. Only template generation pipeline changes. All runtime data preserved.
- **Verification**: `git diff --stat HEAD~1` shows only template/reference/config changes, no tracker file changes.

### TC-37: Non-upgraded install continues working
- **Precondition**: SKILL.md updated to sub-skill version. User has NOT run upgrade. Install still has monolithic templates.
- **Steps**:
  1. Boot the skill-lead agent using existing boot script.
  2. Agent reads `.squidsquad/skill/CLAUDE.md` (bootstrapper).
  3. Agent reads `.squidsquad/templates/dev-agent-skill.md` (old monolithic-generated template).
  4. Agent executes a Ralph Loop cycle.
- **Expected**: Agent works normally with old templates. No errors. No awareness of sub-skill architecture.
- **Verification**: Agent completes a cycle without errors; no references to sub-skills in agent output.

### TC-38: Double upgrade is idempotent
- **Precondition**: Install already upgraded to sub-skill architecture.
- **Steps**:
  1. Run `/squidsquad-upgrade` again.
  2. Verify it detects versions match (or re-applies cleanly).
  3. Verify no duplicate sub-skill files or config entries.
- **Expected**: Either reports "already up to date" or re-generates cleanly without duplication.
- **Verification**: `git diff` after second upgrade shows no changes (or only timestamp-type changes).

### TC-39: Upgrade preserves ID counters
- **Precondition**: Config has `BUG-SKILL: 38`, `FEAT-SKILL: 58`.
- **Steps**:
  1. Run upgrade.
  2. Read config.md.
  3. Verify ID counters are unchanged.
- **Expected**: `BUG-SKILL: 38`, `FEAT-SKILL: 58` preserved exactly.
- **Verification**: `grep "BUG-SKILL\|FEAT-SKILL" .squidsquad/config.md` shows unchanged values.

### TC-40: Upgrade preserves custom config values
- **Precondition**: Config has non-default values: `Iteration Interval: 45`, `Context Pressure Threshold: 70`, `PR Flow: yes`.
- **Steps**:
  1. Run upgrade.
  2. Read config.md.
  3. Verify all custom values are preserved.
- **Expected**: No config values reset to defaults during upgrade.
- **Verification**: Diff config.md before/after; only version and architecture version fields change.

---

## Smoke Tests

- [ ] `references/sub-skills/` directory exists after implementation
- [ ] `references/sub-skills/common/` has at least 5 source files (ralph-loop-core, context-pressure, tracker-protocol, git-protocol, discussion-protocol, status-line, interval-sync)
- [ ] `references/sub-skills/roles/` has 3 files (dev-agent.md, pm-agent.md, dm-agent.md)
- [ ] `references/agent-instructions.md` first line contains "DO NOT EDIT" or "auto-generated"
- [ ] `grep -c '<!-- sub-skill:' references/agent-instructions.md` returns > 0 (section markers present)
- [ ] `grep -c '\[ROLE\]' references/agent-instructions.md` returns > 0 (placeholders preserved in composed template)
- [ ] `.squidsquad/config.md` contains `Architecture Version` field after upgrade
- [ ] `.squidsquad/templates/dev-agent-skill.md` contains no `[ROLE]` placeholders (fully substituted)
- [ ] `.squidsquad/templates/dev-agent-skill.md` contains `## The Ralph Loop` (core content present)
- [ ] Boot scripts (`start-skill.sh`, `start-pm.sh`) are not broken (contain `claude` invocation)
- [ ] `wc -l .squidsquad/templates/pm-agent.md` is <= 650 lines (no template size explosion)
- [ ] No files in `.squidsquad/skill/bugs/` or `.squidsquad/skill/features/` were modified by the implementation (tracker data untouched)

---

## Regression Risks

- **Tracker format drift**: If the `tracker-protocol` sub-skill extraction introduces even subtle wording changes in tracker field definitions, agents may generate malformed tracker files. Mitigate with TC-29 (byte-level diff of tracker sections).
- **Ralph Loop step numbering**: If sub-skill boundaries split a step across files, the composed output may have inconsistent step numbering (e.g., Step 3 in one sub-skill, Step 3 in another). Mitigate with TC-18 (structure verification).
- **Placeholder double-substitution**: If a sub-skill source file accidentally contains a resolved value (e.g., `skill` instead of `[ROLE]`), composition will propagate the hardcoded value. This only affects multi-role setups where `fe` and `be` templates must differ. Mitigate with TC-22 (verify placeholders in sources).
- **PM delivery fallback logic**: The PM template's delivery fallback (when DM absent) is currently inline. If it moves to a PM-specific sub-skill, it must still be conditionally included based on DM presence. Mitigate with TC-15 (DM absent team shape).
- **Cross-filing bug instructions**: Dev templates have role-specific cross-filing logic (`file to [OTHER_ROLE]`). If this moves to a common sub-skill, placeholder substitution must still produce correct per-role output. Mitigate with TC-12 and TC-13.
- **agent-instructions.md backward compatibility**: The upgrade flow currently reads `references/agent-instructions.md` as the source. If it becomes a generated artifact but the upgrade flow is not updated simultaneously, upgrade could read stale content. Mitigate with TC-20 (atomic commit) and TC-9 (full upgrade path verification).
- **Git merge conflicts in sub-skill files**: Future concurrent edits to sub-skill source files may cause merge conflicts that are harder to resolve than conflicts in a single monolithic file. This is a post-ship risk, not testable now, but worth monitoring.
- **Context pressure from section markers**: If markers add significant line count, templates may push closer to context limits. Mitigate with TC-19 (size check).
