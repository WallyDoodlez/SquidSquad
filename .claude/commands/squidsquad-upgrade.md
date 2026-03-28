Run the SquidSquad upgrade using parallel agents.

## Step 1 — Detect Version Gap

Read `.squidsquad/config.md`:
- Extract `SquidSquad Version` (installed)
- Extract `Tracker Schema` (installed)

Read `SKILL.md`:
- Extract `version:` from frontmatter (current)
- Extract current schema version from the `Schema Changelog` section

If both match, tell the user the installation is already up to date and stop.

## Step 2 — Read Active Roles

Read the `Agents` section of `.squidsquad/config.md` to get the list of active dev agent role names.

## Step 3 — Fan Out Agents in Parallel

If the **skill version** differs, spawn these agents **simultaneously**:

- **One agent per dev role** — regenerate `[role]/CLAUDE.md`, `start-[role].sh`, `start-[role].ps1` using the latest Dev Agent template from `references/agent-instructions.md`, substituting `[ROLE]`, `[ROLE_UPPER]`, `[ROLE_TEST_CMD]`, `[OTHER_ROLES]`, and `[INTERVAL]` from `config.md`

- **One agent for PM/QA** — regenerate `pm/CLAUDE.md`, `start-pm.sh`, `start-pm.ps1` using the PM/QA template from `references/agent-instructions.md`, substituting `[ACTIVE_AGENTS]` and `[INTERVAL]` from `config.md`

- **One agent for settings** — update `.claude/settings.json`: ensure `permissions.allow` contains the required entries (`Edit(.squidsquad/**)`, `Write(.squidsquad/**)`, git commands) and the `SessionStart` hook is present and up to date. Merge — never overwrite unrelated entries.

If the **tracker schema** differs, additionally spawn **one agent per tracker file** that needs migration, using the migration instructions in the `Schema Changelog` section of `SKILL.md`.

Each agent must:
- Only write the files assigned to it
- Not commit — the orchestrator handles that

## Step 4 — Wait and Validate

Wait for all agents to complete. Spot-check that each expected file was actually updated.

## Step 5 — Update Version in config.md

Update `.squidsquad/config.md`:
- Set `SquidSquad Version` to the current skill version
- Set `Tracker Schema` to the current schema version

## Step 6 — Commit and Push

```bash
git add .squidsquad/ .claude/
git commit -m "squidsquad: upgrade to [VERSION]"
git push
```

## Step 7 — Report

Tell the user:
- Which version was upgraded from → to
- Which files were regenerated (list per agent)
- Whether any schema migrations ran
- Whether any failures occurred
