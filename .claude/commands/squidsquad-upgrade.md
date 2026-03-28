Run the SquidSquad upgrade flow for this project.

1. Read `.squidsquad/config.md` and extract `SquidSquad Version` and `Tracker Schema`.
2. Read the current skill version from `SKILL.md` frontmatter (`version:` field) and current schema from the Schema Changelog section.
3. Compare installed vs current for both.
4. If both match, tell the user the installation is already up to date and stop.
5. If the skill version differs, regenerate all scaffolding files (boot scripts, CLAUDE.md templates, `.claude/settings.json` permissions+hook) using the latest templates from `SKILL.md` and `references/agent-instructions.md`. Do not touch tracker files or project config values.
6. If the tracker schema version differs, run any schema migrations documented in the `Schema Changelog` section of `SKILL.md` for the version gap.
7. Update `SquidSquad Version` and `Tracker Schema` in `.squidsquad/config.md` to the current values.
8. Run:
   ```bash
   git add .squidsquad/ .claude/
   git commit -m "squidsquad: upgrade to [VERSION]"
   git push
   ```
9. Tell the user what was upgraded and whether any schema migrations ran.
