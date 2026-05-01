# FEAT-PM-4449 Context — L4 Project Instructions: Distribution Packaging + Content Migration

## Scope

Two parts:

**Part 1 — L4 content migration**: Reformat existing project-specific content scattered across vault, config, and soul adaptation into proper L4 files. This is the first real population of L4 for this project.

**Part 2 — Distribution packaging gate**: Add project-specific instructions to PM and DM L4 for verifying npm package, tarball, and installer-files.txt.

## Locked Decisions (human decided)

### Part 1 — L4 Content Migration (concrete inventory)

**→ L4 instructions.md (7 items — what agents DO on this project):**
1. Never ship with failed TCs, git = audit trail (from BRIEFING.md Human Preferences)
2. Quality expectations: all tests pass before complete (from human-profile.md)
3. Platform: Windows 11, Python scripting, bash (from human-profile.md)
4. Direct/mechanical checks over state files (from human-profile.md)
5. Design philosophy: source-agnostic vault, inter-agent sequencing (from human-profile.md)
6. Git protocol: pull --rebase, append-only comments, push cadence (from config.md)
7. Distribution packaging checks for PM and DM (new — Part 2 of this task)

**→ L4 SOUL.md (4 items — who agents ARE on this project):**
1. Communication style: terse, direct, shorthand tolerance (from human-profile.md)
2. Product vision: general-purpose skill, non-technical teams, OSS preference, self-healing (from human-profile.md)
3. Decision-making style: delegate ops, act first when clear (from human-profile.md)
4. Project Context sections: currently empty placeholders across all roles — populate with SquidSquad project identity

**→ Stays put (not moved):**
- All config.md mechanical settings/flags/thresholds/counters (18 items)
- BRIEFING.md pipeline state sections (Active Priorities, Recently Shipped, Core Architecture, Decisions, Constraints, Team State) — vault reference
- Vault decisions/patterns/learnings — institutional knowledge
- human-profile.md Schedule & Availability — stays in vault as reference

**Key note**: human-profile.md is doing double duty. After migration it becomes a thinner vault reference doc. Content that moved to L4 is NOT deleted from vault — vault notes stay as reference, L4 becomes the authoritative operating source.

- **Migration must be non-destructive**: Content moves from vault/adaptation TO L4 source files. Vault notes are NOT deleted — they become reference material that L4 can link to. Soul Shepherd continues writing to L4 going forward.

### Part 2 — Distribution Packaging Gate

- **PM L4 instructions.md** — add to verification checklist:
  - During pending-test verification: does this change affect distributed files?
  - Is installer-files.txt up to date? (new files, renamed files, removed files)
  - Does packages/cli/package.json version match config.md version?
  - If distribution files changed → flag for DM delivery

- **DM L4 instructions.md** — add to delivery checklist:
  - During version bump: verify installer-files.txt is current
  - Verify packages/cli/package.json version matches new version
  - Consider: does this version need npm publish?

- **All agent L4 instructions.md** — general awareness:
  - SquidSquad distributes via npm (npx squidsquad) and GitHub release tarballs
  - installer-files.txt is the file manifest — changes to references/ directory structure must be reflected
  - This is a project-specific concern — other SquidSquad installations don't have this

### Dependency Chain

1. #3465 ✓ shipped — 4-layer architecture exists
2. #4083 in-progress — L4 lifecycle (setup, propagation, upgrade mechanism)
3. **#4449 (this task)** — first real L4 content for this project
4. Future: soul shepherd writes to L4 source files instead of deployed SOUL.md directly

## Dev Discretion

- L4 file structure: one instructions.md + one SOUL.md per role, or split into multiple sub-skill files under references/sub-skills/project/
- How to extract Project Adaptation content from existing deployed SOUL.md into L4 source
- How much vault content actually moves vs gets referenced
- Whether to create a migration script or do it manually (small number of files)

## Side Effect Mitigations (required)

- Do NOT delete vault notes — they become reference material
- Do NOT break soul_adaptation.py — it must write to L4 source going forward, not the deployed file
- Existing agent behavior must not change after migration — same content, different source location
- Run compose.py deploy-all after migration to verify output is identical

## Out of Scope

- Changing the vault system (#4208 handles vault-remember scope change separately)
- Harness/event bus (#4439)
- New presets or L3 content
- Setup wizard changes (#4083 handles that)
