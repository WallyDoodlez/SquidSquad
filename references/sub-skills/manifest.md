# Sub-skill Composition Manifest

This manifest defines how sub-skill source files compose into agent templates. The composition engine reads each role's entry file, resolves `{{include: path}}` directives by inlining the referenced sub-skill content, and wraps each inclusion with `<!-- sub-skill: name -->` section markers.

## Architecture

- **Source files**: `references/sub-skills/` (this directory)
- **Composition**: Build-time (during setup and upgrade), not runtime
- **Output**: `references/agent-instructions.md` (generated, DO NOT EDIT)
- **Final templates**: `.squidsquad/templates/*.md` (generated from composed output with placeholder substitution)

## Composition Order

### Dev Agent (`roles/dev-agent.md`)

Entry file with includes:
0. `souls/dev` — Soul (first include — colors everything)
1. `common/pull-latest` — Step 1
2. `common/context-pressure` — Step 1b
3. `common/resume-working-state` — Step 1c
4. `common/interval-sync` — Step 1d
5. `common/improvement-scan` — Quiet-cycle improvement scanning
6. `common/vault-protocol` — Vault operations
7. `common/working-state` — Working State File format

### PM/QA Agent (`roles/pm-agent.md`) — used when QA agent is NOT present

Entry file with includes (Steps 1b, 1c, Working State are inlined with hardcoded `pm` paths to avoid `[ROLE]` ambiguity — PM uses `[ROLE]` to reference dev agents, not itself):
0. `souls/pm` — Soul (first include)
1. `common/pull-latest` — Step 1
2. `pm-specific/pr-flow` — Step 6b
3. `pm-specific/delivery-fallback` — Step 6d
4. `pm-specific/github-issues` — Step 7b
5. `common/improvement-scan` — Quiet-cycle improvement scanning
6. `pm-specific/feature-intake` — Feature Lifecycle (5-Phase) + Open Artifacts in Editor
7. `pm-specific/feature-approval` — Feature Approval Gate
8. `common/vault-protocol` — Vault operations

### PM Agent — Lean (`roles/pm-lean.md`) — used when QA agent IS present

Reduced PM template without verification steps. Setup/upgrade selects this variant when `.squidsquad/qa/` directory exists.
0. `souls/pm` — Soul (first include — same PM soul)
1. `common/pull-latest` — Step 1
2. `pm-specific/delivery-fallback` — Step 3 (delivery fallback when DM absent)
3. `pm-specific/github-issues` — GitHub Issues ingestion
4. `common/improvement-scan` — Quiet-cycle improvement scanning
5. `pm-specific/feature-intake` — Feature Lifecycle (5-Phase) + Open Artifacts in Editor
6. `pm-specific/feature-approval` — Feature Approval Gate
7. `common/vault-protocol` — Vault operations

### QA Agent (`roles/qa-agent.md`) — recommended when dev/designer agents exist

Entry file with includes:
0. `souls/qa` — Soul (first include)
1. `common/pull-latest` — Step 1
2. `qa-specific/verification` — Steps 2-6 (E2E tests, bug investigation, verification, health check)
3. `common/improvement-scan` — Quiet-cycle improvement scanning
4. `common/vault-protocol` — Vault operations

### Designer Agent (`roles/designer.md`)

Entry file with includes (Steps 1b, 1c, 1d, Working State are inlined with hardcoded `designer` paths — Designer uses `[ROLE]` to reference dev agents, not itself):
0. `souls/designer` — Soul (first include)
1. `common/pull-latest` — Step 1
2. `designer-specific/design-session` — Steps 2-2e (design request scanning, feasibility, interactive session, spec production, rejection handling)
3. `common/improvement-scan` — Quiet-cycle improvement scanning
4. `designer-specific/design-tools` — Design tool integration and discovery
5. `common/vault-protocol` — Vault operations

### DM Agent (`roles/dm-agent.md`)

Entry file with includes (Steps 1b, 1c, 1d, Working State are inlined with hardcoded `dm` paths — DM uses `[ROLE]` to reference dev agents, not itself):
0. `souls/dm` — Soul (first include)
1. `common/pull-latest` — Step 1
2. `dm-specific/delivery-packaging` — Steps 2-2c
3. `dm-specific/version-bumps` — Step 3
4. `common/improvement-scan` — Quiet-cycle improvement scanning
5. `common/vault-protocol` — Vault operations

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
- **PM Open Artifacts in Editor**: Moved from standalone section to inside Feature Lifecycle (feature-intake sub-skill). Same content, more logical location.

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
│   ├── improvement-scan.md           (Quiet-cycle improvement scanning — shared by all roles)
│   └── tracker-protocol.md           (GitHub Issues tracker operations — shared by all roles)
├── souls/
│   ├── dev.md                          (Dev agent soul — pragmatic engineer)
│   ├── pm.md                           (PM soul — diplomat and strategist)
│   ├── qa.md                           (QA soul — evidence-first skeptic)
│   ├── designer.md                     (Designer soul — creative collaborator)
│   └── dm.md                           (DM soul — user-centric delivery)
├── roles/
│   ├── dev-agent.md                    (entry file — dev template skeleton)
│   ├── pm-agent.md                     (entry file — PM/QA template, no QA agent)
│   ├── pm-lean.md                      (entry file — lean PM template, QA present)
│   ├── qa-agent.md                     (entry file — QA template skeleton)
│   ├── dm-agent.md                     (entry file — DM template skeleton)
│   └── designer.md                     (entry file — designer template skeleton)
├── pm-specific/
│   ├── feature-intake.md              (5-phase lifecycle + Open Artifacts)
│   ├── feature-approval.md            (Feature Approval Gate)
│   ├── delivery-fallback.md           (Step 6d — PM delivery when DM absent)
│   ├── github-issues.md              (Step 7b — GitHub Issues ingestion)
│   └── pr-flow.md                     (Step 6b — PR monitoring)
├── qa-specific/
│   └── verification.md               (Steps 2-6 — E2E, bugs, verify, health check)
├── designer-specific/
│   ├── design-session.md             (Steps 2-2e — requests, feasibility, session, specs, rejection)
│   └── design-tools.md              (Design tool integration and discovery)
└── dm-specific/
    ├── delivery-packaging.md          (Steps 2-2c — scan, skip, deliver)
    └── version-bumps.md              (Step 3 — version bump check + sequence)
```
