# FEAT-SKILL-059 Context — SOUL.md: Agent Personality and Operational Philosophy

## Scope

Add a SOUL.md file per role that defines the agent's operational philosophy, communication style, quality bar, boundaries, and self-improvement lens. The soul shapes HOW each agent approaches all work — not just personality, but the interpretive framework for novel situations.

**In scope:**
- One SOUL.md per role (PM, QA, dev, designer, DM) in `references/sub-skills/souls/`
- 7 dimensions per role: professional identity, quality bar, decision-making style, communication style, boundaries, collaboration posture, self-improvement lens
- Structure + anti-patterns format (verifiable, flexible)
- 2-3 example Discussion entries per role showing voice
- Vault references for human adaptation (BRIEFING.md, human-profile)
- First include in each template — colors everything after it
- Built as sub-skills under FEAT-SKILL-030 architecture

## Locked Decisions (human decided)

- **Structure + anti-patterns**: Communication style defined via what to include + what to NEVER do. Verifiable but not rigid.
- **2-3 example Discussion entries per role**: Examples show the voice in action. Most effective way to teach tone.
- **Soul references vault for adaptation**: Soul says "Consult [[human-profile]] to adapt" and "Check BRIEFING.md for priorities." Connects identity to institutional knowledge.
- **One PM soul, lean variant inherits**: Single PM soul file. The lean template naturally drops QA dimensions since it has no QA steps.
- **70% operational philosophy, 30% personality**: Philosophy ("assume every implementation has a defect") produces better behavior than personality alone ("be skeptical").
- **7 dimensions per role**: Professional identity, quality bar, decision-making style, communication style, boundaries, collaboration posture, self-improvement lens.
- **Static soul + dynamic vault**: Soul is hardcoded and never changes. Project/human adaptation happens through the vault. Prevents identity drift.
- **First include in each template**: Soul loads before any other instructions so it colors everything.
- **Human instruction always overrides soul defaults**: Soul is guidance, not law.

## Dev Discretion (dev agent can choose)

- Exact wording and tone of each role's soul
- How many anti-patterns per dimension
- Length of example Discussion entries
- How the self-improvement lens dimension is formatted
- Whether to use markdown sections or a more compact format

## Side Effect Mitigations (required)

- Soul adds ~60-80 lines per template — monitor composed template size
- Soul must not duplicate procedural instructions already in role templates
- Anti-patterns must be specific enough to be verifiable, not generic
- Example Discussion entries must be clearly marked as examples (not mistaken for real history)

## Upgrade Path (required)

- New `references/sub-skills/souls/` directory with 5 soul files
- Manifest updated with soul includes (first position)
- All templates regenerated with soul composed in
- No data migration needed — purely additive

## Out of Scope

- Dynamic/evolving souls (adaptation happens via vault, not soul changes)
- Per-project soul customization (project context comes from vault)
- User-editable souls (hardcoded, ships with template)
