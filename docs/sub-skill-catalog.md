# Sub-Skill Catalog

This document is the reference catalog of sub-skills that compose into SquidSquad's role agents. It pairs with [`sub-skill-guide.md`](sub-skill-guide.md) (how to author them) and [`COMPOSE-ARCHITECTURE.md`](COMPOSE-ARCHITECTURE.md) (how composition works mechanically).

---

## What is a Sub-Skill?

A **sub-skill** is a self-contained unit of agent functionality — a focused capability like "run pre-cycle git pull", "react to a PR-merged event", or "file a bug to the right role's tracker". Sub-skills are referenced from a role agent's composed CLAUDE.md and supply the actual how-to for one piece of behavior.

### Relationship to SquidSquad

The full picture:

```
┌──────────────────────────────────────────────────┐
│                  SquidSquad                      │  ← main skill (orchestrator)
│  (skill registration, harness, install/upgrade)  │
└──────────────────────────────────────────────────┘
            │ ships
            ▼
┌──────────────────────────────────────────────────┐
│         L1–L4 instruction documents              │  ← layered by specificity
│   L1 universal → L2 role → L3 variant → L4       │
│   project-local install                          │
└──────────────────────────────────────────────────┘
            │ compose merges into one CLAUDE.md per agent
            ▼
┌──────────────────────────────────────────────────┐
│       Composed .squidsquad/<role>/CLAUDE.md      │  ← powers one role agent
│       (PM / QA / DM / dev)                       │
└──────────────────────────────────────────────────┘
            │ references
            ▼
┌──────────────────────────────────────────────────┐
│                   Sub-skills                     │  ← this catalog
│  (cycle-runner, vault-remember, pipeline-       │
│   sentinel, task-pickup, etc.)                  │
│  one unit of functionality each                  │
└──────────────────────────────────────────────────┘
```

How to read this:

1. **SquidSquad** is the main skill — it ships the L1-L4 source documents, the compose pipeline, the harness, and the install/upgrade flow.
2. **L1-L4** are documents of varying **specificity of functionality**:
   - **L1** — universal (what *any* SquidSquad agent is; applies to all roles, all installs)
   - **L2** — role-specific (what a PM / QA / DM / dev does)
   - **L3** — role variant (e.g. a dev specialized for a particular stack, or a PM with a project-shipped overlay)
   - **L4** — project-local install (lives in `.squidsquad/project/`; authored from human conversation in a deployed install, customizes the agent for that one install)
3. **Compose** stacks L1 → L2 → L3 → L4 (least → most specific, with later layers refining earlier ones) into a **single composed CLAUDE.md per role agent**.
4. That composed CLAUDE.md **references sub-skills** — for each unit of functionality (vault writes, pipeline sentinel, cycle runner, etc.) it points at the sub-skill that defines how that functionality works.

So L1-L4 set out *what an agent's responsibilities and behaviors are at varying levels of specificity*; sub-skills provide *the focused how-to for each unit of behavior*. The composed CLAUDE.md is the bridge — it's per-agent, assembled from L1-L4, and points to sub-skills as needed.

### Current state — sub-skills are inlined markdown fragments

Today, sub-skills are **plain markdown fragments** under `references/sub-skills/`. They are NOT Claude skills yet:

- No `SKILL.md` frontmatter
- No `.claude/skills/` registration
- No Skill tool invocation

Today's "reference" is mechanical inlining: each role's `references/roles/<role>/includes.yml` declares which sub-skills are needed, and `compose.py deploy <role>` walks that list and **inlines** each sub-skill's markdown into the composed `.squidsquad/<role>/CLAUDE.md`. Sub-skill boundaries survive only as `<!-- sub-skill: name -->` HTML comments. The running agent sees one monolithic document.

This is a transitional implementation. The catalog below reflects today's inlined reality, but the catalog organization (one entry per unit of functionality) is structured to match the target state.

### Target state — real Claude skills

The direction (captured in #9968) is to convert sub-skills into **real Claude skills** with `SKILL.md` frontmatter, registered in `.claude/skills/`, and invoked by the model via the Skill tool when their description matches the situation. The composed CLAUDE.md will then *literally* reference sub-skills instead of inlining them — shrinking the per-agent CLAUDE.md from ~50KB to ~5–10KB and putting the bulk of behavior into discoverable, focused skill units.

Two tiers are anticipated:

- **Mandatory** sub-skills (cycle-runner, boot-bootstrap, context-pressure, status-transitions) — MUST execute every cycle/boot. Likely remain inlined into the small composed CLAUDE.md, because pure description-matched invocation is discretionary and cannot be relied on for procedures that have to fire deterministically.
- **Situational** sub-skills (vault-remember, improvement-scan, soul-shepherd, issue-filing, code-review, etc.) — only fire when conditions match. These are the natural fit for the Claude skill mechanism: each becomes a discoverable skill the model invokes when its description aligns with the current task.

Until that conversion ships, every sub-skill listed below is still an inlined markdown fragment, and the "used by" column reflects which role's `includes.yml` consumes it.

---

## Catalog organization

Sub-skills live in five source directories under `references/sub-skills/`:

| Directory | Audience | Composition behavior |
|---|---|---|
| `common/` | reusable across roles | inlined at compose time into each consuming role's CLAUDE.md |
| `common-events/` | roles in event-driven mode | **runtime-loaded** by `boot-bootstrap` on session start (not inlined) |
| `roles/<role>/` | one role | inlined at compose time |
| `project/` | seed templates for L4 | copied to `.squidsquad/project/` at install (not consumed by compose) |
| `capabilities/<tool>/` | roles that bind to a specific tool | inlined at compose time, gated by `common/capability-check` |

---

## `common/` — Cross-cutting sub-skills

Reusable across multiple roles.

### Boot & cycle transport

| Sub-skill | One-liner | Used by |
|---|---|---|
| `boot-bootstrap` | Mode detection on session start (polling vs event); reads the right runtime fragments | PM, QA, DM, dev |
| `cycle-runner` | 3-phase cycle (pre/creative/post) wired to `cycle_pre.py` and `cycle_post.py` | PM, QA, DM, dev |
| `context-pressure` | Read `.squidsquad/<role>/context-pressure`; checkpoint and signal exit-42 above threshold | PM, QA, DM, dev |
| `task-pickup` | Pick up next approved task from the role's tracker query | PM, QA, dev (DM uses role variant) |
| `resume-working-state` | Resume in-flight work from `working-state.md` on cycle entry | dev |
| `interval-sync` | Honor the configured cycle interval | dev |
| `self-restart` | Detect context-pressure exit and let the harness respawn | PM, QA, DM, dev |
| `agent-lifecycle` | Heartbeat, singleton enforcement, reboot signaling | PM, QA, DM, dev |
| `boot-remote-agents` | PM-only: spawn stalled agents via `boot_remote.py` when the harness can't | PM |

### Tracker & coordination

| Sub-skill | One-liner | Used by |
|---|---|---|
| `agent-boundaries` | "Know your teammates" — declines route to the right role, not generic "not mine" | PM, QA, DM, dev |
| `discussion-protocol` | Append-only tracker comment format | dev (roles override) |
| `issue-filing` | Self-file and cross-file bug templates | dev (roles override) |
| `working-state` | Working-state file format and update rules | dev |
| `pickup-comment-fidelity` | Pickup comments must accurately reflect tracker state | dev |
| `prohibitions` | "Never do" rules (no force push, no skip hooks, etc.) | dev (roles override) |
| `file-conventions` | Where things go on disk — overridable per role | dev (roles override) |
| `status-line` | What the statusline shows during a cycle — overridable per role | dev (roles override) |

### Vault (institutional memory)

| Sub-skill | One-liner | Used by |
|---|---|---|
| `vault-remember` | End-of-cycle reflection; writes to vault when something is worth remembering | PM, dev |
| `vault-optimize` | On quiet cycles, compact and de-dup vault entries | PM, dev |
| `vault-protocol` | Full vault R/W protocol | PM, dev |
| `vault-protocol-slim` | Read-only variant for QA/DM (no vault writes) | QA, DM |

### Quality, git, improvement

| Sub-skill | One-liner | Used by |
|---|---|---|
| `git-commit` | Commit/push protocol with PR flow | dev (DM has its own variant) |
| `improvement-scan` | Full proactive scan for process/template gaps | PM, dev |
| `improvement-scan-slim` | Filing-only variant (no auto-fix) for read-only roles | QA |
| `capability-check` | Verify the agent's environment has the tools it expects | DM |

### Chat & coordination (optional, not on by default)

| Sub-skill | One-liner | Used by |
|---|---|---|
| `chat-etiquette` | Behavior rules for the team chat room | (none yet) |
| `mention-protocol` | @mention escalation tiers and noise budget | (none yet) |
| `consensus-protocol` | Multi-party decision flow for chat-driven decisions | (none yet) |
| `iteration-log` | Per-cycle iteration log format | (legacy; roles use their own variant) |

---

## `common-events/` — Event-mode sub-skills

Loaded at runtime by `boot-bootstrap` when the role's `config.md` says `event-driven: yes`. **Not inlined at compose time** — read fresh on every session start so an `event-driven:` flip takes effect on next agent restart without a recompose.

| Sub-skill | One-liner |
|---|---|
| `l1-base` | Event-mode base contract (replaces polling base for that session) |
| `event-driven-workflow` | The event-listen / react / commit loop |
| `cursor-management` | Advance `last_processed_event_id`; recover from missed events |
| `forge-read-pattern` | How to read the tracker when prompted by an event vs polling |
| `idle-cooldown-loop` | What to do during idle stretches between events |
| `comment-handling` | React to incoming tracker comments as events |

Role-specific event extras:

| Sub-skill | One-liner | Used by |
|---|---|---|
| `roles/dm/events/pr-merge-wait` | DM's behavior while a PR is merging (block other delivery) | DM (event mode) |

---

## `roles/<role>/` — Role-specific sub-skills

### PM (`roles/pm/`)

| Sub-skill | One-liner |
|---|---|
| `responsibility` | What PM does and (importantly) does NOT do |
| `checkin` | Step 2 — non-blocking human check-in; issue/task/approval intake |
| `task-intake` | 5-phase feature lifecycle (Research → Discussion → Planning → human-approve → Execution) |
| `task-approval` | Feature-approval gate; planned → approved transition |
| `testing-and-verification` | Steps 3–6 — delegate to QA; PM doesn't verify |
| `delivery` | Delegate to DM; PM doesn't package |
| `pipeline-sentinel` | Step 6f — stall, conflict, PR-status, and stuck-state sweep |
| `own-domain-autofix` | Fix PM-owned mechanical drift inline; don't file bugs for self |
| `health-check` | Step 7 — agent health sweep + log to `qa-log.md` |
| `github-issues` | Step 7b — triage externally-filed issues; route to a role |
| `soul-shepherd` | Detect character signals in new tasks; update SOUL adaptations |
| `improvement-scan` | PM variant — process-focused, never code |
| `issue-filing` | PM's bug-filing protocol (behavior-only, no RCA) |
| `discussion-protocol` | PM's comment format |
| `file-conventions` | PM's on-disk file layout |
| `status-line` | PM's statusline content |
| `prohibitions` | PM "never do" rules |
| `vault-synthesis` | Cross-agent pattern detection (PM-only) |
| `ralph-loop-overview` | Runtime-loaded polling-mode cycle contract |

### QA (`roles/qa/`)

| Sub-skill | One-liner |
|---|---|
| `responsibility` | QA scope: verify against ACs, file results, don't ship |
| `verification` | Steps 2–6 — E2E tests, AC verification, health check |
| `issue-filing` | QA's bug template (with reproduction + AC reference) |
| `discussion-protocol` | QA's comment format |
| `file-conventions` | QA's planning-artifact layout (`TEST-PLAN-<n>.md`, `QA-RESULTS-<n>.md`) |
| `status-line` | QA's statusline content |
| `prohibitions` | QA "never do" rules (e.g. no shipping with failed tests) |
| `ralph-loop-overview` | Runtime-loaded polling-mode cycle contract |
| Domain context | Per-stack QA notes: `android/`, `ios/`, `web/`, `fullstack/`, `skill/` |
| `skill/finding-categories` | Skill-domain finding taxonomy for QA reports |

### DM (`roles/dm/`)

| Sub-skill | One-liner |
|---|---|
| `responsibility` | DM scope: package, ship, version-bump; never write features |
| `task-pickup` | DM's queue: pending-ship items |
| `issue-triage` | Triage DM-owned bug reports |
| `delivery-packaging` | The packaging step: docs, CHANGELOG, release notes |
| `version-bumps` | Bump rules (uses `shipped_since_bump` counter) |
| `doc-improvement-loop` | DM's scan: drift between source docs and shipped state |
| `issue-filing` | DM's bug template |
| `discussion-protocol` | DM's comment format |
| `file-conventions` | DM's on-disk layout |
| `status-line` | DM's statusline content |
| `prohibitions` | DM "never do" rules |
| `git-commit` | DM's commit/push protocol (state-only, no feature code) |
| `iteration-log` | DM's per-cycle log |
| `ralph-loop-overview` | Runtime-loaded polling-mode cycle contract |
| Domain context | Per-stack DM notes: `android/`, `ios/`, `web/`, `fullstack/`, `skill/` |

### Dev (`roles/dev/`)

| Sub-skill | One-liner |
|---|---|
| `responsibility` | Dev scope: implement, run own unit tests, hand to QA |
| `triage-issues` | Step 2 — deterministic work-queue triage |
| `implement-tasks` | Step 2b — pick up approved tasks; commit on feature branch; open PR |
| `ralph-loop-overview` | Runtime-loaded polling-mode cycle contract |
| Domain context | Per-stack dev notes: `android/`, `ios/`, `web/`, `fullstack/`, `skill/` |

---

## `project/` — L4 seed templates

These are **seed templates** copied to `.squidsquad/project/` at install time. The runtime versions in `.squidsquad/project/` are auto-included by `compose.py` as the L4 layer of the composed CLAUDE.md. The seeds in this directory are NOT consumed at compose time — they're the starting point a fresh install begins from.

| Seed | Purpose |
|---|---|
| `shared-instructions.md` | Cross-role L4 baseline (every agent sees this) |
| `shared-responsibility.md` | Cross-role L4 boundaries |
| `shared-soul-directives.md` | Cross-role L4 SOUL prepend |
| `pm-instructions.md`, `pm-responsibility.md`, `pm-soul-directives.md` | PM-only L4 overrides |
| `qa-instructions.md`, `qa-responsibility.md`, `qa-soul-directives.md` | QA-only L4 overrides |
| `dm-instructions.md`, `dm-responsibility.md`, `dm-soul-directives.md` | DM-only L4 overrides |
| `dev-instructions.md`, `dev-responsibility.md`, `dev-soul-directives.md` | dev-only L4 overrides |
| `setup-upgrade-gate.md` | Setup/upgrade gate L4 hook |

---

## `capabilities/<tool>/` — Tool-binding sub-skills

Bind a role to a specific external tool. Each capability ships with a `sub-skill.md` (the runtime behavior) and a `setup.md` (one-time configuration the human runs at install). Capability sub-skills are gated by `common/capability-check`.

| Capability | Domain | Tool |
|---|---|---|
| `figma/` | Design | Figma MCP server |
| `google_stitch/` | Design | Google Stitch |
| `local_html/` | Design | Local HTML mockups (no external tool) |
| `local_delivery/` | Delivery | Local filesystem delivery (no remote registry) |

---

## How to navigate this catalog

- Adding a new sub-skill? See [`sub-skill-guide.md`](sub-skill-guide.md) and update both `references/sub-skills/manifest.md` and this catalog.
- Wiring a sub-skill into a role? Edit that role's `references/roles/<role>/includes.yml`, then `compose.py deploy <role>` and `reboot_agent.py --role <role>`.
- Looking for the upgrade path to real Claude skills? See #9968 (EPIC: L1-L4 review + compose-architecture doc).
- Looking for the L1-L4 composition layer model? See `RESEARCH-9968.md` and the forthcoming `COMPOSE-ARCHITECTURE.md`.
