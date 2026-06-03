---
description: Compose (regenerate) agent CLAUDE.md and SOUL.md files from sub-skill sources
---

Run the SquidSquad composition engine to regenerate agent templates.

## Usage

- `/squidsquad-compose` — deploy all roles (equivalent to `compose.py deploy-all`)
- `/squidsquad-compose <role>` — deploy a single role (e.g. `/squidsquad-compose skill`)

## Steps

1. **Pre-flight check**: Verify `references/scripts/compose.py` exists. If missing, report error and stop.

2. **Run composition**:
   - Single role: `python references/scripts/compose.py deploy <role>`
   - All roles: `python references/scripts/compose.py deploy-all`

3. **Post-compose validation**: For each deployed role, verify:
   - `.squidsquad/<role>/CLAUDE.md` exists and is non-empty
   - `.squidsquad/<role>/SOUL.md` exists and is non-empty
   - Report any failures clearly

4. **Report results**: Print which roles were composed, line counts, and any validation failures.

## Notes

- SOUL.md customizations are preserved — `compose.py` never overwrites existing SOUL.md files (only seeds on first deploy).
- Vault content (`.squidsquad/vault/`) is untouched.
- This skill is the single entry point for LLM-driven composition. Python scripts (`wizard.py`, `add_role.py`) continue to import `compose.py` directly for mechanical paths.
- Agents in sibling clones get updated CLAUDE.md on their next `git pull` (start of each cycle).
