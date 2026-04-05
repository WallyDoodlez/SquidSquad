# Issue #29 Test Plan — Agent Name Aliases

**Feature**: Assign custom names (aliases) during setup, default to bare role name
**Scope**: Config storage, boot scripts, git commits, GH comments, status bar, setup flow, propagation, safety, backward compat
**Delivery**: One shot

---

## A. Config Storage

### TC-01: Aliases section exists in config.md
- **Check**: `grep -c "## Aliases" .squidsquad/config.md`
- **Expected**: Returns >= 1
- **Failure means**: Config template was not updated with the new section

### TC-02: Each active agent has an alias entry
- **Steps**:
  1. Read `Dev Agents` list from config.md (currently: `skill`)
  2. PM and QA are always present
  3. For each role, verify a line matching `- **{role}**: {value}` exists under `## Aliases`
- **Expected**: Every active role has a parseable alias entry
- **Failure means**: Alias entries are missing or malformed

### TC-03: Default aliases are bare role names
- **Steps**: Read each alias value from the `## Aliases` section
- **Expected**: Default values are `skill`, `pm`, `qa` (bare role names, no project prefix)
- **Failure means**: Default generation logic does not match the CONTEXT.md decision (Decision #4)

### TC-04: Alias values conform to allowed character set
- **Steps**: Extract all alias values, test each against `^[a-zA-Z0-9_-]+$`
- **Expected**: All aliases match the regex (alphanumeric, hyphens, underscores only)
- **Failure means**: Validation is missing or allows special characters that break shell/markdown

---

## B. Boot Scripts

### TC-05: Boot scripts contain `--name` flag in claude launch command
- **Check**: For each `start-*.sh` and `start-*.ps1`, grep for `--name` in the `claude` invocation line
- **Expected**: Every boot script passes `--name "{alias}"` to the claude CLI
- **Failure means**: Session naming was not wired into boot scripts

### TC-06: Boot scripts read alias from config.md
- **Steps**: Read each boot script, verify it parses the alias from config.md (grep for config.md read + alias extraction logic)
- **Expected**: Each script reads its role's alias from the `## Aliases` section
- **Failure means**: Alias is hardcoded or not read from config at all

### TC-07: Boot script falls back to bare role when alias is missing
- **Steps**:
  1. Temporarily remove the `## Aliases` section from config.md
  2. Trace the boot script logic (read the fallback code path)
  3. Verify the script would use the bare role name as `--name` value
  4. Restore config.md: `git checkout -- .squidsquad/config.md`
- **Expected**: Fallback produces `--name "{role}"` (e.g., `--name "skill"`)
- **Failure means**: Missing alias section causes a boot error instead of graceful fallback

### TC-08: Boot banner displays alias
- **Steps**: Read boot script banner section, verify the alias is shown in the ASCII art or startup output
- **Expected**: Banner includes the alias value (not just the bare role)
- **Failure means**: Banner was not updated to show alias

---

## C. Git Commits

### TC-09: Co-Authored-By trailer present in commit format
- **Steps**: Read the git-commit sub-skills:
  - `references/sub-skills/common/git-commit.md`
  - `references/sub-skills/pm-specific/git-commit.md`
  - `references/sub-skills/qa-specific/git-commit.md`
  - `references/sub-skills/dm-specific/git-commit.md`
  - `references/sub-skills/designer-specific/git-commit.md`
- **Expected**: Each contains a `Co-Authored-By:` trailer in its commit message template
- **Failure means**: Git commit sub-skill was not updated

### TC-10: Co-Authored-By format matches spec
- **Steps**: For each git-commit sub-skill, extract the Co-Authored-By line
- **Expected**: Format is `Co-Authored-By: {alias} ({project}-{role}) <noreply@squidsquad>` with appropriate placeholders (e.g., `[ALIAS]`, `[PROJECT]`, `[ROLE]`)
- **Failure means**: Trailer format deviates from the locked decision (CONTEXT.md Decision #2)

### TC-11: Commit prefix stays role-based (not alias-based)
- **Steps**: For each git-commit sub-skill, verify the commit message prefix
- **Expected**: Prefix is `{role}: {description}` (e.g., `skill:`, `pm:`, `qa:`), NOT `{alias}:`
- **Failure means**: Role-based prefix was incorrectly changed to alias-based, breaking pattern matching

---

## D. GH Issue Comments (Discussion Entries)

### TC-12: Discussion protocol includes alias parenthetical
- **Steps**: Read all discussion-protocol sub-skills:
  - `references/sub-skills/common/discussion-protocol.md`
  - `references/sub-skills/pm-specific/discussion-protocol.md`
  - `references/sub-skills/pm-specific/lean-discussion-protocol.md`
  - `references/sub-skills/qa-specific/discussion-protocol.md`
  - `references/sub-skills/dm-specific/discussion-protocol.md`
  - `references/sub-skills/designer-specific/discussion-protocol.md`
- **Expected**: Each shows the format `**{role-alias}** ({alias}): {message}` (e.g., `**skill-lead** (Ralph): message`)
- **Failure means**: Discussion protocol sub-skill was not updated

### TC-13: Role-alias stays as primary bold identifier
- **Steps**: In each discussion-protocol sub-skill, verify the bold identifier is the existing role-alias (e.g., `**skill-lead**`, `**pm/qa**`, `**qa**`)
- **Expected**: The bold role-alias is unchanged; alias appears only in parenthetical
- **Failure means**: Role-alias was replaced instead of augmented, breaking cross-agent pattern matching

---

## E. Status Bar

### TC-14: statusline.sh reads alias from config.md
- **Steps**: Read `references/statusline.sh` (or live `.squidsquad/statusline.sh`), check for config.md alias parsing logic
- **Expected**: Script reads alias from `## Aliases` section for the active role
- **Failure means**: Status bar still uses only the hardcoded role label

### TC-15: Status bar displays alias alongside role label
- **Steps**: In statusline.sh, trace the ROLE_LABEL construction
- **Expected**: Output format includes alias (e.g., `skill (Ralph)` or `Ralph` depending on whether alias differs from role)
- **Failure means**: Alias display was not added to status bar

### TC-16: Status bar falls back to role label when alias equals role
- **Steps**: With default aliases (bare role names), trace statusline.sh logic
- **Expected**: When alias == role, display is unchanged from current behavior (no redundant `skill (skill)`)
- **Failure means**: Redundant display when using default aliases

---

## F. Setup Flow

### TC-17: Setup prompts for alias during agent configuration
- **Steps**: Read SKILL.md setup instructions (Step 2 or Step 3 where config template is generated)
- **Expected**: Setup flow includes an alias prompt for each agent, with default value of bare role name
- **Failure means**: Setup does not offer alias customization

### TC-18: Setup generates Aliases section in config.md
- **Steps**: Read SKILL.md config template generation step
- **Expected**: The generated config.md template includes `## Aliases` section with entries for all configured agents
- **Failure means**: Config template is incomplete

### TC-19: Skipping alias prompt uses defaults
- **Steps**: Verify that the setup flow documents that pressing Enter (accepting default) sets alias to bare role name
- **Expected**: Default behavior produces `- **skill**: skill`, `- **pm**: pm`, etc.
- **Failure means**: Default handling is broken or not documented

---

## G. Custom Alias Propagation

### TC-20: Custom alias in config propagates to git commit trailer
- **Steps**:
  1. In config.md, change skill alias from `skill` to `Ralph`
  2. Trace the git-commit sub-skill: verify `[ALIAS]` placeholder would resolve to `Ralph`
  3. Expected commit: `skill: description\n\nCo-Authored-By: Ralph (SquidSquad-skill) <noreply@squidsquad>`
  4. Restore config.md: `git checkout -- .squidsquad/config.md`
- **Expected**: Co-Authored-By trailer shows `Ralph`
- **Failure means**: Alias placeholder resolution is broken in git-commit sub-skills

### TC-21: Custom alias in config propagates to Discussion comments
- **Steps**:
  1. With alias `Ralph` in config, trace discussion-protocol sub-skill
  2. Expected comment format: `> [YYYY-MM-DD HH:MM] **skill-lead** (Ralph): message`
- **Expected**: Parenthetical shows `Ralph`
- **Failure means**: Alias placeholder resolution is broken in discussion-protocol sub-skills

### TC-22: Custom alias in config propagates to boot script --name
- **Steps**:
  1. With alias `Ralph` in config, trace boot script alias parsing
  2. Expected launch command includes `--name "Ralph"`
- **Expected**: `--name` flag uses the custom alias value
- **Failure means**: Boot script parses alias incorrectly

### TC-23: Custom alias propagates to status bar
- **Steps**: With alias `Ralph` in config, trace statusline.sh
- **Expected**: Status bar shows `Ralph` (or `skill (Ralph)`) instead of bare `skill`
- **Failure means**: Status bar does not pick up custom alias

---

## H. Pattern Matching Safety

### TC-24: QA rejection detection uses role-alias, not custom alias
- **Steps**: Read the dev agent template (Step 3 in `references/sub-skills/roles/dev-agent.md` or composed agent-instructions.md) — find the QA rejection detection logic that checks for `**qa**` or `**pm**` comments
- **Expected**: Pattern matches on `**qa**` and `**pm**` (role-based identifiers), NOT on custom alias values
- **Failure means**: Custom aliases would break cross-agent comment detection

### TC-25: Commit prefix pattern matching unaffected
- **Steps**: Search all sub-skills and role templates for code that parses commit prefixes (e.g., `skill:`, `pm:`, `qa:`)
- **Expected**: All prefix matching uses role names, not aliases. Alias only appears in Co-Authored-By trailer.
- **Failure means**: Alias was incorrectly used in commit prefix, breaking health checks and pattern matching

### TC-26: Agent health check paths use role, not alias
- **Steps**: Read statusline.sh and PM health check logic — verify file paths like `.squidsquad/{role}/current-state` use the role, not the alias
- **Expected**: All file path resolution uses bare role names from `Dev Agents` config, not from `## Aliases`
- **Failure means**: Custom alias breaks file path resolution for health checks

---

## I. Backward Compatibility

### TC-27: Default aliases produce identical commit messages to pre-feature behavior
- **Steps**: With default aliases (bare role names), construct a commit message per the updated git-commit sub-skill
- **Expected**: `skill: description\n\nCo-Authored-By: skill (SquidSquad-skill) <noreply@squidsquad>` — the only difference from pre-feature is the new Co-Authored-By trailer (which is additive, not breaking)
- **Failure means**: Default aliases change existing commit format beyond the intended trailer addition

### TC-28: Default aliases produce identical Discussion format to pre-feature behavior
- **Steps**: With default aliases, construct a Discussion entry per the updated protocol
- **Expected**: `> [YYYY-MM-DD HH:MM] **skill-lead** (skill): message` — the parenthetical `(skill)` is new but the bold role-alias is unchanged
- **Failure means**: Default aliases change existing Discussion format in a breaking way

### TC-29: Existing config.md without Aliases section does not break agent boot
- **Steps**:
  1. Temporarily remove `## Aliases` section from config.md
  2. Verify boot script has fallback logic (TC-07 covers this for boot scripts)
  3. Verify agent CLAUDE.md instructions handle missing alias gracefully
  4. Restore config.md: `git checkout -- .squidsquad/config.md`
- **Expected**: Agent boots normally, uses bare role name as alias
- **Failure means**: Missing Aliases section crashes boot or agent startup

### TC-30: .active-role file still stores bare role name
- **Steps**: Read boot scripts, verify `.squidsquad/.active-role` is written with the role (e.g., `skill`), not the alias
- **Expected**: `.active-role` always contains the bare role string
- **Failure means**: Alias leaked into role file, breaking path resolution for all agents

---

## Test Execution Order

Run in this order to fail fast on structural issues:

1. **TC-01, TC-02, TC-03, TC-04** — Config structure (A section)
2. **TC-05, TC-06, TC-07, TC-08** — Boot scripts (B section)
3. **TC-09, TC-10, TC-11** — Git commits (C section)
4. **TC-12, TC-13** — Discussion protocol (D section)
5. **TC-14, TC-15, TC-16** — Status bar (E section)
6. **TC-17, TC-18, TC-19** — Setup flow (F section)
7. **TC-20, TC-21, TC-22, TC-23** — Custom alias propagation (G section)
8. **TC-24, TC-25, TC-26** — Pattern matching safety (H section)
9. **TC-27, TC-28, TC-29, TC-30** — Backward compatibility (I section)

---

## Pass Criteria

- **All 30 TCs must pass** to mark Issue #29 as Pending Ship
- **TC-24 is a hard gate** — broken QA rejection detection blocks the entire feature
- **TC-11 is a hard gate** — commit prefix must stay role-based
- **TC-30 is a hard gate** — .active-role must stay role-based
- Any TC with a config mutation step (TC-07, TC-20, TC-29) must verify `git checkout` restores clean state after
