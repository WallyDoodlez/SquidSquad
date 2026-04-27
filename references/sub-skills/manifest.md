# Sub-skill Composition Manifest

This manifest defines how shared sub-skill source files compose into agent templates. The composition engine reads each role's entry file, resolves `{{include: path}}` directives by inlining the referenced sub-skill content, and wraps each inclusion with `<!-- sub-skill: name -->` section markers.

## Architecture

- **Role templates** (entry files): `references/roles/<role>/CLAUDE.md` — one self-contained role directory per role, added in #328 Q-new22.
- **Role souls** (identity): `references/roles/<role>/SOUL.md` — copied verbatim (not composed) to `.squidsquad/<role>/SOUL.md` at install time.
- **Shared sub-skills** (source files): `references/sub-skills/` (this directory) — cross-cutting behaviour (tracker, vault, improvement scan, git commit, etc.) composed into each role's CLAUDE.md.
- **Composition**: Build-time (during setup and upgrade), not runtime
- **Output**: `references/agent-instructions.md` (generated, DO NOT EDIT)
- **Final templates**: `.squidsquad/<role>/CLAUDE.md` (generated from composed output with placeholder substitution)

> **Legacy location retired (Q-new22, 2026-04-11)**: Role CLAUDE.md and SOUL.md templates used to live under `references/sub-skills/{roles,souls}/`. They are now inside each role's own directory at `references/roles/<role>/`. `pm-lean.md` was retired in the same change — the task-approval and verification behaviours remain in the main PM CLAUDE.md and are driven by which other roles are installed at runtime.

## Composition Order

### Dev Agent (`references/roles/dev/CLAUDE.md`)

Entry file with includes (the role's own `SOUL.md` sits alongside `CLAUDE.md` in the role directory and is copied verbatim to `.squidsquad/<role>/SOUL.md` at install time — it is NOT listed in the include order because it is not composed):
1. `common/tracker-protocol` — GitHub Issues tracker operations
2. `common/pull-latest` — Step 1
3. `common/context-pressure` — Step 1b
4. `common/resume-working-state` — Step 1c
5. `common/interval-sync` — Step 1d
5b. `dev-specific/triage-issues` — Step 2: triage open issues
5c. `dev-specific/implement-tasks` — Step 3: implement approved tasks
6. `common/boot-remote-agents` — Boot stalled/missing agents in new terminals
7. `common/improvement-scan` — Quiet-cycle improvement scanning
8. `common/iteration-log` — Step 4: iteration log format and cleanup
8b. `common/vault-remember` — Step 4b: end-of-cycle vault reflection
8c. `common/vault-optimize` — Vault optimization on quiet cycles
9. `common/git-commit` — Step 5: commit/push protocol with PR flow
9b. `common/self-restart` — Context-pressure self-restart at cycle end
9c. `common/agent-lifecycle` — Agent lifecycle management (reboot, heartbeat, singleton)
9. `common/discussion-protocol` — Discussion entry format and rules
10. `common/issue-filing` — Self-file and cross-file bug templates
11. `common/working-state` — Working State File format
12. `common/vault-protocol` — Vault operations
13. `common/file-conventions` — File/directory conventions
14. `common/status-line` — Status line description
15. `common/prohibitions` — "Never do" rules
16. `common/cycle-runner` — (optional, feature-flagged) Cycle runner transport layer
17. `common/chat-etiquette` — (optional, comms-layer) Chat room behavior rules
18. `common/mention-protocol` — (optional, comms-layer) @mention escalation tiers and noise budget
19. `common/consensus-protocol` — (optional, comms-layer) Multi-party decision flow in chat

### PM/QA Agent (`references/roles/pm/CLAUDE.md`)

Entry file with includes (Steps 1b, 1c, Working State are inlined with hardcoded `pm` paths to avoid `[ROLE]` ambiguity — PM uses `[ROLE]` to reference dev agents, not itself). PM's `SOUL.md` sits alongside its `CLAUDE.md` and is copied verbatim at install time.
1. `common/tracker-protocol` — GitHub Issues tracker operations
2. `common/pull-latest` — Step 1
2b. `pm-specific/checkin` — Step 2: human check-in and input handling
2c. `pm-specific/testing-and-verification` — Steps 3-6c: E2E, investigate, verify issues/tasks, ship counter
3. `pm-specific/delivery-fallback` — Step 6d: PM delivery when DM absent
3b. `pm-specific/post-merge-recompose` — Step 6e: recompose after branch merge
3c. `pm-specific/pipeline-sentinel` — Step 6f: always-run pipeline health (conflict detection, stall detection, PR status sync)
3d. `pm-specific/own-domain-autofix` — PM auto-fixes own-domain mechanical issues (BRIEFING staleness, config drift) immediately
4b. `pm-specific/health-check` — Step 7: agent health check
5. `pm-specific/github-issues` — Step 7b
5b. `common/boot-remote-agents` — Boot stalled/missing agents in new terminals
5c. `pm-specific/soul-shepherd` — Soul shepherd: character signal detection per task
6. `common/improvement-scan` — Quiet-cycle improvement scanning
7. `pm-specific/iteration-log` — Step 8: PM/QA iteration log
7b. `common/vault-remember` — Step 8b: end-of-cycle vault reflection
7c. `common/vault-optimize` — Vault optimization on quiet cycles
7d. `pm-specific/vault-synthesis` — Vault synthesis: cross-agent pattern detection and posture emergence (5-cycle trigger)
7e. `pm-specific/improvement-scan` — PM-specific improvement scanning (process/workflow focus, not code)
8. `pm-specific/git-commit` — Step 9: commit/push
9. `pm-specific/issue-filing` — Bug Filing Protocol
10. `pm-specific/task-intake` — Feature Lifecycle (5-Phase) + Open Artifacts in Editor
11. `pm-specific/task-approval` — Feature Approval Gate
12. `pm-specific/discussion-protocol` — Discussion entry format (pm/qa alias)
13. `common/vault-protocol` — Vault operations
14. `pm-specific/file-conventions` — PM file/directory conventions
15. `pm-specific/status-line` — PM status line description
16. `pm-specific/prohibitions` — PM "never do" rules

### QA Agent (`references/roles/qa/CLAUDE.md`) — recommended when dev/designer agents exist

Entry file with includes:
   (QA's `SOUL.md` lives at `references/roles/qa/SOUL.md` and is copied verbatim at install time.)
1. `common/tracker-protocol` — GitHub Issues tracker operations
2. `common/pull-latest` — Step 1
3. `qa-specific/verification` — Steps 2-6 (E2E tests, bug investigation, verification, health check)
3b. `common/boot-remote-agents` — Boot stalled/missing agents in new terminals
4. `common/improvement-scan-slim` — Improvement filing only (slim variant)
5. `qa-specific/iteration-log` — Step 7: QA iteration log
6. `qa-specific/git-commit` — Step 8: commit/push
7. `qa-specific/issue-filing` — QA Bug Filing Protocol
8. `qa-specific/discussion-protocol` — Discussion entry format (qa alias)
9. `common/vault-protocol-slim` — Vault read-only operations (slim variant)
10. `qa-specific/file-conventions` — QA file/directory conventions
11. `qa-specific/status-line` — QA status line description
12. `qa-specific/prohibitions` — QA "never do" rules

### Designer Agent (`references/roles/designer/CLAUDE.md`)

Entry file with includes (Steps 1b, 1c, 1d, Working State are inlined with hardcoded `designer` paths — Designer uses `[ROLE]` to reference dev agents, not itself):
   (Designer's `SOUL.md` lives at `references/roles/designer/SOUL.md` and is copied verbatim at install time.)
1. `common/tracker-protocol` — GitHub Issues tracker operations
2. `common/pull-latest` — Step 1
2b. `common/capability-check` — Startup capability verification
3. `designer-specific/design-session` — Steps 2-2e (design request scanning, feasibility, interactive session, spec production, rejection handling)
3b. `common/boot-remote-agents` — Boot stalled/missing agents in new terminals
4. `common/improvement-scan-slim` — Improvement filing only (slim variant)
5. `designer-specific/iteration-log` — Step 3: designer iteration log
6. `designer-specific/git-commit` — Step 4: commit/push
7. `designer-specific/discussion-protocol` — Discussion entry format (designer alias)
8. `designer-specific/design-capabilities` — Design capability integration and discovery
9. `designer-specific/issue-filing` — Designer bug/feature filing
10. `common/vault-protocol-slim` — Vault read-only operations (slim variant)
11. `designer-specific/file-conventions` — Designer file/directory conventions
12. `designer-specific/status-line` — Designer status line description
13. `designer-specific/prohibitions` — Designer "never do" rules

### DM Agent (`references/roles/dm/CLAUDE.md`)

Entry file with includes (Steps 1b, 1c, 1d, Working State are inlined with hardcoded `dm` paths — DM uses `[ROLE]` to reference dev agents, not itself):
   (DM's `SOUL.md` lives at `references/roles/dm/SOUL.md` and is copied verbatim at install time.)
1. `common/tracker-protocol` — GitHub Issues tracker operations
2. `common/pull-latest` — Step 1
3. `dm-specific/issue-triage` — Step 1e: triage bugs assigned to DM
4. `dm-specific/delivery-packaging` — Steps 2-2c
4. `dm-specific/version-bumps` — Step 3
4b. `common/boot-remote-agents` — Boot stalled/missing agents in new terminals
5. `common/improvement-scan-slim` — Improvement filing only (slim variant)
6. `dm-specific/iteration-log` — Step 4: DM iteration log
7. `dm-specific/git-commit` — Step 5: commit/push
8. `dm-specific/discussion-protocol` — Discussion entry format (dm alias)
9. `dm-specific/issue-filing` — DM bug/feature filing
10. `common/vault-protocol-slim` — Vault read-only operations (slim variant)
11. `dm-specific/file-conventions` — DM file/directory conventions
12. `dm-specific/status-line` — DM status line description
13. `dm-specific/prohibitions` — DM "never do" rules

## Include Directive Format

```
{{include: relative/path}}
```

- Path is relative to `references/sub-skills/`
- `.md` extension is omitted in directives
- Each resolved include is wrapped with: `<!-- sub-skill: [filename-without-ext] -->`
- Directives must appear on their own line

## Placeholder Substitution (after composition)

After all includes are resolved, substitute placeholders for the target role:

| Placeholder | Dev | PM | DM |
|-------------|-----|-----|-----|
| `[ROLE]` | role name (e.g. `skill`) | not substituted (used as dev agent variable) | not substituted (used as dev agent variable) |
| `[ROLE_UPPER]` | uppercase (e.g. `SKILL`) | not substituted | not substituted |
| `[ROLE_TEST_CMD]` | from config | N/A | N/A |
| `[OTHER_ROLES]` | other dev roles | N/A | N/A |
| `[INTERVAL]` | from config | from config | from config |
| `[ACTIVE_AGENTS]` | N/A | from config | from config |
| `[E2E_TEST_CMD]` | N/A | from config | N/A |

**Note on `[ROLE]` ambiguity**: In dev templates, `[ROLE]` refers to this agent and is substituted. In PM/DM templates, `[ROLE]` is a template variable meaning "any dev agent's role" and is NOT substituted. Common sub-skills that reference paths (context-pressure, resume-working-state, working-state) use `[ROLE]` and are therefore only shared with dev agents. PM and DM inline these sections with hardcoded paths.

## Intentional Differences from Monolithic Templates

- **PM/DM Step 1 (Pull Latest)**: Now includes "append the conflicting section below the existing one" (previously only in dev template). Functional improvement.
- **PM Open Artifacts in Editor**: Moved from standalone section to inside Feature Lifecycle (task-intake sub-skill). Same content, more logical location.

## Sub-skill File Inventory

```
references/sub-skills/
├── manifest.md                         (this file)
├── common/
│   ├── pull-latest.md                  (Step 1 — shared by all roles)
│   ├── context-pressure.md             (Step 1b — shared by dev only)
│   ├── resume-working-state.md         (Step 1c — shared by dev only)
│   ├── interval-sync.md               (Step 1d — shared by dev only)
│   ├── working-state.md               (Working State — shared by dev only)
│   ├── vault-protocol.md             (Vault operations — shared by all roles)
│   ├── boot-remote-agents.md         (Boot stalled/missing agents — shared by all roles)
│   ├── improvement-scan.md           (Quiet-cycle improvement scanning — shared by all roles)
│   ├── tracker-protocol.md           (GitHub Issues tracker operations — shared by all roles)
│   ├── iteration-log.md              (Step 4 — iteration log format + cleanup — shared by dev)
│   ├── git-commit.md                 (Step 5 — commit/push + PR flow — shared by dev)
│   ├── discussion-protocol.md        (Discussion entry format — shared by dev)
│   ├── issue-filing.md                 (Self-file + cross-file bug templates — shared by dev)
│   ├── file-conventions.md           (File/directory conventions — shared by dev)
│   ├── vault-remember.md             (Step 4b — end-of-cycle vault reflection — PM + dev only)
│   ├── vault-optimize.md            (Vault optimization on quiet cycles — PM + dev only)
│   ├── vault-protocol-slim.md       (Vault read-only operations — QA, DM, designer)
│   ├── improvement-scan-slim.md     (Improvement filing only — QA, DM, designer)
│   ├── status-line.md                (Status line description — shared by dev)
│   ├── prohibitions.md               (Shared "never do" rules — shared by dev)
│   ├── capability-check.md          (Startup capability verification — shared by roles with requires_sub_skills)
│   ├── cycle-runner.md              (Cycle runner transport layer — opt-in via feature flag, all roles)
│   └── agent-lifecycle.md           (Agent lifecycle: reboot, heartbeat, singleton — all roles)
├── dev-specific/
│   ├── triage-issues.md              (Step 2 — triage open issues)
│   └── implement-tasks.md           (Step 3 — implement approved tasks)
├── pm-specific/
│   ├── checkin.md                  (Step 2 — human check-in and input handling)
│   ├── testing-and-verification.md (Steps 3-6c — E2E, investigate, verify, ship counter)
│   ├── health-check.md            (Step 7 — agent health check)
│   ├── post-merge-recompose.md    (Step 6e — recompose after branch merge)
│   ├── task-intake.md              (5-phase lifecycle + Open Artifacts)
│   ├── task-approval.md            (Feature Approval Gate)
│   ├── delivery-fallback.md           (Step 6d — PM delivery when DM absent)
│   ├── discussion-protocol.md        (Discussion — pm/qa alias)
│   ├── issue-filing.md                 (Bug Filing Protocol)
│   ├── file-conventions.md           (PM file conventions)
│   ├── status-line.md                (PM status line)
│   ├── prohibitions.md               (PM "never do" rules)
│   ├── iteration-log.md             (Step 8 — PM/QA iteration log)
│   ├── git-commit.md                (Step 9 — PM commit/push)
│   ├── github-issues.md              (Step 7b — GitHub Issues ingestion)
│   ├── pipeline-sentinel.md           (Step 6f — pipeline health, always runs)
│   ├── soul-shepherd.md              (Soul shepherd — character signal detection per task)
│   ├── vault-synthesis.md            (Vault synthesis — cross-agent posture emergence)
│   └── improvement-scan.md           (PM-specific improvement scan — process/workflow focus)
├── qa-specific/
│   ├── verification.md               (Steps 2-6 — E2E, bugs, verify, health check)
│   ├── discussion-protocol.md        (Discussion — qa alias)
│   ├── issue-filing.md                 (QA Bug Filing Protocol)
│   ├── file-conventions.md           (QA file conventions)
│   ├── status-line.md                (QA status line)
│   ├── prohibitions.md               (QA "never do" rules)
│   ├── iteration-log.md             (Step 7 — QA iteration log)
│   └── git-commit.md                (Step 8 — QA commit/push)
├── designer-specific/
│   ├── design-session.md             (Steps 2-2e — requests, feasibility, session, specs, rejection)
│   ├── design-capabilities.md        (Design capability integration and discovery)
│   ├── discussion-protocol.md        (Discussion — designer alias)
│   ├── issue-filing.md                 (Designer bug/feature filing)
│   ├── file-conventions.md           (Designer file conventions)
│   ├── status-line.md                (Designer status line)
│   ├── prohibitions.md               (Designer "never do" rules)
│   ├── iteration-log.md             (Step 3 — designer iteration log)
│   └── git-commit.md                (Step 4 — designer commit/push)
└── dm-specific/
    ├── issue-triage.md                (Step 1e — triage bugs assigned to DM)
    ├── delivery-packaging.md          (Steps 2-2c — scan, skip, deliver)
    ├── version-bumps.md              (Step 3 — version bump check + sequence)
    ├── discussion-protocol.md        (Discussion — dm alias)
    ├── issue-filing.md                 (DM bug/feature filing)
    ├── file-conventions.md           (DM file conventions)
    ├── status-line.md                (DM status line)
    ├── prohibitions.md               (DM "never do" rules)
    ├── iteration-log.md             (Step 4 — DM iteration log)
    └── git-commit.md                (Step 5 — DM commit/push)
```
