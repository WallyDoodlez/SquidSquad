## FEAT-SKILL-024 — Offer to open planning artifacts in VS Code after each phase

- **Priority**: Low
- **Status**: Shipped
- **Owner**: skill-lead
- **Description**: After each planning phase produces an artifact (RESEARCH.md after Phase 1, CONTEXT.md after Phase 2, TEST-PLAN.md after Phase 3), the PM should ask the user if they want to open it in VS Code for review. Use `AskUserQuestion` with options: "Yes, open in VS Code", "No thanks", and "Never ask again". If "Never ask again" is selected, persist the preference in `config.md` (e.g. `Open Artifacts in Editor: no`) and skip the prompt in future cycles.

- **Acceptance Criteria**:
  - [ ] After Phase 1, PM asks user if they want to view RESEARCH.md in VS Code
  - [ ] After Phase 2, PM asks user if they want to view CONTEXT.md in VS Code
  - [ ] After Phase 3, PM asks user if they want to view TEST-PLAN.md in VS Code
  - [ ] "Yes" opens the file via `code <path>` command
  - [ ] "Never ask again" saves preference to `config.md` and suppresses future prompts
  - [ ] Preference is checked before prompting — if disabled, skip silently
  - [ ] PM template in `references/agent-instructions.md` updated with this behavior
  - [ ] Generated PM CLAUDE.md reflects the new prompt

### Discussion

> [2026-03-29 00:45] **pm/qa**: Filed from human request. QoL improvement — let the user review planning artifacts in their editor with one click, with a persistent opt-out. Status: Pending — awaiting human approval.
> [2026-03-29 00:46] **pm/qa**: Human approved. Light-mode intake (trivial feature). Status → Planning.
> [2026-03-29 00:50] **pm/qa**: Scope revised — apply to all phases (RESEARCH.md, CONTEXT.md, TEST-PLAN.md), not just TEST-PLAN.md. Context and test plan updated. Human approved. Status → Approved.
> [2026-03-29 02:20] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-29 02:25] **skill-lead**: Complete. Added "Open Artifacts in Editor" section to PM template in agent-instructions.md with AskUserQuestion prompt, config.md persistence for "Never ask again", and code CLI fallback. Added per-phase callouts after Phase 1, 2, and 3. CHANGELOG updated. Status → Pending Test.
> [2026-03-29 02:30] **pm/qa**: QA verified — all 3 phases have "Open in editor" callouts, dedicated section in agent-instructions.md with AskUserQuestion flow, config persistence for opt-out. Status → Shipped.
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).
