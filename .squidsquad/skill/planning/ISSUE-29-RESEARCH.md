# Issue #29 — Agent Name Aliases: Phase 1 Research

## 1. Current Agent Identification

### 1.1 Boot Scripts (`start-*.sh` / `start-*.ps1`)

Each agent has a pair of boot scripts (bash + PowerShell). Current identification pattern:

- **Banner**: Hardcoded role label in ASCII art: `S Q U I D S Q U A D   v${V:-?}  —  skill` (or `PM / QA`, `DM`)
- **Active role file**: Writes bare role string to `.squidsquad/.active-role` (e.g., `"skill"`, `"pm"`, `"dm"`)
- **System prompt**: Passes `SQUIDSQUAD_ROLE=[role]` via `--append-system-prompt`
- **Session launch**: `claude --dangerously-skip-permissions --append-system-prompt "SQUIDSQUAD_ROLE=[role]" "start the loop"`
- **No `--name` flag** is currently used anywhere

Files: `.squidsquad/start-skill.sh`, `.squidsquad/start-skill.ps1`, `.squidsquad/start-pm.sh`, `.squidsquad/start-pm.ps1`, `.squidsquad/start-dm.sh`, `.squidsquad/start-dm.ps1`

Template in SKILL.md (Step 5) mirrors this pattern with `[ROLE]` placeholder.

### 1.2 `config.md`

Current agent-related fields:
```markdown
## Agents
- **Dev Agents**: skill
- **PM/QA**: always present

## Project
- **Name**: SquidSquad
- **Repo**: github.com/WallyDoodlez/SquidSquad
```

No alias/name fields exist. The `Project > Name` field exists and can be used for default alias generation (`{project-name}-{role}`).

### 1.3 Discussion Protocol (GitHub Issue Comments)

Each role has a hardcoded Discussion alias used in GH Issue comments:

| Role | Discussion Alias | Sub-skill Source |
|------|-----------------|------------------|
| Dev agent | `**[ROLE]-lead**` (e.g., `**skill-lead**`) | `references/sub-skills/common/discussion-protocol.md` |
| PM (no QA) | `**pm/qa**` | `references/sub-skills/pm-specific/discussion-protocol.md` |
| PM (lean, QA present) | `**pm**` | `references/sub-skills/pm-specific/lean-discussion-protocol.md` |
| QA | `**qa**` | `references/sub-skills/qa-specific/discussion-protocol.md` |
| DM | `**dm**` | `references/sub-skills/dm-specific/discussion-protocol.md` |
| Designer | `**designer**` | `references/sub-skills/designer-specific/discussion-protocol.md` |

Format: `> [YYYY-MM-DD HH:MM] **{alias}**: {message}`

These aliases are also hardcoded in role-specific CLAUDE.md templates (example entries, Step 2/3 comment templates).

### 1.4 Git Commit Messages

Role-prefixed format: `{role}: {description}`

| Role | Prefix | Sub-skill Source |
|------|--------|------------------|
| Dev agent | `skill:`, `be:`, etc. | `references/sub-skills/common/git-commit.md` — uses `[ROLE]:` |
| PM | `pm:` | `references/sub-skills/pm-specific/git-commit.md` |
| QA | `qa:` | `references/sub-skills/qa-specific/git-commit.md` |
| DM | `dm:` | `references/sub-skills/dm-specific/git-commit.md` |
| Designer | `designer:` | `references/sub-skills/designer-specific/git-commit.md` |
| Version bump | `chore:` | PM/DM version bump step |

Convention documented in `vault/areas/code-conventions.md`: "Commit messages: Role-prefixed (`skill: ...`, `pm: ...`, `dm: ...`)"

### 1.5 Status Bar (`statusline.sh`)

- Reads role from `.squidsquad/.active-role`
- Maps role to `ROLE_LABEL`: `pm` -> `PM`, `qa` -> `QA`, `dm` -> `DM`, else uses raw role string
- Displays: `🦑 ${ROLE_LABEL} v${VERSION} │ ...`
- No alias concept exists — only role-based labels

### 1.6 Agent Health Check (PM Statusline)

PM reads agent health by checking `current-state` file mod times for each agent listed in `Dev Agents` config. Uses role names to find paths: `.squidsquad/{role}/current-state`.

### 1.7 PR Flow (Branch Names)

When PR flow is enabled: `squidsquad/feat-[ROLE]-NNN` or `squidsquad/bug-[ROLE]-NNN`

---

## 2. Claude Code Session Naming

### 2.1 The `--name` Flag

Claude Code CLI supports:
```
-n, --name <name>    Set a display name for this session (shown in /resume and terminal title)
```

This is the key mechanism. The name is:
- Shown in `/resume` session picker (Claude Code remote session list)
- Used as terminal title
- Persistent across session restarts

### 2.2 Integration with Boot Scripts

Current launch command:
```bash
claude --dangerously-skip-permissions --append-system-prompt "SQUIDSQUAD_ROLE=skill" "start the loop"
```

With alias:
```bash
claude --dangerously-skip-permissions --name "squidsquad-skill" --append-system-prompt "SQUIDSQUAD_ROLE=skill" "start the loop"
```

### 2.3 Relationship to #9 and FEAT-SKILL-061

- **Issue #9** ("Named sessions for Claude Code remote") — CLOSED, migrated from FEAT-SKILL-061
- **FEAT-SKILL-061** — Status: Pending. Describes session naming with hardcoded patterns like `SquidSquad PM — SquidSquad`
- **FEAT-SKILL-036** — Consolidated into 061. Wanted terminal title via first message line

Issue #29 supersedes both #9 and FEAT-SKILL-061, since the alias becomes the session name. Human confirmed in Discussion: "the alias becomes the Claude Code SESSION NAME visible in remote control."

---

## 3. Storage Design

### Option A: Centralized in `config.md`

Add an `## Aliases` section:
```markdown
## Aliases

- **skill**: squidsquad-skill
- **pm**: squidsquad-pm
- **dm**: squidsquad-dm
```

**Pros:**
- Single source of truth — all agents read config.md already
- Easy to edit (human changes one file)
- Visible in one place for multi-agent overview
- Boot scripts already read config.md for version number

**Cons:**
- Merge conflicts if multiple agents write to config.md simultaneously (but agents don't write aliases — human or setup does)

### Option B: Per-agent config (`.squidsquad/{role}/config.md`)

**Pros:**
- No cross-agent file contention
- Agent reads only its own config

**Cons:**
- New file concept — nothing like this exists today
- Harder to see all aliases at a glance
- Boot scripts would need to read a new file

### Option C: Boot script arguments only

Pass alias as a variable in the boot script itself.

**Pros:**
- Simplest — no new config structure

**Cons:**
- Not readable by agents at runtime (system prompt doesn't contain it)
- Would need to also pass via `--append-system-prompt` or store in a file

### Recommendation: Option A (centralized in `config.md`)

Config.md is already the canonical config. Aliases are set at setup time or by human edit, not by agents during runtime. This avoids new file concepts. Boot scripts already parse config.md for version; they can parse alias the same way. Agents can read their own alias from config.md at boot.

### Alias Availability at Runtime

The alias needs to be available to the agent at runtime for Discussion comments and commit messages. Two sub-options:

**A1. Agent reads config.md**: Already done every cycle (pull latest, read config). Agent finds its own alias by matching its role.

**A2. Pass alias in system prompt**: `--append-system-prompt "SQUIDSQUAD_ROLE=skill SQUIDSQUAD_ALIAS=squidsquad-skill"`. Avoids repeated file reads but is redundant with config.md.

**Recommendation**: A1. Agents already read config.md. Adding `SQUIDSQUAD_ALIAS=` to the system prompt is a nice-to-have for quick access but not strictly necessary. Boot scripts should populate both (system prompt for immediate access, config.md for persistence).

---

## 4. Impact Analysis

### 4.1 Boot Scripts

**Changes needed:**
- Read alias from config.md (or use default `{project-name}-{role}`)
- Add `--name "{alias}"` to the `claude` launch command
- Update banner to show alias instead of bare role
- Optionally pass alias in system prompt

**Template changes** (SKILL.md Step 5):
- `.sh` and `.ps1` templates both need updating
- All 6 current boot scripts need regeneration on upgrade

### 4.2 Discussion Comments (GH Issue Comments)

**Current**: `> [2026-04-04 14:30] **skill-lead**: Fixed.`
**With alias**: `> [2026-04-04 14:30] **squidsquad-skill**: Fixed.`

**Decision needed**: Should Discussion alias change to the custom alias?

**Recommendation**: Yes, but keep the role machine-parseable. Human confirmed: "the alias should also be used in... GitHub Issue comments (Discussion signature)." The alias replaces the current hardcoded Discussion alias.

**Sub-skill changes**: All 6 discussion-protocol sub-skills need updating to use alias instead of hardcoded strings. The `[ROLE]-lead` pattern in common/discussion-protocol.md becomes `[ALIAS]`. PM-specific becomes `[ALIAS]` instead of `pm/qa` or `pm`.

**Pattern recognition concern**: The dev agent's Step 3 checks for comments from `**qa**` or `**pm**` after its last `**[ROLE]-lead**` comment to detect QA rejections. If aliases change, this pattern-matching logic must use the alias. Agents would need to know OTHER agents' aliases too (or pattern-match differently).

This is the **highest-risk area** of the feature. Current cross-agent pattern matching relies on known, fixed alias strings.

### 4.3 Commit Messages

**Current**: `skill: fix #29 — add alias support`
**With alias**: `squidsquad-skill: fix #29 — add alias support`

**Decision needed**: Human confirmed alias should be used in commit prefixes.

**Sub-skill changes**: All 5 git-commit sub-skills need updating. The `[ROLE]:` pattern becomes `[ALIAS]:`.

**Impact**: Commit-based health checks (FEAT-SKILL-006) use commit prefix to identify which agent made a commit. If prefix changes, health check grep patterns must change too. Currently health check in statusline.sh is file-mtime-based (not git-log-based), so this may be lower risk than expected.

### 4.4 Status Bar

**Current**: `🦑 skill v0.10.0 │ ...`
**With alias**: `🦑 squidsquad-skill v0.10.0 │ ...`

**Changes**: `statusline.sh` ROLE_LABEL logic should read alias from config.md instead of hardcoded mapping. The `.active-role` file still stores the bare role (needed for path resolution), but display uses alias.

### 4.5 GH Issue Comments (Agent Signing)

Same as 4.2 — the Discussion comment format IS the GH Issue comment format.

### 4.6 Working State / Iteration Logs

Working state (`working-state.md`) references task numbers, not agent names. No change needed.

Iteration logs use role in filename path (`.squidsquad/{role}/iterations/`). No change needed — paths stay role-based.

### 4.7 Git Config (user.name)

Human requested: "git config user.name per agent clone." This means each agent's git clone should have `git config user.name "{alias}"` set, so commits are attributed to the alias in git history.

**Change**: Boot scripts should run `git config user.name "{alias}"` at startup.

### 4.8 Summary of Files Requiring Changes

| File/Component | Change Type |
|----------------|-------------|
| `config.md` (template + live) | Add `## Aliases` section |
| SKILL.md Step 3 (config template) | Add aliases to template |
| SKILL.md Step 5 (boot script template) | Add `--name`, alias logic |
| `start-*.sh` (6 files, live) | Add `--name`, read alias |
| `start-*.ps1` (6 files, live) | Add `--name`, read alias |
| `statusline.sh` (live + reference) | Read alias for display |
| `references/sub-skills/common/discussion-protocol.md` | Use `[ALIAS]` |
| `references/sub-skills/pm-specific/discussion-protocol.md` | Use `[ALIAS]` |
| `references/sub-skills/pm-specific/lean-discussion-protocol.md` | Use `[ALIAS]` |
| `references/sub-skills/qa-specific/discussion-protocol.md` | Use `[ALIAS]` |
| `references/sub-skills/dm-specific/discussion-protocol.md` | Use `[ALIAS]` |
| `references/sub-skills/designer-specific/discussion-protocol.md` | Use `[ALIAS]` |
| `references/sub-skills/common/git-commit.md` | Use `[ALIAS]` |
| `references/sub-skills/pm-specific/git-commit.md` | Use `[ALIAS]` |
| `references/sub-skills/qa-specific/git-commit.md` | Use `[ALIAS]` |
| `references/sub-skills/dm-specific/git-commit.md` | Use `[ALIAS]` |
| `references/sub-skills/designer-specific/git-commit.md` | Use `[ALIAS]` |
| `references/sub-skills/manifest.md` | Add `[ALIAS]` placeholder docs |
| `roles/dev-agent.md` (entry template) | QA-rejection detection pattern |
| `roles/pm-agent.md` | Cross-agent pattern matching |
| `vault/areas/code-conventions.md` | Update commit prefix convention |
| Setup flow (SKILL.md Step 2) | Add alias prompt |
| Upgrade flow | Migrate existing installs |

---

## 5. Cross-Project Identification

### Current Problem

Two repos both running SquidSquad:
- Both have a `skill` agent with commit prefix `skill:`
- Both have a `pm` agent signing as `**pm/qa**`
- In Claude Code remote, both sessions show generic IDs
- Git history shows `skill:` commits — no way to tell which project

### With Aliases (Default)

- Repo "SquidSquad": `squidsquad-skill`, `squidsquad-pm`
- Repo "MyApp": `myapp-skill`, `myapp-pm`
- Claude Code remote: sessions named `squidsquad-skill`, `myapp-skill` — instantly distinguishable
- Git commits: `squidsquad-skill: ...` vs `myapp-skill: ...`
- GH Issue comments: `**squidsquad-skill**:` vs `**myapp-skill**:`

### Default Format

`{project-name}-{role}` where `project-name` is from `config.md > Project > Name`, lowercased and kebab-cased.

Examples:
- Project "SquidSquad", role "skill" -> `squidsquad-skill`
- Project "My Cool App", role "be" -> `my-cool-app-be`
- Project "MyApp", role "pm" -> `myapp-pm`

---

## 6. Edge Cases

### 6.1 Duplicate Aliases

**Scenario**: Two agents assigned the same alias (e.g., both "Ralph").
**Risk**: Discussion comments indistinguishable; commit prefix ambiguous; session names collide.
**Mitigation**: Setup validates uniqueness across all agents in config.md. Reject duplicates with error message.

### 6.2 Special Characters in Alias

**Scenario**: Alias contains spaces, quotes, pipe characters, markdown formatting chars.
**Risk**: Breaks git commit messages (`git commit -m "my agent: ..."`), Discussion markdown (`**my|agent**: ...`), shell arguments.
**Mitigation**: Restrict aliases to `[a-zA-Z0-9_-]` (alphanumeric, hyphens, underscores). Validate at setup time. Reject others with a clear error.

### 6.3 Alias Changed After Agents Running

**Scenario**: Human edits config.md aliases while agents are actively running.
**Risk**: Agent reads new alias next cycle — Discussion entries switch mid-conversation. Old entries signed with old alias, new entries with new alias.
**Mitigation**: This is acceptable behavior. Agents read config.md every cycle, so they pick up changes naturally. Old Discussion entries are immutable (append-only). The change is visible in the Discussion history as a natural transition. No special handling needed beyond documenting the behavior.

### 6.4 Old Discussion Entries After Rename

**Scenario**: Agent was `squidsquad-skill`, renamed to `ralph`. Old GH Issue comments still say `**squidsquad-skill**:`.
**Risk**: Cross-agent pattern matching may not recognize the old alias. For example, dev agent checks for `**qa**` or `**pm**` comments — if QA was renamed, the pattern breaks.
**Mitigation**:
1. Pattern matching should use current aliases from config.md, not hardcoded strings
2. For historical entries, the role is still identifiable from context
3. Document that renaming mid-stream creates a visible alias transition but does not break functionality
4. Consider: agents could match on both current alias AND bare role as fallback

### 6.5 Upgrade Path (Existing Installs)

**Scenario**: Existing SquidSquad install with no aliases in config.md.
**Risk**: Agents boot but find no alias — need a default.
**Mitigation**: If no `## Aliases` section in config.md, auto-generate defaults using `{project-name}-{role}` pattern. Upgrade flow should add the section. Boot scripts should have a fallback: if alias not found, use bare role (backward compatible).

### 6.6 Very Long Aliases

**Scenario**: Human sets alias "my-super-long-project-name-for-the-skill-dev-agent".
**Risk**: Status bar truncation, commit messages get long.
**Mitigation**: Setup validates max length (suggest 30 chars). Warn but don't block — human can override.

### 6.7 Alias Collision with Git Conventional Commits

**Scenario**: Alias "fix" or "feat" could confuse tools that parse conventional commit messages.
**Risk**: Low — SquidSquad uses its own commit prefix convention, not conventional commits.
**Mitigation**: Document reserved words to avoid. Not a hard block.

---

## 7. Key Design Decisions Needed (Phase 2 Questions)

1. **Should Discussion alias fully replace role-based signing?** Or should it be `**{alias} ({role})**`? The human's GH comment says "the alias should also be used in... Discussion signature" — suggests full replacement.

2. **Cross-agent pattern matching**: How should agents identify each other's comments? Options:
   - a. Read all aliases from config.md and match against those
   - b. Match on role substring (e.g., any comment containing the role name)
   - c. Use a structured comment format with parseable role metadata

3. **Should `--name` and `SQUIDSQUAD_ALIAS=` both be set?** Redundant but convenient. Boot script can set `--name` for Claude Code session list, and `SQUIDSQUAD_ALIAS=` in system prompt for immediate runtime access.

4. **git config user.name**: Should it be set per-clone at boot time? Human requested this. This makes git blame show the alias.

5. **PR branch names**: Should they use alias? Currently `squidsquad/feat-[ROLE]-NNN`. With alias: `squidsquad/feat-[ALIAS]-NNN`? Or keep role-based (simpler path resolution)?

6. **Consolidation with #9 and FEAT-SKILL-061**: These should be closed as superseded by #29 once #29 ships.

---

## 8. Recommended Implementation Approach

### Phase 1: Config + Boot Scripts (Core)
- Add `## Aliases` section to config.md template and setup flow
- Setup prompts for alias per agent, defaults to `{project-name}-{role}`
- Boot scripts read alias, pass `--name "{alias}"` to claude CLI
- Upgrade flow adds aliases section to existing config.md

### Phase 2: Discussion + Commits (Agent Behavior)
- Update all discussion-protocol sub-skills to use `[ALIAS]`
- Update all git-commit sub-skills to use `[ALIAS]`
- Add `[ALIAS]` to manifest.md placeholder table
- Recompose agent templates
- Update cross-agent pattern matching (QA rejection detection, etc.)

### Phase 3: Status Bar + Polish
- Update statusline.sh to read alias from config.md
- Add `git config user.name` to boot scripts
- Update code-conventions vault note
- Close #9 and FEAT-SKILL-061

---

## 9. Risk Assessment

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| Cross-agent pattern matching breaks | High | Medium | Phase 2 must update all matchers to use config aliases |
| Existing Discussion entries unrecognized after rename | Medium | Low | Fallback to role-based matching |
| Boot script alias parsing fails | Low | Low | Fallback to bare role |
| Merge conflicts in config.md | Low | Low | Aliases set once at setup, rarely changed |
| Special chars in alias break shell/markdown | Medium | Medium | Validate at setup time |
