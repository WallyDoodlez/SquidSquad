# FEAT-PM-3465 Context — Layered Role Definition Architecture

## Scope

Restructure role definitions into 3 composable layers with matching SOULs:

- **Layer 1 — Agent Definition**: What a SquidSquad agent IS. Shared by every agent regardless of role. (Ralph Loop, tracker protocol, vault protocol, health/heartbeat, cycle runner, context pressure, git protocol, base identity)
- **Layer 2 — Role Definition**: What a `<role>` agent IS. The concrete role: dev, pm, qa, dm, designer. Role-specific workflow, responsibilities, quality bar, decision style.
- **Layer 3 — Role Customization**: Specialization of a role for a specific use case. Variants inherit Layer 2 and add/override behavior for a domain.

Each layer carries both CLAUDE.md (instructions) and SOUL.md (personality). Composition remains build-time via compose.py. Deployed artifacts (.squidsquad/<role>/CLAUDE.md and SOUL.md) remain single flat files — layering is a source-time concern only.

**Key insight**: This formalizes what already partially exists (dev → skill/be/fe variants) into a consistent 3-layer architecture that applies to ALL roles and enables arbitrary customization without copy-paste.

## Locked Decisions (human decided)

- **Layer model** (human clarification):
  - Layer 1 = agent definition (what any SquidSquad agent is)
  - Layer 2 = role definition (what a dev/pm/qa/dm/designer is)
  - Layer 3 = role customization (skill dev, FE dev, PM-for-coding, etc.)
  - NO intermediate "role family" abstraction
- **SOUL.md assembly**: Deploy-time flat assembly. compose.py concatenates Layer 1 + Layer 2 + Layer 3 SOUL sources into one flat file. soul_adaptation.py and `{{runtime:}}` unchanged.
- **Layer 3 naming**: Hyphen convention — `<base>-<variant>` (e.g., `pm-skill`, `qa-skill`, `dev-ios`). compose.py strips suffix to find base role via existing `_load_manifest()` fallback.
- **Layer 3 SOUL.md**: Full file (not overlay/patch). Layer 3 author starts from Layer 2 SOUL as base and modifies. No new merge mechanism needed.
- **Variant inheritance**: Existing dev variants (skill, be, fe) become Layer 3 customizations. `_load_manifest()` fallback chain handles this naturally. Must include integration test.
- **Ship with presets**: Feature ships with concrete Layer 3 presets. Each preset is a **full team composition** — all roles get a customization per preset, not just dev.
  - **Skill preset** (this project's domain — skill/probabilistic code development):
    - `dev-skill` — existing (currently "skill" variant), skill development focus
    - `pm-skill` — conscious about deterministic vs probabilistic boundaries, what needs deterministic scripting vs what is LLM-generated
    - `qa-skill` — knows how to test probabilistic code, create e2e tests using test agents, verify LLM-consumed instructions
    - `dm-skill` — delivery-aware of skill packaging and distribution
  - **iOS preset**:
    - `dev-ios`, `pm-ios`, `qa-ios`, `dm-ios` — iOS app development team
  - **Web preset**:
    - `dev-web`, `pm-web`, `qa-web`, `dm-web` — Web app development team
  - **Android preset**:
    - `dev-android`, `pm-android`, `qa-android`, `dm-android` — Android app development team
  - **Full-stack preset**:
    - `dev-fullstack`, `pm-fullstack`, `qa-fullstack`, `dm-fullstack` — Full stack development team
- **Comms layer independence**: Comms sub-skills stay in `common/` with feature-flag gating. Independent from this feature.
- **Layer 1/2 boundary** (Q3/Q4): Dev discretion to classify and document. Note: `common/` directory does NOT mean Layer 1 — some sub-skills in `common/` are role-specific in practice (e.g., `boot-remote-agents` is PM-only).

## Dev Discretion (dev agent can choose)

- Directory structure for Layer 1 sources
- How `includes.yml` encodes the 3 layers (position convention vs explicit markers)
- Whether `upgrade_soul()` is a new function or extension of `deploy_role()`
- Whether existing `references/roles/<role>/` maps to Layer 2 directly or needs restructuring
- Layer 1/2 boundary classification for edge cases (vault-protocol variants, boot-remote-agents)
- How to document the layer model in `manifest.md`
- Implementation details of preset SOUL.md content (personality traits, domain vocabulary)

## Side Effect Mitigations (required)

- soul_adaptation.py must remain unchanged — deploy-time assembly guarantees flat SOUL.md
- Atomic write pattern for SOUL.md generation (write to .tmp then mv)
- All roles must be migrated simultaneously per [[learning-atomic-migration-strategy]]
- Full reboot cycle required post-migration
- Existing `_load_manifest()` fallback chain must not break — add integration test
- `upgrade_soul()` must preserve Layer 3 content and `## Project Adaptation` section on upgrade
- Current variant behavior (skill/be/fe inheriting from dev) must work identically post-migration

## Upgrade Path (required)

- `squidsquad-upgrade` runs `compose.py deploy-all` which picks up new 3-layer composition
- New `upgrade_soul(role)` re-renders L1+L2, preserves L3 + Project Adaptation
- Full agent reboot post-upgrade
- Graceful degradation: old flat composition continues working if user doesn't upgrade
- Existing SOUL.md Project Adaptation sections map to Layer 3 automatically

## Out of Scope

- Comms sub-skill placement (stays in common/, deferred to #3415 follow-up)
- Runtime multi-file SOUL reading
- New compose.py directive types — use includes.yml ordering
- Conditional SOUL.md content (runtime conditionals stay in CLAUDE.md sub-skills)
- Capability sub-skills (Layer 5) — unchanged
- SOUL.md overlay/patch mechanism — full file only
