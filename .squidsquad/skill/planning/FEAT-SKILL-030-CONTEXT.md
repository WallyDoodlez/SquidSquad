# FEAT-SKILL-030 Context — Sub-skill Architecture

## Scope

Break the monolithic SKILL.md (~1100 lines) and agent-instructions.md into composable sub-skill source files under `references/sub-skills/`. A composition engine assembles these into the monolithic template files agents already read. No change to the agent boot path — agents continue reading one composed template file via their CLAUDE.md bootstrapper.

**In scope (Phase A only):**
- Sub-skill source file structure in `references/sub-skills/`
- Composition engine (runs during setup and upgrade)
- Template generation from sub-skill sources with section markers
- `agent-instructions.md` becomes a generated artifact
- `Architecture Version` field in config.md
- Diff-verified migration from monolithic to sub-skill
- Upgrade path via `/squidsquad-upgrade`

**Effectively unchanged (Phase B):**
- Agent tool continues to be used for Research/Test Plan subagents (no switch to `--print`)

## Locked Decisions (human decided)

- **Build-time composition**: Templates are composed at setup/upgrade time, not at agent boot. Agents read one pre-composed file as today.
- **Concatenation with section markers**: Composed templates use `<!-- sub-skill: [name] -->` delimiters to preserve sub-skill boundaries for debugging/maintenance.
- **Source location**: Sub-skill source files live in `references/sub-skills/` (common/, roles/, pm-specific/, skill-specific/, dm-specific/).
- **agent-instructions.md becomes generated**: Kept as auto-composed artifact with "DO NOT EDIT" header. Sub-skill files are the true source of truth.
- **Separate Architecture Version**: New `Architecture Version` field in config.md. Schema versions track tracker format; architecture versions track template generation changes.
- **Keep Agent tool**: No switch to `--print` mode. Current in-process subagent pattern is sufficient. Revisit `--print` for headless/CI use cases later.
- **Diff-verified composition testing**: Composed templates are diffed against current monolithic templates before swapping. Differences must be intentional and documented. No scripted test harness needed.
- **Phase C removed from scope**: Current CLI conversation flow (AskUserQuestion) is the interaction layer. GitHub Issues integration is a separate future feature after sub-skills are established.

## Dev Discretion (dev agent can choose)

- Exact section marker format (e.g., `<!-- sub-skill: tracker-protocol -->` vs `<!-- begin: tracker-protocol -->`)
- Internal composition order within common sub-skills
- How placeholder substitution integrates with composition (compose-then-substitute vs interleaved)
- Whether to keep `references/agent-instructions.md` as a single composed file or split into per-role composed files
- File naming conventions within `references/sub-skills/`

## Side Effect Mitigations (required)

- Composed templates must be byte-equivalent to current monolithic templates (excluding intentional changes and section markers)
- Upgrade must detect non-bootstrapper CLAUDE.md files (>50 lines or containing `## The Ralph Loop`) and warn/backup before overwriting
- Composition must handle all team shapes: single dev agent, multi-dev, DM present vs absent
- All sub-skill source files must exist before composition runs — fail early with clear error if any missing
- Template size after composition must not exceed current template sizes (PM ~600 lines is the largest)

## Upgrade Path (required)

- `/squidsquad-upgrade` detects monolithic vs sub-skill install by checking for `references/sub-skills/` directory
- Monolithic → sub-skill: create sub-skill source files, compose templates, verify via diff, swap atomically
- Sub-skill → sub-skill: regenerate composed templates from updated sources
- Add `Architecture Version: 1` to config.md during migration
- Single commit, single push — git ensures atomic delivery to all agents
- Existing templates continue working if user doesn't upgrade (graceful degradation)

## Out of Scope

- **Phase C (interaction layer)**: GitHub Issues integration as discussion surface — separate future feature
- **Phase D (API/SDK migration)**: Claude API direct usage — separate future feature
- **`--print` mode execution**: Deferred — revisit for headless/CI use cases
- **User-configurable sub-skills**: Future work (FEAT-SKILL-054 covers workflow editing)
- **Web UI (FEAT-SKILL-020)**: Not part of this feature
- **VS Code extension (FEAT-SKILL-028)**: Not part of this feature
