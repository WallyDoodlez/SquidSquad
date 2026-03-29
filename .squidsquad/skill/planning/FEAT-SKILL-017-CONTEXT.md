# FEAT-SKILL-017 Context — Externalize Agent Templates

## Scope
Split each agent's CLAUDE.md into two parts: (1) a shared, build-time-substituted template in `.squidsquad/templates/` and (2) a small per-agent bootstrapper CLAUDE.md (~20 lines) with role config + a Read instruction pointing to the template. Includes an upgrade migration path for existing inline CLAUDE.md files.

## Locked Decisions (human decided)
- **Build-time substitution**: Setup substitutes all `[ROLE]` placeholders when copying templates from `references/agent-instructions.md` into `.squidsquad/templates/`. Agents never see placeholders — they get fully resolved instructions. Each role gets its own template file (e.g. `dev-agent-fe.md`, `dev-agent-be.md`, `pm-agent.md`).
- **Keep [ROLE] placeholder syntax**: `references/agent-instructions.md` retains current `[ROLE]`, `[ROLE_UPPER]`, etc. placeholder format. No rewrite to generic language. Minimal change to source templates.
- **Natural-language Read instruction**: Bootstrapper CLAUDE.md uses proven pattern: "Read `.squidsquad/templates/dev-agent-fe.md` for your complete instructions. Follow them exactly." Same approach as root CLAUDE.md auto-boot.
- **Auto-detect migration**: Upgrade detects inline vs bootstrapper format by checking if CLAUDE.md contains `## The Ralph Loop` (inline, >50 lines) vs bootstrapper (<50 lines, no Ralph Loop heading). No config flag needed.
- **Upgrade path must be adjusted**: Human explicitly flagged that the update/upgrade flow must be updated to handle the new template architecture — regenerate templates from source, leave bootstrappers untouched unless config format changes.

## Dev Discretion (dev agent can choose)
- Exact bootstrapper format (YAML-like config block vs freeform)
- Template file naming convention (e.g. `dev-agent-fe.md` vs `fe-agent.md`)
- Error messaging when template file is missing
- Whether to preserve user customizations from inline CLAUDE.md during migration (recommended: extract and note in bootstrapper)

## Side Effect Mitigations (required)
- Bootstrapper MUST contain an imperative instruction to read the template ("You MUST read ... NOW before proceeding")
- Missing template file must produce a clear error message directing user to run upgrade
- Migration must detect and handle mixed states (templates exist but bootstrapper is old format, or vice versa)
- Upgrade flow in SKILL.md must be rewritten to regenerate templates/ and only touch bootstrappers if config format changes

## Out of Scope
- Runtime placeholder substitution
- Generic language rewrite of templates
- Native Claude Code include mechanism (doesn't exist yet)
- Remote/auto-update template pulling
- Config flag for template format detection
