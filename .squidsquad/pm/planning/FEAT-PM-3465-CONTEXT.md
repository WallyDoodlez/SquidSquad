# FEAT-PM-3465 Context — Layered Role Definition Architecture

## Scope

Restructure role definitions into 3 composable layers. **Both CLAUDE.md and SOUL.md must be layered.**

- **Layer 1 — Agent Definition**: What a SquidSquad agent IS. Shared by every agent regardless of role. (Ralph Loop, tracker protocol, vault protocol, health/heartbeat, cycle runner, context pressure, git protocol, base identity)
- **Layer 2 — Role Definition**: What a `<role>` agent IS. The concrete role: dev, pm, qa, dm, designer. Role-specific workflow, responsibilities, quality bar, decision style.
- **Layer 3 — Role Customization**: Specialization of a role for a specific use case. Variants inherit Layer 2 and add/override behavior for a domain.

Each layer carries **both** CLAUDE.md (instructions) **and** SOUL.md (personality). Composition remains build-time via compose.py. Deployed artifacts (.squidsquad/<role>/CLAUDE.md and SOUL.md) remain single flat files — layering is a source-time concern only.

**Key insight**: This formalizes what already partially exists (dev → skill/be/fe variants) into a consistent 3-layer architecture that applies to ALL roles and enables arbitrary customization without copy-paste.

## Locked Decisions (human decided)

- **Layer model** (human clarification):
  - Layer 1 = agent definition (what any SquidSquad agent is)
  - Layer 2 = role definition (what a dev/pm/qa/dm/designer is)
  - Layer 3 = role customization (skill dev, FE dev, PM-for-coding, etc.)
  - NO intermediate "role family" abstraction
- **Both files layered** (human blocked partial implementation): CLAUDE.md AND SOUL.md must both be layered. Shipping only SOUL.md layering is not acceptable.
- **SAME assembly pattern for both files** (human directive): CLAUDE.md and SOUL.md use the IDENTICAL layering mechanism — 3 source files (Layer 1 + Layer 2 + Layer 3) assembled into one flat file at deploy time. NOT two different mechanisms. NOT includes.yml `base_role`/`additional_includes` for CLAUDE.md. The same deploy-time flat assembly used for SOUL.md applies to CLAUDE.md too: Layer 1 CLAUDE.md + Layer 2 CLAUDE.md + Layer 3 CLAUDE.md → one flat `.squidsquad/<role>/CLAUDE.md`.
- **SOUL.md assembly**: Deploy-time flat assembly. compose.py concatenates Layer 1 + Layer 2 + Layer 3 SOUL sources into one flat file. soul_adaptation.py and `{{runtime:}}` unchanged.
- **CLAUDE.md assembly**: Same as SOUL.md — deploy-time flat assembly. compose.py concatenates Layer 1 CLAUDE.md + Layer 2 CLAUDE.md + Layer 3 CLAUDE.md into one flat file. 3 source files per layer, assembled identically to SOUL.md.
- **Layer 3 naming**: Hyphen convention — `<base>-<variant>` (e.g., `pm-skill`, `qa-skill`, `dev-ios`). compose.py strips suffix to find base role.
- **Layer 3 SOUL.md**: Full file (not overlay/patch).
- **Variant inheritance**: Existing dev variants (skill, be, fe) become Layer 3 customizations. Must include integration test.
- **Ship with presets**: Each preset is a **full team composition** — all roles per preset.
  - **Skill preset** (this project's domain — skill/probabilistic code development):
    - `dev-skill` — skill development, probabilistic code awareness
    - `pm-skill` — deterministic vs probabilistic boundary awareness
    - `qa-skill` — testing probabilistic code, e2e tests with test agents
    - `dm-skill` — skill packaging and distribution awareness
  - **iOS preset**: `dev-ios`, `pm-ios`, `qa-ios`, `dm-ios`
  - **Web preset**: `dev-web`, `pm-web`, `qa-web`, `dm-web`
  - **Android preset**: `dev-android`, `pm-android`, `qa-android`, `dm-android`
  - **Full-stack preset**: `dev-fullstack`, `pm-fullstack`, `qa-fullstack`, `dm-fullstack`
- **Comms layer independence**: Comms sub-skills stay in `common/`. Independent from this feature.
- **Layer 1/2 boundary**: Dev discretion. Note: `common/` does NOT mean Layer 1 (e.g., `boot-remote-agents` is PM-only).

## Dev Discretion (dev agent can choose)

- Whether to use `{{extend:}}` directive for Layer 3 entry files vs prose copy (research recommends `{{extend:}}`, ~10 lines)
- Layer 3 variant-specific sub-skill directory naming (`<variant>-specific/` vs `<base>-specific/<variant>/`)
- `includes.yml` variant schema details (`base_role` + `additional_includes` recommended)
- Directory structure for Layer 1 sources
- Whether `upgrade_soul()` is a new function or extension of `deploy_role()`
- Layer 1/2 boundary classification for edge cases (vault-protocol variants, boot-remote-agents)
- How to document the layer model in `manifest.md`
- Implementation details of preset content (personality traits, domain vocabulary)
- Whether existing dev variants (skill/be/fe) get actual new Layer 3 CLAUDE.md content or just rename

## Side Effect Mitigations (required)

- soul_adaptation.py must remain unchanged — deploy-time assembly guarantees flat SOUL.md
- Atomic write pattern for both CLAUDE.md and SOUL.md generation
- All roles must be migrated simultaneously per [[learning-atomic-migration-strategy]]
- Full reboot cycle required post-migration
- Existing `_load_manifest()` fallback chain must not break — add integration test
- `upgrade_soul()` must preserve Layer 3 content and `## Project Adaptation` section on upgrade
- Current variant behavior (skill/be/fe inheriting from dev) must work identically post-migration
- Layer 3 `includes.yml` must be backward-compatible — existing `includes:` schema unchanged for Layer 2

## Upgrade Path (required)

- `squidsquad-upgrade` runs `compose.py deploy-all` which picks up new 3-layer composition
- New `upgrade_soul(role)` re-renders L1+L2, preserves L3 + Project Adaptation
- Full agent reboot post-upgrade
- Graceful degradation: old flat composition continues working if user doesn't upgrade
- Existing SOUL.md Project Adaptation sections map to Layer 3 automatically

## Out of Scope

- Comms sub-skill placement (stays in common/, deferred to #3415 follow-up)
- Runtime multi-file SOUL reading
- Conditional SOUL.md content (runtime conditionals stay in CLAUDE.md sub-skills)
- Capability sub-skills (Layer 5) — unchanged
- SOUL.md overlay/patch mechanism — full file only
