# FEAT-PM-2495 Test Plan — Rewrite /squidsquad-upgrade

## Test Cases

### TC-1: SKILL.md upgrade section rewritten
- **Precondition**: Current SKILL.md has old instructions (lines 326–379)
- **Steps**: Read the new upgrade section
- **Expected**: No references to agent-instructions.md, no manual [ROLE] substitution, no parallel subagent fan-out, no .squidsquad/templates/ creation
- **Verification**: grep for obsolete terms returns empty

### TC-2: squidsquad-upgrade.md skill file rewritten
- **Precondition**: Current .claude/commands/squidsquad-upgrade.md references agent-instructions.md and Tracker Schema
- **Steps**: Read the new skill file
- **Expected**: References compose.py deploy-all, boot-all. No Tracker Schema check. No agent-instructions.md as template source.
- **Verification**: grep for obsolete terms returns empty

### TC-3: SKILL.md and skill file agree
- **Precondition**: Both files updated
- **Steps**: Compare the upgrade flow described in SKILL.md vs the steps in squidsquad-upgrade.md
- **Expected**: Same steps in same order — no contradictions
- **Verification**: Manual comparison of step sequences

### TC-4: compose.py deploy-all is the template regeneration method
- **Precondition**: Upgrade instructions written
- **Steps**: Check instructions reference compose.py deploy-all
- **Expected**: deploy-all is the primary template build command, not manual substitution
- **Verification**: grep "compose.py deploy-all" in both files returns matches

### TC-5: SOUL.md preservation documented
- **Precondition**: Upgrade instructions written
- **Steps**: Check instructions explicitly state SOUL.md is never overwritten
- **Expected**: Clear statement that SOUL.md customizations are preserved
- **Verification**: grep "SOUL.md" in upgrade section references preservation

### TC-6: Config v1→v2 patching adds missing sections
- **Precondition**: config.md at Architecture Version 1
- **Steps**: Follow the config patching instructions
- **Expected**: Missing v2 sections added with documented defaults. Existing v1 sections untouched.
- **Verification**: All expected v2 sections present, Architecture Version set to 2, old sections still readable by config.py

### TC-7: No-install-spec fallback
- **Precondition**: .install-spec.json does not exist
- **Steps**: Follow upgrade instructions
- **Expected**: Instructions handle this gracefully — derive agent list from config.md Dev Agents field
- **Verification**: Upgrade flow works without .install-spec.json

### TC-8: wizard.py ensure-labels included
- **Precondition**: Upgrade instructions written
- **Steps**: Check for label sync step
- **Expected**: wizard.py ensure-labels called as an upgrade step
- **Verification**: grep "ensure-labels" returns match

### TC-9: Clone isolation documented
- **Precondition**: Upgrade instructions written
- **Steps**: Check for note about agent clones
- **Expected**: Instructions note that agents in sibling clones get updated CLAUDE.md on next git pull, not immediately
- **Verification**: Clone/pull note present

### TC-10: Tracker Schema check removed
- **Precondition**: New skill file
- **Steps**: Search for Tracker Schema references
- **Expected**: No references to Tracker Schema field
- **Verification**: grep "Tracker Schema" returns empty in both files

## Smoke Tests

- [ ] `python tests/run_tests.py` passes after changes
- [ ] Both SKILL.md and squidsquad-upgrade.md updated in same commit
- [ ] No references to obsolete architecture (agent-instructions.md as template, manual substitution, .squidsquad/templates/)

## Regression Risks

- SKILL.md other sections accidentally modified — diff should only touch upgrade section
- squidsquad-upgrade.md losing non-upgrade functionality — verify skill file scope is upgrade only

## Comprehension Questions

### CQ-1: How does a user upgrade SquidSquad to the latest version?
- **Files**: SKILL.md (upgrade section), .claude/commands/squidsquad-upgrade.md
- **Expected**: Run /squidsquad-upgrade or follow SKILL.md instructions. Steps: version check → compose.py deploy-all → compose.py boot-all → config patch → ensure-labels → commit. SOUL.md and vault preserved.

### CQ-2: What happens if .install-spec.json doesn't exist during upgrade?
- **Files**: .claude/commands/squidsquad-upgrade.md
- **Expected**: Upgrade derives agent list from config.md Dev Agents field and proceeds normally. No error.

### CQ-3: After running the upgrade, how do other agent clones get the updated templates?
- **Files**: SKILL.md (upgrade section)
- **Expected**: Agents in sibling clones receive updated CLAUDE.md on their next git pull (cycle_pre). The upgrade only writes to the primary repo.
