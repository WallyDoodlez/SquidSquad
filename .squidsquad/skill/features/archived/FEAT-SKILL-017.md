## FEAT-SKILL-017 — Externalize agent templates from generated CLAUDE.md files

- **Priority**: High
- **Status**: Shipped
- **Owner**: skill-lead
- **Description**: Currently, setup generates full CLAUDE.md files for each agent by inlining the entire template from `references/agent-instructions.md` with substitutions. This creates large, duplicated files in the user's repo that are hard to maintain and require full regeneration on every upgrade.

  Instead, externalize the templates:

  **Architecture:**
  1. During setup, copy the template files into `.squidsquad/templates/` (e.g. `dev-agent.md`, `pm-agent.md`) — these are the canonical instructions, shared across all agents of the same type
  2. Each agent's `.squidsquad/[role]/CLAUDE.md` becomes a small bootstrapper that contains only:
     - Role-specific config (role name, test command, other roles, interval)
     - A reference instruction: "Read `.squidsquad/templates/dev-agent.md` for your full Ralph Loop instructions. Substitute the config values above wherever you see `[ROLE]`, `[ROLE_TEST_CMD]`, etc."
  3. The agent reads the template at runtime — Claude pulls the file when it needs the instructions

  **Benefits:**
  - Templates maintained in one place — edit once, all agents pick up changes
  - Upgrades only update `.squidsquad/templates/` — no need to regenerate per-agent CLAUDE.md files
  - Much smaller generated files — less git bloat
  - Cleaner separation between "what this agent is" (config) and "how agents work" (template)
  - Future: templates could be pulled from a remote source for auto-updates

  **Migration:**
  - Existing setups need an upgrade path: detect inline CLAUDE.md, extract config, replace with bootstrapper
  - `references/agent-instructions.md` in the skill repo continues to be the source of truth; setup copies from there into `.squidsquad/templates/`

- **Acceptance Criteria**:
  - [ ] Setup creates `.squidsquad/templates/dev-agent.md` and `.squidsquad/templates/pm-agent.md` from `references/agent-instructions.md`
  - [ ] Generated `[role]/CLAUDE.md` is a small bootstrapper (~20 lines) with role config + reference to template
  - [ ] Agents correctly read and follow the template at runtime
  - [ ] Placeholder substitution works (agent reads config block, applies values to template)
  - [ ] Upgrade process migrates existing inline CLAUDE.md to bootstrapper + template
  - [ ] SKILL.md setup steps updated to reflect the new structure
  - [ ] File structure section updated to show `templates/` directory
  - [ ] Tested with at least two different role names to confirm substitution works

### Discussion

> [2026-03-28 04:25] **pm/qa**: Filed from human request. Architectural improvement — externalize templates so they're maintained once and referenced at runtime. Reduces duplication, simplifies upgrades, and keeps generated files small. Status: Pending — awaiting human approval.
> [2026-03-29 00:00] **pm/qa**: Human approved. Status → Planning. Beginning intake process.
> [2026-03-29 00:30] **pm/qa**: Phase 1 (research), Phase 2 (discussion), Phase 3 (test plan) complete. All decisions locked: build-time substitution, keep [ROLE] placeholders, natural-language Read instruction, auto-detect migration. Human approved. Status → Approved.
> [2026-03-29 02:00] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-29 02:10] **skill-lead**: Complete. Updated SKILL.md (Step 2 adds templates/, Step 4 split into 4a/4b/4c for template generation + bootstrapper + root CLAUDE.md, Upgrade Instructions handle migration with auto-detect), File Structure section shows templates/, references/agent-instructions.md header updated, README.md file structure and upgrade section updated, CHANGELOG.md entry added. Status → Pending Test.
> [2026-03-29 02:30] **pm/qa**: QA verified — setup generates templates + bootstrappers, upgrade path handles inline-to-bootstrapper migration via auto-detect heuristic, SKILL.md and README updated. Status → Shipped.
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).
