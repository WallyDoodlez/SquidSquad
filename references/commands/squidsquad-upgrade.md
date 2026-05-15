Run the SquidSquad upgrade flow for this project.

1. Read `.squidsquad/config.md` and extract `SquidSquad Version` and `Architecture Version`.
2. Read the current skill version from `SKILL.md` frontmatter (`version:` field).
3. If both versions match, tell the user the installation is already up to date and stop.
4. Read `.squidsquad/.install-spec.json` if it exists. If absent, derive the agent list from the `Dev Agents` field in `config.md` — the upgrade works without it.
5. Regenerate all agent templates via the compose skill:
   ```
   /squidsquad-compose
   ```
   This runs `compose.py deploy-all` + `compose.py all` (reference copy) with post-compose validation. SOUL.md customizations are preserved — compose.py never overwrites existing SOUL.md files. Vault content (`.squidsquad/vault/`) is untouched.
6. Patch config schema if `Architecture Version` is `1` or absent. Add missing v2 sections with defaults (Preset, Tools, Loop, Flags, Git Branches, Forge Backend, Model Routing). Do NOT delete existing v1 sections — only add alongside. After patching, set `Architecture Version` to `2`.
7. Sync GitHub Issue labels (idempotent):
   ```bash
   python references/scripts/wizard.py ensure-labels
   ```
8. Update `SquidSquad Version` in `.squidsquad/config.md` to the current skill version.
9. Commit and push:
   ```bash
   git add .squidsquad/
   git commit -m "squidsquad: upgrade to [VERSION]"
   git push
   ```
   Agents in sibling clones get updated CLAUDE.md on their next git pull (start of each cycle).
10. Tell the user what was upgraded: version change, templates regenerated, config schema version, new sections added, label sync result, any failures.
