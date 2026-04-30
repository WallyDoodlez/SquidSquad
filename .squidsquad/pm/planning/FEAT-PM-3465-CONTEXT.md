# FEAT-PM-3465 Context — Layered Role Definition Architecture

## Scope

Restructure role definitions into 4 composable layers. **Both CLAUDE.md and SOUL.md must be layered.**

- **Layer 1 — Agent Definition**: What a SquidSquad agent IS. Shared by every agent regardless of role. (Ralph Loop, tracker protocol, vault protocol, health/heartbeat, cycle runner, context pressure, git protocol, base identity)
- **Layer 2 — Role Definition**: What a `<role>` agent IS. The concrete role: dev, pm, qa, dm, designer. Role-specific workflow, responsibilities, quality bar, decision style.
- **Layer 3 — Role Customization**: Specialization of a role for a specific use case. Variants inherit Layer 2 and add/override behavior for a domain.
- **Layer 4 — Project Specific**: Project-level customization. Instructions and personality specific to THIS project. PM can push behavioral directives here directly (write → recompose → reboot). Managed as project sub-skills (`references/sub-skills/project/*.md`). Soul Shepherd writes observed signals here via soul_adaptation.py.

Each layer carries **both** CLAUDE.md and SOUL.md. These serve distinct purposes:

**CLAUDE.md** = Instructions, procedures, workflows, rules, protocols — what the agent **DOES**.
**SOUL.md** = Personality, identity, decision style, quality bar, communication style, values — who the agent **IS**.

Both are composed build-time via compose.py. Deployed artifacts remain single flat files.

**Key insight**: The primary value of layering is **deduplication through extraction**. Shared instructions and behaviors that are currently duplicated across role templates MUST be extracted into lower layers:
- Content shared by ALL agents → extract to Layer 1
- Content shared by a role family → extract to Layer 2
- Only the delta/customization remains in Layer 3

If the implementation just creates new files without actually MOVING shared content down, the layering is cosmetic. The test for success: Layer 3 files should be THIN (only the customization delta), and Layer 1/2 should contain the bulk of shared content that was previously duplicated.

## Layer Content Map (what goes where)

### CLAUDE.md (instructions — what the agent DOES)

| Layer | Content | Currently lives in |
|-------|---------|-------------------|
| **L1 — Base Agent** | Tracker protocol, cycle runner, vault protocol, health/heartbeat, context pressure, git protocol, status bar, self-restart, working state, discussion protocol, file conventions | `references/sub-skills/common/` — already shared but not formally Layer 1 |
| **L2 — Role** | Role-specific workflow steps (PM's Ralph Loop steps, dev's implementation workflow, QA's verification steps, DM's delivery steps), role-specific filing rules, role-specific verification rules | `references/roles/<role>/CLAUDE.md` + `<role>-specific/` sub-skills — currently one flat file per role |
| **L3 — Customization** | Domain-specific procedures only. Example: `pm-skill` adds "deterministic vs probabilistic boundary checklist" to PM's workflow. `dev-ios` adds "App Store submission checklist". THIN — only the delta. | Does not exist yet — this is what the feature creates |

### SOUL.md (personality — who the agent IS)

| Layer | Content | Currently lives in |
|-------|---------|-------------------|
| **L1 — Base Agent** | "You are a SquidSquad agent", timestamp discipline, atomic write discipline, sub-agent model preference, core values shared by all agents | Currently duplicated across all role SOUL.md files — MUST be extracted |
| **L2 — Role** | Role-specific personality (PM's diplomatic/skeptical style, dev's code-first mentality, QA's zero-gap gate philosophy, DM's delivery precision), role quality bar, role decision style, role communication style | Currently in each role's SOUL.md — stays here but with L1 content extracted out |
| **L3 — Customization** | Domain-specific personality traits, domain vocabulary, tech stack awareness. Example: `pm-skill` adds "conscious about probabilistic boundaries". `dev-ios` adds "thinks in Swift, knows UIKit/SwiftUI patterns". THIN. | Does not exist yet |

### The deduplication test

After implementation, verify:
- L1 SOUL.md contains content that was previously copy-pasted in ALL role SOUL.md files
- L2 SOUL.md is SHORTER than current role SOUL.md (because L1 was extracted)
- L3 SOUL.md is THIN (only domain delta, not a copy of L2)
- Same principle applies to CLAUDE.md: L1 holds what was in common/, L2 holds role-specific, L3 is delta only

## Locked Decisions (human decided)

- **Layer model** (human clarification):
  - Layer 1 = agent definition (what any SquidSquad agent is)
  - Layer 2 = role definition (what a dev/pm/qa/dm/designer is)
  - Layer 3 = role customization (skill dev, FE dev, PM-for-coding, etc.)
  - NO intermediate "role family" abstraction
- **Both files layered** (human blocked partial implementation): CLAUDE.md AND SOUL.md must both be layered. Shipping only SOUL.md layering is not acceptable.
- **Deduplication is the point** (human directive): Shared content MUST be extracted from higher layers into lower layers. If L1 content is still duplicated in L2, or L2 content is duplicated in L3, the implementation is wrong. L3 files must be THIN — only the customization delta. L2 files must be SHORTER than current role templates because L1 was extracted out.
- **SOUL.md vs CLAUDE.md distinction**: CLAUDE.md = procedures, workflows, rules (what agent DOES). SOUL.md = personality, identity, values, decision style (who agent IS). These are separate concerns and must not bleed into each other.
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

- Directory structure for layer source files (e.g., `references/layers/1-base/`, `references/layers/2-role/<role>/`, `references/layers/3-preset/<variant>/`)
- Whether `upgrade_soul()` is a new function or extension of `deploy_role()`
- Layer 1/2 boundary classification for edge cases (vault-protocol variants, boot-remote-agents)
- How to document the layer model in `manifest.md`
- Implementation details of preset content (personality traits, domain vocabulary)
- Whether existing dev variants (skill/be/fe) get actual new Layer 3 content or just rename

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
