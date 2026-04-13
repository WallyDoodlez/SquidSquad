---
type: decision
tags: [architecture, sub-skills, composition, foundational]
created: 2026-04-02
updated: 2026-04-12
owner: skill
status: active
confidence: high
source: code
links: [squidsquad, code-conventions, learning-atomic-migration-strategy]
---

## Context

SquidSquad originally crammed all agent instructions into a single monolithic SKILL.md file. As the project grew to support multiple roles (PM, QA, dev leads, DM, Designer), this became unwieldy. FEAT-SKILL-030 redesigned the architecture to break the monolith into cooperating sub-skills.

## Content

SquidSquad uses a layered sub-skill architecture where the main skill is the orchestrator (setup, config, philosophy) and each role is an independent sub-skill. The hierarchy is:

1. **Main skill** (squidsquad) -- setup, config, philosophy, orchestration
2. **Role sub-skills** (hardcoded, one per role) -- pm/qa, skill-lead, dm
3. **Common sub-skills** (auto-included by every role) -- tracker protocol, discussion protocol, Ralph Loop core, context pressure, working state, health checks, git protocol
4. **Role-specific sub-skills** (shipped with each role) -- pm: feature intake, QA test execution, delivery fallback; skill: bug triage, implementation workflow; dm: delivery packaging, version bumps
5. **Capability sub-skills** (external integrations) -- packaged as `references/sub-skills/capabilities/<id>/` with manifest.yaml + sub-skill.md + setup.md. Composed at build time via `{{capability: <id>}}` directive. Runtime self-check via `capability_check.py`. PM Phase 1 Research includes capability gap analysis. Examples: figma, google_stitch, local_html, local_delivery.

Composition is build-time concatenation: sub-skill sources live in `references/sub-skills/` and are composed into `agent-instructions.md` with section markers. The composed artifact has a DO NOT EDIT header.

## Rationale

- A monolithic file could not scale as new roles and capabilities were added
- Each role needs different instructions but shares common protocols (Ralph Loop, tracker, git)
- Build-time composition (vs. runtime include) was chosen for simplicity and predictability
- All phases shipped atomically in one dev cycle to avoid breaking running agents mid-migration
- Agent tool kept for interactive execution (no --print mode); hardened non-interactive execution deferred
- Phase C (interaction layer) and Phase D (API/SDK) deferred to separate features

## Related

- [[squidsquad]]
- [[code-conventions]]
- [[learning-atomic-migration-strategy]]

---

### Changelog

- 2026-04-02 -- Created by QA agent. Captured from FEAT-SKILL-030 feature file and discussion history during vault-create testing.
- 2026-04-12 -- Updated by skill agent. Added Layer 5 (capability sub-skills) from #401: tools→capabilities rename, schema v2, {{capability:}} compose directive, capability_check.py runtime self-check, PM gap analysis.
