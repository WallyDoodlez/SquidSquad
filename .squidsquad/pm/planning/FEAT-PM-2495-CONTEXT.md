# FEAT-PM-2495 Context — Rewrite /squidsquad-upgrade

## Scope

Full rewrite of upgrade instructions in SKILL.md (lines 326–379) and .claude/commands/squidsquad-upgrade.md. Replace obsolete parallel-subagent fan-out with compose.py-based flow. Add config v1→v2 schema patching. Both files updated atomically.

## Locked Decisions (human decided)

- **Architecture Version**: Set to 2 in config.md after patching
- **Label sync**: Include wizard.py ensure-labels as an upgrade step (idempotent, catches new labels)
- **Tracker Schema check**: Drop entirely — field doesn't exist, tracker is always github-issues
- **Config patching**: Add missing v2 sections with defaults, do NOT delete existing v1 sections (agents still read them via config.py)

## Dev Discretion (dev agent can choose)

- Exact prose wording of the upgrade instructions
- How to structure the config-patching logic (inline prose steps vs helper script)
- Order of upgrade steps (version check → deploy → config patch → labels → commit)
- How to present the no-install-spec fallback path

## Side Effect Mitigations (required)

- SOUL.md must never be touched by upgrade (compose.py already enforces this — document the guarantee explicitly)
- Vault content must be preserved (upgrade does not touch .squidsquad/vault/)
- Config v1 sections must NOT be deleted — only add v2 sections alongside
- Both SKILL.md and squidsquad-upgrade.md must agree — update atomically in one commit
- Clone isolation: note that agents get new CLAUDE.md on next git pull, not immediately
- No-install-spec path: derive agent list from config.md Dev Agents field if .install-spec.json absent

## Upgrade Path (required)

- This IS the upgrade path — meta-upgrade is just git pull (SKILL.md and skill file are hand-maintained, not generated)

## Out of Scope

- State branch migration (#3664 — separate concern, already shipped)
- Lifecycle rewrite (#3807 — separate concern, already shipped)
- Writing new scripts — all mechanical operations already exist (compose.py, wizard.py, config.py)
- Changing compose.py or wizard.py behavior
