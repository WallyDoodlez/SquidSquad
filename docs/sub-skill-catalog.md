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
│       (PM / verifier / DM / worker)              │
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
   - **L2** — role-specific (what a PM / verifier / DM / worker does)
   - **L3** — role variant (e.g. a worker specialized for a particular stack, or a PM with a project-shipped overlay)
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
| `common-events/` | all roles (event-shaped procedural fragments) | **runtime-loaded** by `boot-bootstrap` on session start (not inlined); fall-back paths inside these fragments handle the boot-time loop-mode-fallback case (per AGENT-RUNTIME §8.3-§8.4) |
| `roles/<role>/` | one role | inlined at compose time |
| `project/` | seed templates for L4 | copied to `.squidsquad/project/` at install (not consumed by compose) |
| ~~`capabilities/<tool>/`~~ | _removed 2026-05-27_ | _was: tool integrations; superseded by per-agent post-install tool setup, see [INSTALLER-ARCH.md §8](INSTALLER-ARCH.md)_ |

---

## `common/` — Cross-cutting sub-skills

Reusable across multiple roles.

### Boot & cycle transport

| Sub-skill | One-liner | Used by |
|---|---|---|
| `boot-bootstrap` | Mode detection on session start (polling vs event); reads the right runtime fragments | PM, verifier, DM, worker |
| `cycle-runner` | 3-phase cycle (pre/creative/post) wired to `cycle_pre.py` and `cycle_post.py` | PM, verifier, DM, worker |
| `context-pressure` | Read `.squidsquad/<role>/context-pressure`; checkpoint and signal exit-42 above threshold | PM, verifier, DM, worker |
| `task-pickup` | Pick up next approved task from the role's tracker query | PM, verifier, worker (DM uses role variant) |
| `resume-working-state` | Resume in-flight work from `.squidsquad/<alias>/working-state.md` on cycle entry | all roles |
| `interval-sync` | Honor the configured cycle interval | all roles |
| `self-restart` | Detect context-pressure exit and let the harness respawn | PM, verifier, DM, worker |
| `agent-lifecycle` | Heartbeat, singleton enforcement, reboot signaling | PM, verifier, DM, worker |
| `boot-remote-agents` | PM-only: spawn stalled agents via `boot_remote.py` when the harness can't | PM |

### Tracker & coordination

| Sub-skill | One-liner | Used by |
|---|---|---|
| `tracker-protocol` | Full mechanical contract for tracker.py — timestamps, check-gh gate, list/read/create flows, legal status transitions matrix + per-role authority, Discussion entries, planning-artifact paths, per-cycle caching | all roles |
| ~~`discussion`~~ | Append-only tracker comment format — the inter-agent communication channel named in [COMPOSE-ARCHITECTURE.md §5.1](COMPOSE-ARCHITECTURE.md#51-identity) (renamed from `discussion-protocol` at #10360 — strike-through pending the file rename which lands as part of #10360) | all roles (per-role overrides retire at #10360) |
| ~~`issue-filing`~~ | _retired in #11334_ — body templates absorbed into `tracker-protocol`'s per-finding-kind one-liners (Bug fix / Feature task / Improvement-scan / Cross-role). The bare `issue-filing` name no longer resolves; use `→ run sub-skill: tracker-protocol` for the canonical mechanics. Per-role policy files (`roles/{dm,pm,verifier}/issue-filing.md`) survive separately. | _retired_ |
| `working-state` | Working-state file format and update rules | all roles |
| `pickup-comment-fidelity` | Pickup comments must accurately reflect tracker state | worker |

> Rows removed: `agent-boundaries`, `file-conventions`, `status-line`, `prohibitions` — these are no longer classified as sub-skills. Migration targets (see retirement notes above for full detail): `agent-boundaries` → Identity + Responsibility slots; `file-conventions` → inline in instructions; `status-line` → cycle-inlined (no slot); `prohibitions` → Identity Boundaries + Responsibility "does NOT do". Source files removed in #11087; content inlined per #11049 Path A D1 (verbatim into each role's `instructions.md` with `<!-- #10360-cleanup: ... -->` markers naming the eventual destination slot). Slot-migration (move bodies from `instructions` slot to Identity/Responsibility per the design above) deferred to #10360.

### Vault (institutional memory)

> Vault architecture (PARAG model, entity types, cycle integration, failure modes): [`VAULT-ARCH.md`](VAULT-ARCH.md).

| Sub-skill | One-liner | Used by |
|---|---|---|
| `vault-remember` | End-of-cycle reflection; writes to vault when something is worth remembering | PM, worker |
| `vault-optimize` | On quiet cycles, compact and de-dup vault entries | PM, worker |
| `vault-protocol` | Full vault R/W protocol | PM, worker |
| `vault-protocol-slim` | Read-only variant for verifier/DM (no vault writes) | verifier, DM |

### Quality, git, improvement

| Sub-skill | One-liner | Used by |
|---|---|---|
| `git-commit` | Commit/push protocol with PR flow | worker (DM has its own variant) |
| `pr-protocol` | PR lifecycle — `git_ops.py pr-create` lock vs bare `gh pr create`; two-lane merge protocol (verifier auto-merge + DM ship-pending; PM observes, never merges); squash-strategy lock; conflict-resolve via merge (never rebase) | all roles (runtime-loaded via `→ run sub-skill: pr-protocol` from `common/git-commit.md`, `roles/pm/task-intake.md`, `roles/verifier/verification.md`, `roles/dm/delivery-packaging.md`, `roles/pm/pipeline-sentinel.md`) |
| `improvement-scan` | Full proactive scan for process/template gaps | PM, worker |
| `improvement-scan-slim` | Filing-only variant (no auto-fix) for read-only roles | verifier |
| `capability-check` | _deprecated — slated for removal_; was: verify the agent's environment has the tools it expects | DM (currently; removal paired with the broader capability-framework retirement per [INSTALLER-ARCH.md §8](INSTALLER-ARCH.md), not this PR) |
| `l4-curation` | Elicitation dialog for runtime L4 writes — detect customization request, scope bucket + rationale, walk the §7.2 decision tree (replace / insert-before / insert-after / append), run the three §7.4 safety gates (DeepSeek audit / mini-CQ / compose dry-run), produce a well-formed H3 op-block for `.squidsquad/project/<role-class>.md`. Reactively invoked; not part of any cycle step. One-off requests and feature requests are explicitly NOT routed through this sub-skill. Authored in PRD-C/C1 (#10650); wired into pm/dm/verifier/worker L2 instructions.md in PRD-C/C2 (#10651) via the standard `→ run sub-skill: l4-curation` reference (NOT inlined via any role's `includes.yml` — wiring is v2-path only per C2 AC4). | every role-class (pm/dm/verifier/worker) — reactive (no cycle step); §7 of [COMPOSE-ARCHITECTURE.md](COMPOSE-ARCHITECTURE.md) |
| ~~`compose-output-review`~~ | Sub-procedure for reviewing composed CLAUDE.md output for source-output drift — invoked during code review (planned per COMPOSE-ARCHITECTURE.md §9; implementation pending — strike-through until the source file lands) | worker (planned) |

### Chat & coordination (deferred — chat-integration roadmap)

The three chat sub-skills below are **intentionally unwired** today. They're scaffolding for the harness chat-room roadmap (see [HARNESS-ARCH.md](HARNESS-ARCH.md) — chat-room is part of the supervisor + event-bus + web-terminal harness vision). When chat lands, these become the behavioral contracts every role agent loads.

**Do not delete these as "dead sub-skills" in future improvement scans** — they're parked, not abandoned. Defer any wiring/usage work until chat integration is on the active roadmap.

| Sub-skill | One-liner | Status |
|---|---|---|
| `chat-etiquette` | Behavior rules for the team chat room | deferred — chat roadmap |
| `mention-protocol` | @mention escalation tiers and noise budget | deferred — chat roadmap |
| `consensus-protocol` | Multi-party decision flow for chat-driven decisions | deferred — chat roadmap |

---

## `common-events/` — Event-shaped procedural fragments (all roles)

Referenced by the single mode-agnostic `references/roles/<role>/includes.yml` manifest (per [COMPOSE-ARCHITECTURE.md §6.5](COMPOSE-ARCHITECTURE.md#65-wake-mode-handling--one-manifest-boot-time-selection-at-runtime)). The fragments themselves are **loaded by `boot-bootstrap` at agent boot** (Read tool calls per AGENT-RUNTIME), not inlined into the composed CLAUDE.md body. The fragments are written event-shaped (event mode is the unconditional architecture) with fall-back paths the cycle body invokes when the boot probe binds to loop-mode wake or when a mid-cycle bus read fails — see AGENT-RUNTIME §4.5 / §8.3.

| Sub-skill | One-liner |
|---|---|
| `event-mode-contract` | Event-mode base contract (replaces polling base for that session) |
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

> **Note on `responsibility`** — The `responsibility` content (what each role does / does NOT do / why it matters) is **no longer a sub-skill**. It is the L2-and-up authoring of the dedicated **Responsibility slot** in the composed CLAUDE.md (see [COMPOSE-ARCHITECTURE.md §5.2](COMPOSE-ARCHITECTURE.md#52-responsibility)) — authored directly in the role's L2 source with explicit `slot: responsibility` frontmatter. The legacy per-role `responsibility.md` files remain on disk until #10360 deletes them; this catalog reflects target architecture, not v1 disk state.

> **Note on `status-line` — retired entirely (corrected twice, 2026-05-27)** — First draft of this PR moved status-line to Project Context (wrong: not descriptive). Second draft kept it as a `common/` sub-skill (wrong: not a single procedure the agent invokes). Final: same pattern as `file-conventions` — statusline updates are inlined wherever a cycle step needs to surface progress. The bookend writes (pre-cycle "idle", post-cycle "idle") live in the `cycle-runner` sub-skill. Mid-cycle progress updates use a one-line `cycle.py status-bar` invocation directly in the step that's running. No standalone `status-line` sub-skill is needed. All 4 `status-line.md` files delete at #10360 implementation time.

> **Note on `file-conventions` — retired entirely (not moved to a slot)** — Today's `file-conventions.md` per-role sub-skill is a centralized path manifest, but every path in it is already used by exactly one specific instruction sub-skill (PM's task-intake names where `RESEARCH.md` goes; verifier's `verification` names where `TEST-PLAN-<N>.md` goes; etc.). The centralized map duplicates facts that already live in the instruction that touches them. Resolution: drop `file-conventions.md` entirely; paths stay inline in the instruction sub-skills that use them. L4 path overrides use `### replace step:<step-id>` on the specific instruction. Tracked in #10360.

> **Note on `agent-boundaries` — retired entirely (inlined into L1/L2)** — Today's `common/agent-boundaries.md` (5 lines) is two pieces of foundational content: a team-awareness baseline (`{{role-roster}}` + "know your teammates") and a decline-and-route discipline rule. Both are L1/L2 foundational content, not focused how-to. Resolution: inline the team-roster + awareness sentence into each role's Identity slot ([§5.1](COMPOSE-ARCHITECTURE.md#51-identity)); inline the decline-and-route rule into each role's Responsibility slot ([§5.2](COMPOSE-ARCHITECTURE.md#52-responsibility)). The `agent-boundaries` row below stays as the historical authoring location until #10360 ships, then the sub-skill file is deleted.

> **Note on `prohibitions` — retired entirely (inlined into L1/L2)** — 4 files today (`common/prohibitions.md` + per-role overrides in `pm/`, `verifier/`, `dm/`, ~63 lines total). Content is role-boundary content, not focused how-to. Splits cleanly: universal "never do" rules ("never push without pulling", "never edit composed CLAUDE.md", etc.) go to **L1 Identity Boundaries** ([§5.1](COMPOSE-ARCHITECTURE.md#51-identity)); role-specific rules ("PM never verifies", "verifier never ships with failed tests") go to **L2 Responsibility "does NOT do"** ([§5.2](COMPOSE-ARCHITECTURE.md#52-responsibility)) — substantially duplicates what's already in each role's responsibility content. The 4 files are deleted at #10360 implementation time.

> **Note on `discussion` and `issue-filing` — keep `common/` only, collapse per-role overrides; `discussion-protocol` renames to `discussion`** — Both ARE legitimate sub-skills (focused how-to procedures for tracker comments and bug filing). `discussion` is the procedure for the **inter-agent communication channel** named at L1 Identity ([COMPOSE-ARCHITECTURE.md §5.1](COMPOSE-ARCHITECTURE.md#51-identity)). The per-role overrides in `pm/`, `verifier/`, `dm/` exist only to bake the role name into the bash example instead of using the `[ROLE]` placeholder — pure DRY violations with no functional difference. Resolution: keep `common/discussion.md` (renamed from `discussion-protocol.md` — the "protocol" suffix added no information; L1 Identity references the short name) and `common/issue-filing.md` as the single authoring location, with `[ROLE]` placeholder substitution per the manifest's Placeholder Substitution rules; delete the 6 per-role overrides at #10360.

### PM (`roles/pm/`)

| Sub-skill | One-liner |
|---|---|
| `checkin` | Step 2 — non-blocking human check-in; issue/task/approval intake |
| `task-intake` | 5-phase feature lifecycle (Research → Discussion → Planning → human-approve → Execution) |
| `task-approval` | Feature-approval gate; planned → approved transition |
| `testing-and-verification` | Steps 3–6 — delegate to verifier; PM doesn't verify |
| `delivery` | Delegate to DM; PM doesn't package |
| `pipeline-sentinel` | Step 6f — stall, conflict, PR-status, and stuck-state sweep |
| `own-domain-autofix` | Fix PM-owned mechanical drift inline; don't file bugs for self |
| `health-check` | Step 7 — agent health sweep + log to `qa-log.md` |
| `github-issues` | Step 7b — triage externally-filed issues; route to a role |
| `soul-shepherd` | Detect character signals in new tasks; update SOUL adaptations |
| `roles/pm/improvement-scan` | PM variant — process-focused, never code (slash-bearing form per #10743; disambiguates from `common/improvement-scan`) |
| `roles/pm/issue-filing` | PM's bug-filing protocol (behavior-only, no RCA) — slash-bearing per #10743 |
| `roles/pm/discussion-protocol` | PM's comment format (→ retires; common/`discussion` is the canonical) — slash-bearing per #10743 |
| `vault-synthesis` | Cross-agent pattern detection (PM-only) |
| `roles/pm/ralph-loop-overview` | Runtime-loaded polling-mode cycle contract — slash-bearing per #10743 |
| Domain context | Per-stack PM notes: `android/`, `ios/`, `web/`, `fullstack/`, `skill/` |

### Verifier (`roles/verifier/`)

| Sub-skill | One-liner |
|---|---|
| `verification` | Steps 2–6 — E2E tests, AC verification, health check |
| `roles/verifier/issue-filing` | Verifier's bug template (with reproduction + AC reference) — slash-bearing per #10743 |
| `roles/verifier/discussion-protocol` | Verifier's comment format (→ retires; common/`discussion` is the canonical) — slash-bearing per #10743 |
| `roles/verifier/ralph-loop-overview` | Runtime-loaded polling-mode cycle contract — slash-bearing per #10743 |
| Domain context | Per-stack verifier notes: `android/`, `ios/`, `web/`, `fullstack/`, `skill/` |
| `roles/verifier/skill/finding-categories` | Skill-domain finding taxonomy for verifier reports — slash-bearing per #10743; resolves to `references/sub-skills/roles/verifier/skill/finding-categories.md` |

### DM (`roles/dm/`)

| Sub-skill | One-liner |
|---|---|
| `roles/dm/task-pickup` | DM's queue: pending-ship items — slash-bearing per #10743 |
| `issue-triage` | Triage DM-owned bug reports |
| `delivery-packaging` | The packaging step: docs, CHANGELOG, release notes |
| `version-bumps` | Bump rules (uses `shipped_since_bump` counter) |
| `doc-improvement-loop` | DM's scan: drift between source docs and shipped state |
| `roles/dm/issue-filing` | DM's bug template — slash-bearing per #10743 |
| `roles/dm/discussion-protocol` | DM's comment format (→ retires; common/`discussion` is the canonical) — slash-bearing per #10743 |
| `roles/dm/ralph-loop-overview` | Runtime-loaded polling-mode cycle contract — slash-bearing per #10743 |
| Domain context | Per-stack DM notes: `android/`, `ios/`, `web/`, `fullstack/`, `skill/` |

### Worker (`roles/worker/`)

| Sub-skill | One-liner |
|---|---|
| `triage-issues` | Step 2 — deterministic work-queue triage |
| `implement-tasks` | Step 2b — pick up approved tasks; commit on feature branch; open PR |
| `roles/worker/ralph-loop-overview` | Runtime-loaded polling-mode cycle contract — slash-bearing per #10743 |
| Domain context | Per-stack worker notes: `android/`, `ios/`, `web/`, `fullstack/`, `skill/` |

> Removed from all per-role tables: `responsibility`, `file-conventions`, `status-line`. These are no longer sub-skills (see the migration notes earlier in this section). Source files removed in #11087; content inlined per #11049 Path A D1 (verbatim into each role's `instructions.md` with `<!-- #10360-cleanup: ... -->` markers naming the eventual destination slot). Slot-migration (move bodies from `instructions` slot to Identity/Responsibility per the design above) deferred to #10360.

---

## `project/` — L4 seed templates

These are **seed templates** copied to `.squidsquad/project/` at install time. The runtime versions in `.squidsquad/project/` are auto-included by `compose.py` as the L4 layer of the composed CLAUDE.md. The seeds in this directory are NOT consumed at compose time — they're the starting point a fresh install begins from.

**Target state — one seed per role-class** (per [COMPOSE-ARCHITECTURE.md §3.3 + §7.3](COMPOSE-ARCHITECTURE.md#33-l4-operations-creative-overlay)):

| Seed | Purpose |
|---|---|
| `pm.md` | PM L4 — H2 sections for Identity / Responsibility / Soul / Instructions / Project Context / Vault as needed |
| `verifier.md` | Verifier L4 — same H2 grammar |
| `dm.md` | DM L4 — same H2 grammar |
| `worker.md` | Worker L4 — exactly one file, shared by ALL worker-class agents regardless of L3 specialization (FE/BE/iOS/etc.). Same H2 grammar as the other role-class seeds. |

Per [COMPOSE-ARCHITECTURE.md §3.3](COMPOSE-ARCHITECTURE.md#33-l4-operations-creative-overlay): the four L4 filenames are fixed (`pm.md` / `worker.md` / `verifier.md` / `dm.md`) — one per L2 role-class. L3 specialization does NOT differentiate L4 files. `compose.py deploy <alias>` resolves alias → role-class via the `## Aliases` registry, then reads the corresponding L4 file. Multi-instance installs of the same role-class share that one L4 file.

**Legacy multi-file L4 seeds (deprecated)** — earlier installs scattered L4 content across per-slot files. These remain on disk under `references/sub-skills/project/` until the unified model is implemented (see #10359 doc spec; implementation tracked separately), at which point they collapse into the per-role-class files above:

- ~~`shared-instructions.md`~~, ~~`shared-responsibility.md`~~, ~~`shared-soul-directives.md`~~ — cross-role baselines fold into each role's `<role>.md` as appropriate H2 sections, or remain as a project-level shared baseline if a clean "shared" precedent emerges
- ~~`<role>-instructions.md`~~, ~~`<role>-responsibility.md`~~, ~~`<role>-soul-directives.md`~~ (per role pm/verifier/dm/worker) — fold into `<role>.md` under their slot's H2
- ~~`setup-upgrade-gate.md`~~ — folds into each role's L4 file as a sub-section of the appropriate slot, or is retired if its content is no longer load-bearing

---

## ~~`capabilities/<tool>/` — Tool-binding sub-skills (REMOVED)~~

**Removed 2026-05-27.** The original model bound a role to a specific external tool via a `capabilities/<tool>/` sub-skill plus a `setup.md` walked at install time. Superseded — tool/MCP/CLI configuration is now a **per-agent, post-install runtime concern**. See [INSTALLER-ARCH.md §8](INSTALLER-ARCH.md) for the replacement model: the human tells each agent what tools to use, and the agent persists via L4 writes per [COMPOSE-ARCHITECTURE.md §7](COMPOSE-ARCHITECTURE.md).

The `figma/`, `google_stitch/`, `local_html/`, and `local_delivery/` directories under `references/sub-skills/capabilities/` were deleted along with the parent directory; tool-specific instructions belong in each install's L4 content.

---

## How to navigate this catalog

- Adding a new sub-skill? See [`sub-skill-guide.md`](sub-skill-guide.md) and update both `references/sub-skills/manifest.md` and this catalog.
- Wiring a sub-skill into a role?
  - **v2 (target — [COMPOSE-ARCHITECTURE.md §3.2](COMPOSE-ARCHITECTURE.md#32-slot--ordinal-contract-l1-l3))**: add `slot:` and `ordinal:` frontmatter to the sub-skill source file. Compose discovers it automatically; no per-role manifest edit needed.
  - **v1 (current implementation)**: edit that role's `references/roles/<role>/includes.yml`, then `compose.py deploy <role>` and `reboot_agent.py --role <role>`. The v1 includes.yml mechanism is retired at implementation time (#10360).
- Looking for the upgrade path to real Claude skills? See #9968 (EPIC: L1-L4 review + compose-architecture doc).
- Looking for the L1-L4 composition layer model? See `RESEARCH-9968.md` and the forthcoming `COMPOSE-ARCHITECTURE.md`.
