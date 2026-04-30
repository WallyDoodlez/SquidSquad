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

Entry file with includes (the role's own `SOUL.md` sits alongside `CLAUDE.md` in the role directory and is copied verbatim to `.squidsquad/<role>/SOUL.md` at install time — it is NOT listed in the include order because it is not composed). **Source of truth**: `references/roles/dev/includes.yml`.

1. `common/tracker-protocol` — GitHub Issues tracker operations
2. `common/cycle-runner` — Cycle runner transport layer (pre/post cycle mechanical operations)
3. `common/context-pressure` — Step 1b: context pressure check
4. `common/resume-working-state` — Step 1c: resume from working state
5. `common/interval-sync` — Step 1d: interval sync
6. `roles/dev/triage-issues` — Step 2: deterministic work queue triage
7. `roles/dev/implement-tasks` — Step 2b: implement approved tasks
8. `common/improvement-scan` — Quiet-cycle improvement scanning
9. `common/vault-remember` — Step 4b: end-of-cycle vault reflection
10. `common/vault-optimize` — Vault optimization on quiet cycles
11. `common/git-commit` — Step 5: commit/push protocol with PR flow
12. `common/discussion-protocol` — Discussion entry format and rules
13. `common/issue-filing` — Self-file and cross-file bug templates
14. `common/working-state` — Working State File format
15. `common/vault-protocol` — Vault operations
16. `common/file-conventions` — File/directory conventions
17. `common/status-line` — Status line description
18. `common/self-restart` — Context-pressure self-restart at cycle end
19. `common/agent-lifecycle` — Agent lifecycle management (reboot, heartbeat, singleton)
20. `common/prohibitions` — "Never do" rules

Optional (comms-layer, not yet included by default):
- `common/chat-etiquette` — Chat room behavior rules
- `common/mention-protocol` — @mention escalation tiers and noise budget
- `common/consensus-protocol` — Multi-party decision flow in chat

### PM Agent (`references/roles/pm/CLAUDE.md`)

Entry file with includes. PM's `SOUL.md` sits alongside its `CLAUDE.md` and is copied verbatim at install time. **Source of truth**: `references/roles/pm/includes.yml`.

1. `common/tracker-protocol` — GitHub Issues tracker operations
2. `common/cycle-runner` — Cycle runner transport layer
3. `common/context-pressure` — Context pressure check
4. `roles/pm/checkin` — Step 2: human check-in and input handling
5. `roles/pm/testing-and-verification` — Steps 3-6c: E2E, investigate, verify issues/tasks, ship counter
6. `roles/pm/delivery-fallback` — Step 6d: PM delivery when DM absent
7. `roles/pm/post-merge-recompose` — Step 6e: recompose after branch merge
8. `roles/pm/pipeline-sentinel` — Step 6f: pipeline health (conflict, stall, PR sync)
9. `roles/pm/own-domain-autofix` — Auto-fix own-domain mechanical issues
10. `roles/pm/health-check` — Step 7: agent health check
11. `roles/pm/github-issues` — Step 7b: GitHub Issues management
12. `common/boot-remote-agents` — Boot stalled/missing agents
13. `roles/pm/soul-shepherd` — Soul shepherd: character signal detection
14. `roles/pm/improvement-scan` — PM-specific improvement scanning (process focus)
15. `common/vault-remember` — End-of-cycle vault reflection
16. `common/vault-optimize` — Vault optimization on quiet cycles
17. `roles/pm/vault-synthesis` — Cross-agent pattern detection
18. `roles/pm/issue-filing` — Bug Filing Protocol
19. `roles/pm/task-intake` — Feature Lifecycle (5-Phase)
20. `roles/pm/task-approval` — Feature Approval Gate
21. `roles/pm/discussion-protocol` — Discussion entry format
22. `common/vault-protocol` — Vault operations
23. `roles/pm/file-conventions` — PM file/directory conventions
24. `roles/pm/status-line` — PM status line description
25. `common/self-restart` — Self-restart
26. `common/agent-lifecycle` — Agent lifecycle
27. `roles/pm/prohibitions` — PM "never do" rules

### QA Agent (`references/roles/qa/CLAUDE.md`)

Entry file with includes. **Source of truth**: `references/roles/qa/includes.yml`.

1. `common/tracker-protocol` — GitHub Issues tracker operations
2. `common/cycle-runner` — Cycle runner transport layer
3. `common/context-pressure` — Context pressure check
4. `roles/qa/verification` — Steps 2-6: E2E tests, verification, health check
5. `common/improvement-scan-slim` — Improvement filing only (slim variant)
6. `roles/qa/issue-filing` — QA Bug Filing Protocol
7. `roles/qa/discussion-protocol` — Discussion entry format
8. `common/vault-protocol-slim` — Vault read-only operations (slim variant)
9. `roles/qa/file-conventions` — QA file/directory conventions
10. `roles/qa/status-line` — QA status line description
11. `common/self-restart` — Self-restart
12. `common/agent-lifecycle` — Agent lifecycle
13. `roles/qa/prohibitions` — QA "never do" rules

### Designer Agent (`references/roles/designer/CLAUDE.md`)

Entry file with includes. **Source of truth**: `references/roles/designer/includes.yml`.

1. `common/tracker-protocol` — GitHub Issues tracker operations
2. `common/capability-check` — Startup capability verification
3. `common/cycle-runner` — Cycle runner transport layer
4. `common/context-pressure` — Context pressure check
5. `roles/designer/design-session` — Design request scanning, feasibility, interactive session, spec production
6. `common/improvement-scan-slim` — Improvement filing only (slim variant)
7. `roles/designer/discussion-protocol` — Discussion entry format
8. `roles/designer/design-capabilities` — Design capability integration and discovery
9. `roles/designer/issue-filing` — Designer bug/feature filing
10. `common/vault-protocol-slim` — Vault read-only operations (slim variant)
11. `roles/designer/file-conventions` — Designer file/directory conventions
12. `roles/designer/status-line` — Designer status line description
13. `common/self-restart` — Self-restart
14. `common/agent-lifecycle` — Agent lifecycle
15. `roles/designer/prohibitions` — Designer "never do" rules

### DM Agent (`references/roles/dm/CLAUDE.md`)

Entry file with includes. **Source of truth**: `references/roles/dm/includes.yml`.

1. `common/tracker-protocol` — GitHub Issues tracker operations
2. `common/capability-check` — Startup capability verification
3. `common/cycle-runner` — Cycle runner transport layer
4. `common/context-pressure` — Context pressure check
5. `roles/dm/issue-triage` — Triage bugs assigned to DM
6. `roles/dm/delivery-packaging` — Delivery packaging
7. `roles/dm/version-bumps` — Version bump check + sequence
8. `common/improvement-scan-slim` — Improvement filing only (slim variant)
9. `roles/dm/discussion-protocol` — Discussion entry format
10. `roles/dm/issue-filing` — DM bug/feature filing
11. `common/vault-protocol-slim` — Vault read-only operations (slim variant)
12. `roles/dm/file-conventions` — DM file/directory conventions
13. `roles/dm/status-line` — DM status line description
14. `common/self-restart` — Self-restart
15. `common/agent-lifecycle` — Agent lifecycle
16. `roles/dm/prohibitions` — DM "never do" rules

### Legacy Sub-Skills (not included by any role)

These files exist on disk but are no longer referenced by any role's includes.yml after the cycle-runner migration (#2487). cycle-runner and cycle_post.py handle their responsibilities. Kept for reference; may be deleted in a future cleanup.

- `common/pull-latest` — replaced by cycle_pre.py git pull
- `common/iteration-log` — replaced by cycle_post.py iteration logging
- ~~roles/pm/iteration-log~~ — deleted (#3499), replaced by cycle_post.py
- ~~roles/pm/git-commit~~ — deleted (#3499), replaced by cycle_post.py
- `roles/qa/iteration-log` — replaced by cycle_post.py
- `roles/qa/git-commit` — replaced by cycle_post.py
- `roles/dm/iteration-log` — replaced by cycle_post.py
- `roles/dm/git-commit` — replaced by cycle_post.py
- `roles/designer/iteration-log` — replaced by cycle_post.py
- `roles/designer/git-commit` — replaced by cycle_post.py

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
│   ├── agent-lifecycle.md           (Agent lifecycle: reboot, heartbeat, singleton — all roles)
│   ├── self-restart.md              (Context-pressure self-restart — all roles)
│   ├── chat-etiquette.md            (Chat room behavior rules — comms-layer, optional)
│   ├── mention-protocol.md          (@mention escalation tiers and noise budget — comms-layer, optional)
│   └── consensus-protocol.md        (Multi-party decision flow in chat — comms-layer, optional)
├── roles/dev/
│   ├── triage-issues.md              (Step 2 — triage open issues)
│   └── implement-tasks.md           (Step 3 — implement approved tasks)
├── roles/pm/
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
├── roles/qa/
│   ├── verification.md               (Steps 2-6 — E2E, bugs, verify, health check)
│   ├── discussion-protocol.md        (Discussion — qa alias)
│   ├── issue-filing.md                 (QA Bug Filing Protocol)
│   ├── file-conventions.md           (QA file conventions)
│   ├── status-line.md                (QA status line)
│   ├── prohibitions.md               (QA "never do" rules)
│   ├── iteration-log.md             (Step 7 — QA iteration log)
│   └── git-commit.md                (Step 8 — QA commit/push)
├── roles/designer/
│   ├── design-session.md             (Steps 2-2e — requests, feasibility, session, specs, rejection)
│   ├── design-capabilities.md        (Design capability integration and discovery)
│   ├── discussion-protocol.md        (Discussion — designer alias)
│   ├── issue-filing.md                 (Designer bug/feature filing)
│   ├── file-conventions.md           (Designer file conventions)
│   ├── status-line.md                (Designer status line)
│   ├── prohibitions.md               (Designer "never do" rules)
│   ├── iteration-log.md             (Step 3 — designer iteration log)
│   └── git-commit.md                (Step 4 — designer commit/push)
└── roles/dm/
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
