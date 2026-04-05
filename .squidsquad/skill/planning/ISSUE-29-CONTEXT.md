# Issue #29 Context — Agent Name Aliases

## Locked Decisions

### 1. Alias Is Attribution, Not Replacement
**Decision**: The alias appears as co-author attribution alongside the role name. Role names stay primary for all parsing and pattern-matching. Alias adds human-readable identity.
**Rationale**: Human wants it like Claude's `Co-Authored-By` pattern in commits — indicating who (which agent) co-worked on this.

### 2. Format
**Decision**:
- **Git commits**: `{role}: {description}\n\nCo-Authored-By: {alias} ({project}-{role}) <noreply@squidsquad>`
- **GH Issue comments**: `> **{role-alias}** ({alias}): {message}` (e.g., `> **skill-lead** (Ralph): Fixed bug`)
- **Session name**: `--name {alias}` in boot script
- **Status bar**: Show alias alongside role label
- **Boot banner**: Show alias in ASCII art

### 3. Storage: config.md Aliases Section
**Decision**: Centralized in config.md:
```markdown
## Aliases
- **skill**: skill
- **pm**: pm
- **qa**: qa
- **dm**: dm
- **designer**: designer
```
Agents read their alias from config on boot and each cycle. Boot scripts parse it for `--name` flag.

### 4. Default: Just {role}
**Decision**: Default alias is the bare role name (`skill`, `pm`, `qa`, `dm`, `designer`). Users can customize during setup or later by editing config.md. No project prefix by default.

### 5. Consolidates #9 and FEAT-SKILL-061
**Decision**: Close #9 (Named sessions for Claude Code remote) and #61 (Named sessions) as covered by #29. Session naming via `--name` flag is included in this feature.

### 6. One Shot Delivery
**Decision**: Ship all changes at once. Scope is manageable: config, boot scripts, git-commit sub-skills, Discussion protocol sub-skills, status bar. No pattern-matching changes needed since role stays primary.

## Changes Required

### Boot Scripts (6 files)
- Parse alias from config.md
- Add `--name {alias}` to `claude` launch command
- Update banner to show alias

### Config (1 file)
- Add `## Aliases` section with default values
- Setup flow prompts for custom names

### Git Commit Sub-skills (5 files)
- common/git-commit.md + all role-specific: add `Co-Authored-By: {alias}` trailer

### Discussion Protocol Sub-skills (6 files)
- All role discussion-protocols: add `({alias})` parenthetical after role

### Status Bar (1 file)
- statusline.sh: read alias, display alongside role

### Setup Flow (SKILL.md)
- Add alias prompt during setup
- Default to bare role name

### Template Composition
- Regenerate agent-instructions.md after sub-skill updates

## Side Effects & Mitigations
- **Pattern matching safe**: Role names unchanged in comment signatures — QA rejection detection still works
- **Git history consistent**: Commit prefix stays `{role}:` — alias only in Co-Authored-By trailer
- **Backward compatible**: Default alias = role name, so existing installs look identical until customized

## Dev Discretion Areas
- Exact parsing logic for reading alias from config.md in bash
- Whether boot scripts cache the alias or re-read each boot
- Co-Authored-By email format (noreply@squidsquad or omit)
