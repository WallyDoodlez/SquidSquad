# FEAT-SKILL-017 Test Plan — Externalize Agent Templates

## Test Cases

### TC-1: Setup generates templates/ directory with substituted templates
- **Precondition**: Fresh project with no `.squidsquad/` directory. User runs setup with agents `fe, be`.
- **Steps**: Run `/squidsquad-setup` with roles `fe` and `be`. Let setup complete through Step 4 (agent file generation).
- **Expected**: Directory `.squidsquad/templates/` is created containing `dev-agent-fe.md`, `dev-agent-be.md`, and `pm-agent.md`. Each template file contains fully substituted instructions (no `[ROLE]`, `[ROLE_UPPER]`, `[ROLE_TEST_CMD]`, `[OTHER_ROLES]`, `[INTERVAL]`, `[ACTIVE_AGENTS]`, `[E2E_TEST_CMD]` placeholders remain).
- **Verification**: `ls .squidsquad/templates/` shows expected files. `grep -c '\[ROLE\]\|\[ROLE_UPPER\]\|\[OTHER_ROLES\]\|\[INTERVAL\]\|\[ACTIVE_AGENTS\]\|\[E2E_TEST_CMD\]\|\[ROLE_TEST_CMD\]' .squidsquad/templates/*.md` returns 0 for each file.

### TC-2: Setup generates bootstrapper CLAUDE.md files (~20 lines)
- **Precondition**: Fresh setup with agents `fe, be`.
- **Steps**: Run setup. Inspect `.squidsquad/fe/CLAUDE.md`, `.squidsquad/be/CLAUDE.md`, and `.squidsquad/pm/CLAUDE.md`.
- **Expected**: Each CLAUDE.md is a short bootstrapper (~20 lines or fewer, definitely <50 lines). Contains role identity/config block and an imperative Read instruction pointing to the corresponding template file.
- **Verification**: `wc -l .squidsquad/fe/CLAUDE.md` returns a number under 50. `grep -c 'Read.*templates/' .squidsquad/fe/CLAUDE.md` returns at least 1. Same checks for `be` and `pm`.

### TC-3: Bootstrapper contains imperative Read instruction
- **Precondition**: Setup completed.
- **Steps**: Read each bootstrapper CLAUDE.md.
- **Expected**: Each bootstrapper contains a strong imperative instruction such as "You MUST read `.squidsquad/templates/dev-agent-fe.md` NOW before proceeding" (per side-effect mitigation requirement).
- **Verification**: `grep -i 'MUST.*read\|read.*NOW' .squidsquad/fe/CLAUDE.md` matches at least one line.

### TC-4: No leftover placeholders in generated templates
- **Precondition**: Setup completed with agents `fe, be`.
- **Steps**: Search all generated files under `.squidsquad/templates/` and `.squidsquad/*/CLAUDE.md` for any remaining placeholder syntax.
- **Expected**: Zero matches for `[ROLE]`, `[ROLE_UPPER]`, `[ROLE_TEST_CMD]`, `[OTHER_ROLES]`, `[INTERVAL]`, `[ACTIVE_AGENTS]`, `[E2E_TEST_CMD]`.
- **Verification**: `grep -rn '\[ROLE\]\|\[ROLE_UPPER\]\|\[OTHER_ROLES\]\|\[INTERVAL\]\|\[ACTIVE_AGENTS\]\|\[E2E_TEST_CMD\]\|\[ROLE_TEST_CMD\]' .squidsquad/templates/ .squidsquad/fe/CLAUDE.md .squidsquad/be/CLAUDE.md .squidsquad/pm/CLAUDE.md` returns no matches.

### TC-5: Agent reads template via bootstrapper Read instruction (end-to-end chain)
- **Precondition**: Setup completed. `.squidsquad/.active-role` set to `fe`.
- **Steps**: Start a Claude Code session. Root CLAUDE.md auto-loads, reads `.active-role`, reads `.squidsquad/fe/CLAUDE.md` (bootstrapper), which instructs agent to read `.squidsquad/templates/dev-agent-fe.md`.
- **Expected**: Agent successfully loads the full template and begins the Ralph Loop. The chain root CLAUDE.md -> bootstrapper -> template completes without errors.
- **Verification**: Agent prints `[🦑] Pulling latest...` (Ralph Loop Step 1) within its first actions, confirming it loaded and followed the template instructions.

### TC-6: Upgrade detects inline CLAUDE.md and migrates to bootstrapper + template
- **Precondition**: Existing setup with old-style inline CLAUDE.md files (>50 lines, containing `## The Ralph Loop`).
- **Steps**: Run `/squidsquad-upgrade`.
- **Expected**: Upgrade detects inline format (presence of `## The Ralph Loop` heading). Creates `.squidsquad/templates/` with substituted templates. Replaces each inline CLAUDE.md with a bootstrapper. Original inline content is preserved in the template files.
- **Verification**: `grep -c '## The Ralph Loop' .squidsquad/fe/CLAUDE.md` returns 0 (no longer inline). `wc -l .squidsquad/fe/CLAUDE.md` returns <50. `.squidsquad/templates/dev-agent-fe.md` exists and contains `## The Ralph Loop`. `grep -c '## The Ralph Loop' .squidsquad/templates/dev-agent-fe.md` returns 1.

### TC-7: Upgrade regenerates templates but leaves bootstrappers untouched
- **Precondition**: Already-migrated setup with bootstrapper CLAUDE.md files and existing templates/ directory.
- **Steps**: Note the content and timestamp of `.squidsquad/fe/CLAUDE.md`. Run `/squidsquad-upgrade`.
- **Expected**: Templates in `.squidsquad/templates/` are regenerated from `references/agent-instructions.md`. Bootstrapper CLAUDE.md files remain identical (content unchanged).
- **Verification**: `diff` the pre-upgrade and post-upgrade bootstrapper files — they should be identical. Templates may differ if the source template was updated.

### TC-8: Mixed state handling (partial migration)
- **Precondition**: `.squidsquad/templates/` exists with some templates, but one agent's CLAUDE.md is still inline (old format with `## The Ralph Loop`).
- **Steps**: Run `/squidsquad-upgrade`.
- **Expected**: Upgrade detects mixed state. Migrates the inline CLAUDE.md to bootstrapper format. Regenerates all templates. Does not corrupt the already-migrated bootstrappers.
- **Verification**: All CLAUDE.md files are <50 lines. All templates exist in `.squidsquad/templates/`. No agent CLAUDE.md contains `## The Ralph Loop`.

### TC-9: Missing template file produces clear error
- **Precondition**: Setup completed. Manually delete `.squidsquad/templates/dev-agent-fe.md`.
- **Steps**: Start a Claude Code session with `.active-role` set to `fe`. Agent reads bootstrapper, attempts to read missing template.
- **Expected**: Agent encounters file-not-found when trying to read the template. Bootstrapper instructions should guide the agent to output a clear error directing the user to run `/squidsquad-upgrade` to regenerate templates.
- **Verification**: Agent output contains an error message mentioning the missing template file path and suggesting `/squidsquad-upgrade` (or equivalent recovery action).

### TC-10: Multiple dev agents each get their own substituted template
- **Precondition**: Setup with three dev agents: `fe`, `be`, `api`.
- **Steps**: Run setup. Inspect templates directory.
- **Expected**: Three separate template files exist: `dev-agent-fe.md`, `dev-agent-be.md`, `dev-agent-api.md`. Each contains role-specific substitutions (e.g. `fe` template references `fe/bugs.md`, `be` template references `be/bugs.md`). PM template also exists as `pm-agent.md`.
- **Verification**: `ls .squidsquad/templates/` shows all four files. `grep 'fe' .squidsquad/templates/dev-agent-fe.md | head -3` shows fe-specific paths. `grep 'be' .squidsquad/templates/dev-agent-be.md | head -3` shows be-specific paths. No cross-contamination (fe template does not reference be paths in role-specific locations).

### TC-11: Template content matches source template structure
- **Precondition**: Setup completed.
- **Steps**: Compare a generated template (e.g. `dev-agent-fe.md`) against Template 1 in `references/agent-instructions.md`.
- **Expected**: The generated template has the same section structure (headings, protocols, loop steps) as the source. Only placeholder values differ (substituted with role-specific values).
- **Verification**: Extract headings from both files and compare: `grep '^##' references/agent-instructions.md` (Template 1 section) vs `grep '^##' .squidsquad/templates/dev-agent-fe.md` — headings should match structurally.

### TC-12: Root CLAUDE.md unchanged by this feature
- **Precondition**: Setup completed with new template architecture.
- **Steps**: Read root `CLAUDE.md`.
- **Expected**: Root CLAUDE.md still uses the existing auto-boot pattern: read `.active-role`, then read `.squidsquad/<role>/CLAUDE.md`. It does NOT reference templates directly. The bootstrapper handles the second level of indirection.
- **Verification**: `grep -c 'templates/' CLAUDE.md` returns 0 (root CLAUDE.md does not mention templates).

### TC-13: Bootstrapper config block contains all required role values
- **Precondition**: Setup completed with `fe, be` agents.
- **Steps**: Read `.squidsquad/fe/CLAUDE.md` bootstrapper.
- **Expected**: Config block includes role name, role_upper, test_cmd, other_roles, interval, and template file path. All values are correct for the `fe` role.
- **Verification**: Bootstrapper contains `role: fe` (or equivalent), mentions other agents, and points to the correct template path.

### TC-14: Permissions allow template read/write
- **Precondition**: Setup completed. Check `.claude/settings.json`.
- **Steps**: Inspect permission globs in settings.json.
- **Expected**: Existing `Edit(.squidsquad/**)` and `Write(.squidsquad/**)` globs cover the new `templates/` subdirectory. No permission changes needed.
- **Verification**: `grep 'squidsquad' .claude/settings.json` shows glob patterns that cover `.squidsquad/templates/`.

## Smoke Tests

- [ ] After fresh setup: `.squidsquad/templates/` directory exists with at least one `dev-agent-*.md` and one `pm-agent.md`
- [ ] After fresh setup: each agent's `CLAUDE.md` is under 50 lines
- [ ] After fresh setup: `grep -r '\[ROLE\]' .squidsquad/templates/` returns no matches
- [ ] After fresh setup: each bootstrapper contains a Read instruction pointing to a template file that actually exists
- [ ] After upgrade from inline: no CLAUDE.md under `.squidsquad/*/` contains `## The Ralph Loop`
- [ ] Agent startup with `.active-role` set proceeds through root -> bootstrapper -> template chain without errors
- [ ] `references/agent-instructions.md` still contains `[ROLE]` placeholders (source templates unchanged)

## Regression Risks

- **Root CLAUDE.md auto-boot breaks**: Adding a second level of indirection (bootstrapper -> template) could break if the agent does not follow the Read instruction. Watch for agents that stop after reading the bootstrapper and never load the template.
- **Upgrade overwrites user customizations**: If a user added custom content to their inline CLAUDE.md, migration must not silently discard it. Watch for lost project-specific context (like the current `skill/CLAUDE.md` which has custom project context).
- **Existing inline setups still work pre-migration**: Until a user runs upgrade, their old inline CLAUDE.md files must continue to function normally. The feature must not break setups that have not yet migrated.
- **FEAT-SKILL-018 subagent delegation compatibility**: Subagent prompts reference agent behavior. If subagent spawning reads CLAUDE.md content and now gets a 20-line bootstrapper instead of full instructions, subagent behavior could degrade. Verify subagent prompts are self-contained and do not depend on CLAUDE.md content.
- **Template naming collision**: If a role name conflicts with template naming conventions (e.g., a role named `pm-agent`), the template file path could collide. Watch for edge cases in role naming.
- **statusline.sh unaffected**: The status line script reads `.active-role` and tracker files, not CLAUDE.md. Verify it still works after migration.
- **Setup flow Step 2 folder structure**: The `templates/` directory must be included in the folder structure creation step. Missing it would cause template write failures.
