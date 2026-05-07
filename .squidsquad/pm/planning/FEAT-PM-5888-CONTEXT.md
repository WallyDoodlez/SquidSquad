# FEAT-PM-5888 Context — /squidsquad-compose Skill

## Scope

Create `/squidsquad-compose` as a first-class Claude Code skill wrapping compose.py. All composition flows route through this skill. Scripts (wizard.py, add_role.py) become scaffolding-only — they lose all compose.py calls.

## Locked Decisions (human decided)

- **Always validate**: Every compose runs mechanical validation (files exist, non-empty, markers intact). Creative validation (#5868) added later through this same skill.
- **Scripts scaffold, skill composes**: wizard.py and add_role.py lose ALL compose.py calls. They do scaffolding only (directories, config, clones). The compose skill is the ONLY composition entry point.
- **SOUL.md seeding moves to compose.py**: `deploy_role()` handles SOUL.md seeding (reads .install-spec.json and .repo-scan.json for project context). Wizard no longer seeds SOUL.md. Compose owns all instructional content.
- **Conversation-based error reporting**: Compose skill prints clear success/fail markers. Calling skills read the output.
- **Remove agent-compose dead code**: Delete `agent_compose()`, `_is_agent_compose_enabled()`, `_extract_code_blocks()`, `_extract_markers()`, `_generate_cqs_from_sources()`, the config flag, and all references. Never enabled, redundant since compose skill runs inside Claude.
- **Remove boot_role dead code**: Delete `boot_role()` function, `boot`/`boot-all` CLI commands, and all call sites. No-op since #4966.
- **Remove --boot from add_role.py**: The add-role skill orchestrates boot after compose succeeds. add_role.py has zero boot awareness.
- **CI setup-yes becomes two-step**: scaffold then compose. Post-setup summary updated to say "Next: run compose."

## Orchestration After This Ships

- `/squidsquad-setup` → wizard.py (scaffold) → `/squidsquad-compose` (compose + validate)
- `/squidsquad-add-role` → add_role.py (scaffold) → `/squidsquad-compose` (compose + validate)
- `/squidsquad-upgrade` → `/squidsquad-compose` (compose + validate)
- PM post-merge recompose → `/squidsquad-compose`

## Dev Discretion (dev agent can choose)

- Internal structure of the compose skill slash command
- How compose.py's deploy_role reads .install-spec.json for SOUL.md seeding
- How mechanical validation is structured in compose.py (separate function vs inline)
- Whether to keep agent-compose config field as deprecated or remove entirely from config.py FIELD_MAP

## Side Effect Mitigations (required)

- SOUL.md seeding in deploy_role must read .install-spec.json and .repo-scan.json — verify files exist before reading, skip seeding gracefully if missing (first-ever compose before scaffold runs repo scan)
- generate_local_config must still run — compose.py deploy-all already calls it. Skill must always run deploy-all, not per-role deploy.
- Stale squidsquad-upgrade.md MUST be rewritten atomically with this change
- WIZARD.md runbook references to compose.py must be updated
- Post-merge recompose sub-skill updated to reference skill, not inline bash
- All prohibitions sub-skills updated to mention both compose.py and /squidsquad-compose
- cmd_setup_yes prints "Scaffolding complete. Next: run /squidsquad-compose" — not boot instructions
- add_role dry-run messages updated to reflect no-compose behavior
- ~15 tests across test_wizard.py, test_add_role.py, test_wizard_runbook.py need updates

## Upgrade Path (required)

- New slash command arrives via git pull into .claude/commands/
- Old wizard.py (with embedded compose) still works until new code is pulled — graceful degradation
- No config schema changes. No data migration.
- Atomic delivery: wizard.py + add_role.py + compose.py + tests + SKILL.md + upgrade.md + compose.md all ship together

## Out of Scope

- Event contract generation (#5868 — extends this skill later)
- Creative/LLM validation (#5868)
- Cross-agent event contract validation (#5868)
- Interactive fix loop on validation failure (#5868)
