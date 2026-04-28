# FEAT-PM-3465 Context — Layered Role Definition Architecture

## Scope

Restructure role definitions into 3 composable layers (base agent → general role → specific role) with matching SOULs. Each layer carries both CLAUDE.md (instructions) and SOUL.md (personality). Composition remains build-time via compose.py. The deployed artifacts (.squidsquad/<role>/CLAUDE.md and SOUL.md) remain single flat files — layering is a source-time concern only.

## Locked Decisions (human decided)

- **SOUL.md assembly**: Deploy-time flat assembly. compose.py concatenates Layer 1 + Layer 2 + Layer 3 SOUL sources into one flat `.squidsquad/<role>/SOUL.md`. soul_adaptation.py and `{{runtime:}}` directive unchanged. Requires new `upgrade_soul()` function to re-render L1+L2 without clobbering L3 and Project Adaptation.
- **Layer 2 content**: Role-family identity. Layer 2 owns the coordinator/executor/verifier/delivery/creative distinction — content that is genuinely not in `common/` today. Examples: developer = code-change protocol, PR conventions; verifier = zero-gap gate, coverage reqs; coordinator = pipeline oversight, human check-in.
- **PM's Layer 2**: Coordinator + verifier dual. PM's Layer 2 carries both identities. Verification content will overlap with QA's "verifier" Layer 2 — acceptable duplication given the layers are small, or dev may extract shared verification primitives.
- **Dev variant inheritance**: Variants (skill, be, fe) inherit Layer 2 from parent manifest via existing `_load_manifest()` fallback. Add `general_role: developer` to `dev/manifest.yaml`. Zero new logic needed. Must include explicit integration test for variant Layer 2 content.
- **Comms layer independence**: Comms sub-skills (chat-etiquette, mention-protocol, consensus-protocol) stay in `common/` with feature-flag gating. Layer 2 and #3415 are independent features with no interaction. Revisit placement after #3415 stabilizes.

## Dev Discretion (dev agent can choose)

- Internal directory structure for Layer 1 and Layer 2 sources (e.g., `references/roles/base/` vs `references/layers/`)
- How `includes.yml` encodes the 3 layers (position convention vs explicit markers)
- Whether `upgrade_soul()` is a new function or an extension of existing `deploy_role()`
- How to handle PM+QA verification content overlap (shared extraction vs acceptable duplication)
- Manifest schema approach: new `general_role` field vs directory convention

## Side Effect Mitigations (required)

- soul_adaptation.py must remain unchanged — deploy-time assembly guarantees flat SOUL.md
- Atomic write pattern for SOUL.md generation (write to .tmp then mv)
- All 5 roles must be migrated simultaneously per [[learning-atomic-migration-strategy]]
- Full reboot cycle required post-migration (all agents restart with new CLAUDE.md + SOUL.md)
- Existing `_load_manifest()` fallback chain for dev variants must not be broken — add integration test
- `upgrade_soul()` must preserve Layer 3 content and `## Project Adaptation` section on upgrade

## Upgrade Path (required)

- `squidsquad-upgrade` runs `compose.py deploy-all` which picks up new Layer 1+2+3 composition
- New `upgrade_soul(role)` function re-renders Layer 1+2 sections, preserves Layer 3 + Project Adaptation
- Full agent reboot post-upgrade (all agents load fresh CLAUDE.md and SOUL.md)
- Graceful degradation: users who don't upgrade continue running old flat composition, no breakage

## Out of Scope

- Comms sub-skill placement (stays in common/, deferred to #3415 follow-up)
- Runtime multi-file SOUL reading
- New compose.py directive types ({{layer1:}}, {{layer2:}}) — use includes.yml ordering
- Conditional SOUL.md content (runtime conditionals stay in CLAUDE.md sub-skills)
- Capability sub-skills (Layer 5) — unchanged by this feature
