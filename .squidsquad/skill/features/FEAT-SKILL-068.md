## FEAT-SKILL-068 — Migrate tracker from internal markdown files to GitHub Issues

- **Priority**: High
- **Owner**: skill-lead
- **Status**: In Progress
- **Blocks**: FEAT-SKILL-055 (going public)
- **Description**: Replace the internal markdown-based tracker (`.squidsquad/*/bugs/`, `features/`) with GitHub Issues as the primary tracker. For a public project, contributors expect to file and track work via GitHub Issues, not by editing markdown files in a `.squidsquad/` directory.

  **Current state:**
  - Bugs: `.squidsquad/[role]/bugs/BUG-[ROLE]-NNN.md` + `INDEX.md`
  - Features: `.squidsquad/[role]/features/FEAT-[ROLE]-NNN.md` + `INDEX.md`
  - Discussion entries: inline in each bug/feature file
  - Status transitions: agents edit the `**Status**:` field in markdown
  - All agents read/write these files, commit to git

  **Target state:**
  - Bugs and features are GitHub Issues with labels for type (`bug`, `feature`), priority (`high`, `medium`, `low`), status (`approved`, `in-progress`, `pending-test`, `pending-ship`), and role (`skill`, `pm`, `qa`, `designer`, `dm`)
  - Agents use `gh` CLI to create, read, update, and comment on Issues
  - Discussion entries become Issue comments
  - Status transitions become label changes
  - INDEX.md replaced by `gh issue list` queries
  - ID format: GitHub Issue numbers replace BUG-SKILL-NNN / FEAT-SKILL-NNN

  **Key design questions:**
  - Should internal markdown files remain as a local cache/fallback, or be fully replaced?
  - How to handle the transition — migrate existing items to Issues, or start fresh?
  - How does this interact with the existing GitHub Issues Ingestion feature (config.md)?
  - Rate limits on `gh` CLI — agents making many API calls per cycle
  - Offline mode — what if GitHub is unreachable?
  - How to preserve the Discussion protocol (append-only, timestamped, role-signed)

- **Acceptance Criteria**:
  - [ ] All agents create/read/update bugs and features via `gh issue` commands
  - [ ] Labels for type, priority, status, and role
  - [ ] Issue comments replace Discussion entries (same format: timestamped, role-signed)
  - [ ] Status transitions via label changes
  - [ ] `gh issue list` replaces INDEX.md scanning
  - [ ] Tracker protocol sub-skill rewritten for GitHub Issues
  - [ ] Works with `gh` CLI (already available in SquidSquad's environment)
  - [ ] Fallback behavior when GitHub is unreachable
  - [ ] Migration path from existing markdown tracker to Issues
  - [ ] ID counter in config.md replaced by GitHub Issue numbers

### Discussion

> [2026-04-03 23:30] **pm/qa**: Filed from human.
> [2026-04-03 23:45] **pm/qa**: Human approved. Status → Planning. Beginning Phase 1 Research.
> [2026-04-04 00:30] **pm/qa**: Phase 2 Discussion complete.
> [2026-04-04 01:15] **pm/qa**: Scope simplified per human insight: SquidSquad already requires GitHub (git push/pull). If you can push, you can use Issues. Drop the dual backend/markdown fallback entirely — adds complexity for a case that doesn't exist. GH Issues is THE tracker, no config toggle, no setup question. Updated CONTEXT.md.
> [2026-04-04 01:30] **skill-lead**: Picking up. Status → In Progress.
> [2026-04-04 02:00] **skill-lead**: Implementation complete.
> [2026-04-04 03:00] **skill-lead**: Fixed all 5 QA gaps:
> [2026-04-04 03:45] **pm/qa**: Added deployment procedure to CONTEXT.md. The switch is an atomic coordinated event: stop all agents → migrate → regenerate templates → restart all agents. No agent can be mid-cycle during migration. Working states cleared. Old markdown dirs preserved as archive.
> [2026-04-04 03:30] **pm/qa**: Re-verified — original 5 gaps all PASS. However, new gap found: pm-agent.md and pm-lean.md status bar examples still use old FEAT-SKILL-037/BUG-SKILL-029 format instead of #37/#29. Zero-gap gate — back to In Progress. Fix remaining role files' status bar examples to use #N format. Status → In Progress. (1) Dev File Conventions updated for GH Issues, (2) Dev Prohibitions updated — no markdown tracker refs, (3) PM github-issues.md rewritten as external issue triage (no markdown filing), (4) Config.md: added Tracker: github-issues, removed ID Counters and GitHub Issues Ingestion sections, (5) Status bar examples use #N format. Also updated QA File Conventions, Prohibitions, and status bar examples. Recomposed agent-instructions.md. Status → Pending Test.
> [2026-04-04 02:30] **pm/qa**: Unbiased QA: 15 PASS / 5 FAIL. Zero-gap gate — back to In Progress. Gaps: (1) dev-agent File Conventions still refs markdown tracker, (2) dev-agent "Never Do" still refs markdown files, (3) PM github-issues.md still creates markdown tracker files, (4) config.md missing Tracker field + has obsolete ID counters, (5) status bar examples use old BUG-SKILL-029 format instead of #29. Full results in FEAT-SKILL-068-QA-RESULTS.md. Status → In Progress. Created common/tracker-protocol.md with GH Issues operations (startup check, ~25 label taxonomy, CRUD via gh CLI, status transitions via labels, Discussion as comments). Rewrote dev-agent Steps 2-3 and Filing Bugs for gh CLI. Rewrote qa-specific/verification Steps 3-5 for gh CLI. Added tracker-protocol include and startup check to all 6 role templates. Regenerated agent-instructions.md (5588 lines). All smoke tests passing. Status → Pending Test.
> [2026-04-04 01:00] **pm/qa**: Phase 3 complete — TEST-PLAN.md generated (30 TCs). Planning phases complete. Status → Approved. Ready for skill-lead pickup. Note: startup check refined — verify gh Issues PERMISSIONS (not availability), soft-fail during setup, hard crash post-setup. — 5 questions + 1 architectural clarification resolved. Key human decisions: (1) dual backend — GH Issues default, markdown opt-out fallback, (2) setup asks user which tracker, (3) soft-fail at startup — warn if gh unavailable, offer fallback (NOT hard crash), (4) exclude closed issues, (5) issue numbers in working-state, (6) migration via upgrade. CONTEXT.md written. Human approved Phase 2 gate. Prerequisite for going public (FEAT-SKILL-055). Contributors expect GitHub Issues, not internal markdown files. This is a major rewrite of the tracker protocol — all agents' read/write patterns change. 055 on hold until this ships.
