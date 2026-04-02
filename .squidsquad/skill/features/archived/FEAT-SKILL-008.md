## FEAT-SKILL-008 — Annotated step markers in chat output

- **Priority**: Medium
- **Status**: Shipped
- **Owner**: skill-lead
- **Description**: When agents execute Ralph Loop steps, the chat output should clearly show which step is being performed with a consistent, highlighted prefix. This makes it easy for the human to scan scrollback and identify SquidSquad activity vs. normal Claude output. Each step should print a marker like `[SquidSquad] Pulling latest...`, `[SquidSquad] Running QA pass...`, `[SquidSquad] Filing bug...`, etc. The `[SquidSquad]` prefix acts as a visual anchor. This applies to all agents (dev and PM/QA).
- **Acceptance Criteria**:
  - [ ] Every Ralph Loop step prints a `[SquidSquad]` prefixed status line when it starts (e.g. `[SquidSquad] Step 1 — Pulling latest...`)
  - [ ] Key sub-actions within steps also get markers (e.g. `[SquidSquad] Filing BUG-SKILL-008...`, `[SquidSquad] Committing and pushing...`)
  - [ ] Markers are concise — one line each, not verbose
  - [ ] Both dev and PM/QA CLAUDE.md templates in `references/agent-instructions.md` include the marker convention
  - [ ] SKILL.md documents the marker format
  - [ ] Generated CLAUDE.md files for this project updated to include markers

### Discussion

> [2026-03-28 02:20] **pm/qa**: Filed from human request. Human wants visible, annotated step markers so SquidSquad activity is easy to spot in scrollback. Status: Pending — awaiting human approval.
> [2026-03-28 02:25] **pm/qa**: Human approved. Status → Approved.
> [2026-03-28 03:00] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-28 03:10] **skill-lead**: Complete. Added `[squidsquad]` prefixed step markers to all Ralph Loop steps in both dev and PM/QA templates (references/agent-instructions.md) and generated CLAUDE.md files. Documented marker convention in SKILL.md. Updated CHANGELOG. Status → Pending Test.
> [2026-03-28 03:15] **pm/qa**: QA verified — all 6 criteria pass. Step markers in both templates and generated files, sub-actions covered, SKILL.md documented. Status → Shipped.
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).
