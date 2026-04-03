# FEAT-SKILL-027 Context — Designer Agent Role

## Scope

Add a Designer agent role to SquidSquad — a creative collaborator that takes the human's vision after PM planning and works interactively with the human to produce approved design specs before handing off to dev agents. The designer assesses technical feasibility, produces structured design specs, and participates in real-time design sessions with the human.

**In scope:**
- Designer role sub-skill under FEAT-SKILL-030 sub-skill architecture
- Designer Ralph Loop (autonomous, standard pattern)
- Tag-based design routing on features (`Design: needed/in-progress/complete/not-needed`)
- Technical feasibility assessment (Green/Yellow/Red) in every design spec
- Real-time interactive design session (human ↔ designer conversation)
- Design spec handoff format to dev agents
- Own tracker (`.squidsquad/designer/bugs/`, `features/`)
- Setup flow integration (detecting `designer` role)
- Manual mode (no external tool required)
- MCP/CLI integration for design tools when available

## Locked Decisions (human decided)

- **Fixed `designer` name**: Always called `designer`, like `pm` and `dm`. Auto-detected in setup. One designer per project.
- **Tag-based routing**: Features get a `Design: needed/in-progress/complete/not-needed` field. No new statuses added to the lifecycle. Dev agents check: if `Design` field is `needed` or `in-progress`, skip the feature. If `complete` or `not-needed`, pick it up.
- **Own tracker**: Designer gets `.squidsquad/designer/bugs/` and `features/` following the one-tracker-per-agent pattern. Design-specific issues (spec revisions, token conflicts) go here.
- **Per-feature tokens for now**: Each design spec includes its own tokens section. No global design system. The global memory layer (FEAT-SKILL-029) will handle design system knowledge when it's built.
- **MCP/CLI for design tools, manual fallback**: Designer connects to external tools (Figma, Stitch) via MCP servers or CLI tools if available. Falls back to manual spec mode when no tool is connected. Zero credential management in SquidSquad.
- **Autonomous with idle detection**: Standard Ralph Loop on 30-min interval. After 5 consecutive quiet cycles, logs suggestion to stop the designer agent. Human decides.
- **Real-time interactive design session**: When designer picks up a `Design: needed` feature, it enters interactive mode in its conversation — presenting options, iterating with the human in real-time, exploring alternatives. This blocks the designer's loop (analogous to PM Phase 2 Discussion blocking PM's loop, and FEAT-SKILL-058 suppressing cycles). Human must approve the design before it's handed to dev.
- **Built as sub-skill from day one**: Designer MUST use the FEAT-SKILL-030 sub-skill architecture. Template lives in `references/sub-skills/roles/designer.md` with designer-specific sub-skills alongside. Composed via the same build-time engine. No monolithic template.

## Dev Discretion (dev agent can choose)

- Exact structure of `references/sub-skills/designer-specific/` files and how many sub-skill files
- Design spec markdown format details (sections, ordering)
- How the designer discovers available MCP/CLI tools at runtime
- Feasibility assessment heuristics (how to calibrate "reasonable effort" per project)
- How idle detection counts quiet cycles (config value vs hardcoded)
- Session format for the interactive design conversation (how the designer presents options)

## Side Effect Mitigations (required)

- Dev agent templates must add one check: skip features where `Design` field is `needed` or `in-progress`
- PM template must add design routing logic during Phase 2 (asking human if feature needs design, adding Design Brief to CONTEXT.md)
- Designer specs must be in a standardized path dev agents can find (`.squidsquad/designer/specs/FEAT-[ROLE]-XXX/`)
- Circular rejection loop (dev rejects → designer revises → dev rejects again) must escalate to PM/human after 2 round-trips
- PM template size growth from design routing must be minimal (~40-60 lines)
- Composed template size must stay within FEAT-SKILL-030's constraints

## Upgrade Path (required)

- `/squidsquad-upgrade` detects `designer` role in config.md Dev Agents list
- If present and `.squidsquad/designer/` doesn't exist: create directory structure, generate template via sub-skill composition, create boot scripts
- Add `Design Tools` section to config.md with defaults (`Tool: none`)
- Add `BUG-DESIGNER` and `FEAT-DESIGNER` counters to config.md
- Existing features without `Design` field default to `not-needed`
- Graceful degradation: missing designer = features skip design phase entirely

## Out of Scope

- **Global design system / token management**: Deferred to FEAT-SKILL-029 (memory layer)
- **Multiple designers per project**: Single `designer` role only
- **Web UI for design sessions**: Future (FEAT-SKILL-020)
- **GitHub Issues as design discussion surface**: Future (Phase C of FEAT-SKILL-030 follow-up)
- **User-configurable sub-skills for designer**: Future (FEAT-SKILL-054)
