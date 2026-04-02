## FEAT-SKILL-027 — Designer agent template with external design tool integration

- **Priority**: High
- **Owner**: skill-lead
- **Description**: Add a new agent template type — **Designer** — alongside the existing Dev and PM/QA templates. The designer agent works with external design tools (Figma, Google Stitch, and others) and bridges design output into frontend implementation.

  **Key capabilities:**
  1. **External tool integration**: The designer agent should support connecting to design tools via MCP or API (Figma API, Google Stitch, etc.). The architecture should be generalized — not hard-coded to one tool — so any design platform can be plugged in.
  2. **Design-to-code handoff**: The designer produces design artifacts (component specs, tokens, layout specs, asset references) that the FE agent can consume to produce UI. The handoff format should be structured and live in `.squidsquad/designer/` or a shared `design-specs/` directory.
  3. **Designer Ralph Loop**: Different from the dev loop — instead of fix bugs → implement features, the designer loop would be: pull latest → review design requests → fetch/update designs from external tool → produce/update design specs → hand off to FE agent → commit.
  4. **Cross-agent coordination**: The designer files design specs, the FE agent implements them. PM/QA verifies visual fidelity. Needs a new tracker flow: design request → design spec → FE implementation → visual QA.
  5. **Setup integration**: During setup, if user adds a `designer` role, use the Designer template instead of the generic Dev template. Auto-detect by role name or let user choose template type.

  **Generalized design tool abstraction:**
  - A `design-tools.md` config or section in `config.md` listing connected tools and their access method (MCP tool name, API endpoint, etc.)
  - The designer template references this config — "use whichever design tool is configured" rather than hard-coding Figma
  - Support for: fetching component specs, exporting design tokens (colors, spacing, typography), downloading assets, reading annotations/comments

- **Acceptance Criteria**:
  - [ ] New Template 3 (Designer Agent) added to `references/agent-instructions.md`
  - [ ] Designer template has its own Ralph Loop optimized for design workflows
  - [ ] Design tool integration is generalized — works with Figma, Google Stitch, or any MCP-connected design tool
  - [ ] Design-to-FE handoff format defined (component specs, tokens, layout specs)
  - [ ] Cross-agent flow documented: designer → FE → PM/QA visual verification
  - [ ] Setup detects `designer` role and uses Designer template
  - [ ] SKILL.md updated with designer role documentation
  - [ ] Works even without an external tool connected (manual design spec mode)

### Discussion

> [2026-03-29 01:30] **pm/qa**: Filed from human request. Major new capability — a designer agent type that integrates with external design tools (Figma, Google Stitch, etc.) and produces structured design specs for FE agents to implement. Generalized architecture, not locked to one tool. Status: Pending — awaiting human approval.
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).
