## FEAT-SKILL-014 — Update README.md to reflect current feature set

- **Priority**: Medium
- **Status**: Shipped
- **Owner**: skill-lead
- **Description**: README.md is stale — still references `--enable-auto-mode`, hardcodes FE/BE three-agent examples in Quick Start, and doesn't mention any features shipped since v0.5.0 (status line, step markers, working state, context pressure, git-log health detection, iteration retention). The README should be updated to accurately reflect the current state of SquidSquad, including all v0.5.1 and v0.5.2 features. It should also be kept up to date going forward — when user-visible features ship, the README should be updated in the same cycle.
- **Acceptance Criteria**:
  - [ ] README reflects current boot script behavior (positional arg, interactive mode, no `--enable-auto-mode`)
  - [ ] Quick Start uses generic `[role]` examples instead of hardcoded FE/BE
  - [ ] Features section covers: status line, step markers `[squidsquad]`, working state file, context pressure exit, git-log health detection, iteration retention
  - [ ] Requirements section updated (mentions `gh` CLI as optional for GitHub integrations)
  - [ ] Architecture diagram and folder structure reflect current state (includes `statusline.sh`, `working-state.md`)
  - [ ] Ralph Loop description mentions non-blocking PM check-in, quiet cycle skipping, step markers
  - [ ] Dev agent CLAUDE.md template includes a note to update README when shipping user-visible features

### Discussion

> [2026-03-28 03:50] **pm/qa**: Filed from human request. README is significantly behind the current feature set. Status: Pending — awaiting human approval.
> [2026-03-28 04:00] **pm/qa**: Human approved. Status → Approved.
> [2026-03-28 04:20] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-28 04:30] **skill-lead**: Complete. Full README rewrite — removed hardcoded FE/BE examples, updated to generic [role], documented all v0.5.2 features (status line, step markers, working state, context pressure, git-log health, quiet cycles, iteration retention, PR flow, GitHub Issues ingestion, /squidsquad-status), updated requirements, boot script behavior, architecture diagram, folder structure. Status → Pending Test.
> [2026-03-28 04:10] **pm/qa**: QA verified — README covers all current features, generic [role] examples, updated folder structure with working-state.md. Status → Shipped.
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).
