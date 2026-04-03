## FEAT-SKILL-027 — Designer agent template with external design tool integration

- **Priority**: High
- **Owner**: skill-lead
- **Status**: Planning
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
> [2026-04-02 07:00] **pm/qa**: Human approved with expanded scope.
> [2026-04-02 07:15] **pm/qa**: Critical workflow clarification from human. The designer's core purpose is to be the human's creative collaborator — taking the human's vision after PM planning and working WITH the human interactively to produce an approved design. Flow: PM planning completes → Designer takes planning artifacts + human vision → Interactive design session (human ↔ designer iterate) → Human approves design → Design handed to dev for implementation. The designer is NOT a fire-and-forget spec generator. There must be an interactive phase where the human talks to the designer and works with the generated design before approval. Dev cannot start until the human approves the design. This is analogous to PM's Phase 2 Discussion but for design. Status → Planning. Key additions: (1) designer must assess technical feasibility against engineering effort before committing to design direction, (2) quality gate for design inputs — no garbage in, (3) pipeline integration — where designer sits in product development flow (PM intake → Designer → Dev, not all features), (4) designer validates requests have sufficient context. Research phase must investigate: feasibility assessment mechanisms, pipeline positioning, input validation, and how designer communicates constraints back to PM/human. Beginning Phase 1 Research.
