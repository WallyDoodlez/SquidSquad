# SquidSquad Architecture

SquidSquad turns a single git repository into a multi-agent development environment. Each agent is a separate Claude Code CLI instance that loops autonomously, reading and writing to a shared `.squidsquad/` folder. Agents coordinate through git (the durable audit trail) and a lightweight in-process event bus on the harness (for real-time signals). No external databases, no persistent queues — just files, Issue labels, and ephemeral events.

This document describes the six-layer architecture that makes it work.

---

## The Six Layers

SquidSquad is built as a vertical stack of six layers. Each layer has a single responsibility and a clean boundary with the layers above and below it. Higher layers shape *what* the agent is. Lower layers handle *how* it operates.

> **Open the interactive diagram:** [docs/diagrams/layer-stack.html](diagrams/layer-stack.html)

```
┌──────────────────────────────────────────────────────────────┐
│  L6  Memory          vault/, BRIEFING.md, galaxy notes       │  ← what the squad knows
├──────────────────────────────────────────────────────────────┤
│  L5  Soul            SOUL.md — personality, quality bar      │  ← how the agent thinks
├──────────────────────────────────────────────────────────────┤
│  L4  Sub-skill       composable blocks, compose.py           │  ← reusable capabilities
├══════════════════════════════════════════════════════════════╡
│  L3  Behavior ★      CLAUDE.md — Ralph Loop, role logic      │  ← the creative core
├══════════════════════════════════════════════════════════════╡
│  L2  Orchestration   /loop, harness, thin launcher            │  ← timing & lifecycle
├──────────────────────────────────────────────────────────────┤
│  L1  Transport       cycle_pre/post, git_ops, tracker.py     │  ← mechanical plumbing
└──────────────────────────────────────────────────────────────┘
     HUMAN ↑                                          ↓ MACHINE
```

The **Behavior Layer** (L3) is the focal layer — it's where agents reason, decide, and create. Everything above it shapes the agent's character. Everything below it is deterministic plumbing.

---

## L1 — Transport Layer

**Purpose:** Move bits. Pull code, push commits, switch branches, transition tracker labels, write status bar files. No reasoning, no decisions — pure mechanics.

**Key files:**
- `references/scripts/cycle_pre.py` — pre-cycle mechanical work (git pull, context check, queue read)
- `references/scripts/cycle_post.py` — post-cycle mechanical work (commit, push, transitions, logging)
- `references/scripts/git_ops.py` — git operations (pull, commit-push, branch management)
- `references/scripts/tracker.py` — GitHub Issues CRUD with label-based status machine

**What changes here:** Adding new git operations, new tracker commands, new mechanical steps. Changes are always deterministic — if the same input produces different output, it's a bug.

**Boundary with L2:** The orchestration layer *calls* transport scripts. Transport scripts never decide *when* to run — they just execute when called.

---

## L2 — Orchestration Layer

**Purpose:** Control *when* things happen, in what order, and manage the agent's lifecycle. The conductor that sequences transport and behavior.

**Key files:**
- `references/scripts/harness.py` — FastAPI lifecycle manager, owns agent spawning, health monitoring, crash recovery, PR merging, and auto-recomposition of agent templates
- `references/scripts/thin_launcher.py` — lightweight agent launcher, spawned by harness into terminal windows
- `/loop` command — schedules recurring cycle execution
- `.squidsquad/.harness-state.json` — persistent agent state for crash recovery (single file per repo)
- `.squidsquad/[role]/current-state` — per-role status bar state file, written atomically

**What changes here:** Cycle cadence, restart logic, boot sequence, harness API. The orchestration layer knows about timing but not about what work gets done.

**Boundary with L3:** Orchestration triggers each cycle. The behavior layer decides what to *do* during that cycle.

### Agent Process Tree

Each SquidSquad agent runs as a chain of three processes:

```
python.exe (thin_launcher.py)
  └── cmd.exe (claude.CMD shim from npm install)
        └── claude.exe (the actual agent)
```

Why cmd.exe is in the chain: `thin_launcher.py:184` resolves the claude binary via `shutil.which("claude")`, which returns `claude.CMD` on Windows (the npm shim). Running a `.CMD` file requires `cmd.exe` to interpret it, so Windows inserts `cmd.exe` between the launcher and the actual `claude.exe`. This is a Windows-only artifact of how `.CMD` shims work — POSIX systems launch `claude.exe` directly.

### `.claude-pid` convention

`.squidsquad/<role>/.claude-pid` stores the **cmd.exe** PID (the immediate parent of `claude.exe`), NOT the `claude.exe` PID itself. The name is historical — it was originally written assuming the launcher would spawn `claude.exe` directly. To find the actual agent `claude.exe` process: read `.claude-pid` → find the `claude.exe` whose `ParentProcessId` matches.

### Killing agents

- **Reboot (terminate agent + restart)**: `taskkill /F /T /PID <cmd.exe PID from .claude-pid>`. The `/T` flag kills the process tree — both `cmd.exe` and its `claude.exe` child terminate. The python `thin_launcher` (grandparent) sees its child exit and returns; the operator typically respawns via `boot_remote.py`.
- **Orphan cleanup**: `taskkill /F /PID <orphan claude.exe PID>`. Orphans are leaf processes with no children, so no `/T` needed. See #9688 for the cleanup mechanism.

### Three claude.exe populations

When examining live `claude.exe` processes, three categories matter:

1. **Protected agent** — `ParentProcessId` matches some role's `.claude-pid`. This is the live agent; never kill except via reboot.
2. **Live subagent** — `ParentProcessId` is alive but does NOT match any `.claude-pid`. Spawned by the agent's `Agent` tool (deepseek code review, exploratory research); legitimately in progress.
3. **Orphan** — `ParentProcessId` is dead. Subagent whose parent task completed but Windows didn't propagate the exit. Safe to terminate via the cleanup mechanism (#9688).

---

## L3 — Behavior Layer (Focal)

**Purpose:** The creative core. This is where agents read code, reason about problems, make decisions, write implementations, verify work, and communicate with humans and each other.

**Key files:**
- `.squidsquad/[role]/CLAUDE.md` — the full agent template, composed from sub-skills
- The Ralph Loop steps — triage, implement, verify, deliver, plan

**What changes here:** Adding new capabilities to a role, changing how agents prioritize work, modifying the Ralph Loop flow, adjusting how agents interact with each other.

**This is where product differentiation lives.** Two SquidSquad installations with different behavior layers produce fundamentally different development experiences. The layers above (soul, memory) fine-tune *how* the behavior layer operates. The layers below (orchestration, transport) ensure it operates reliably.

**Boundary with L4:** The behavior layer is *assembled from* sub-skills. At runtime, the agent sees one flat template — the sub-skill boundaries are invisible.

---

## L4 — Sub-skill Layer

**Purpose:** Composable capability blocks that snap into any role's behavior layer. Sub-skills are the building blocks that make the behavior layer modular.

**Key files:**
- `references/roles/[role]/includes.yml` — which sub-skills each role includes, in composition order
- `references/sub-skills/common/` — shared capabilities (vault-protocol, cycle-runner, context-pressure, etc.)
- `references/roles/[role]/` — role-specific capabilities (e.g., `roles/dm/`, `roles/pm/`)
- `references/scripts/compose.py` — assembles sub-skills into a single CLAUDE.md per role

**What changes here:** Adding a new capability that multiple roles need (write it as a sub-skill). Changing how a shared protocol works (edit the sub-skill, all roles get the update on next deploy).

**How composition works:**
1. `includes.yml` per role lists which sub-skills to include and their order
2. `compose.py deploy [role]` reads `includes.yml`, concatenates sub-skills, resolves `{{runtime:}}` directives
3. Output is a single `.squidsquad/[role]/CLAUDE.md` — the agent's complete instructions

**Boundary with L5:** Sub-skills define *what* the agent can do. The soul layer defines *how* it exercises those capabilities.

---

## L5 — Soul Layer

**Purpose:** Personality, judgment, and quality bar. The soul shapes *how* an agent uses its capabilities — its decision-making style, communication tone, what it considers "done," and where its boundaries are.

**Key files:**
- `.squidsquad/[role]/SOUL.md` — one per role, loaded at session start via `{{runtime:}}` directive

**What changes here:** Adjusting an agent's quality bar, changing how it communicates, adding project-specific governance (like branch workflow rules). Soul changes take effect on next agent boot — no template redeployment needed.

**Key design choice:** Souls are project-adaptable. The same PM template can produce a cautious, process-heavy PM for a regulated project and a fast, lightweight PM for a hackathon — just by editing SOUL.md. This is how SquidSquad adapts to your team culture without changing code.

**Boundary with L6:** The soul defines the agent's character. Memory gives it institutional knowledge to apply that character intelligently.

---

## L6 — Memory Layer

> **Deep-dive**: [`VAULT-ARCH.md`](VAULT-ARCH.md) — full vault architecture (PARAG model, entity types, frontmatter, sub-skills, scripts, cycle integration, failure modes, current inventory).

**Purpose:** Institutional knowledge that persists across sessions and version bumps. What the squad has learned about your project, your preferences, your decisions, and your patterns.

**Key files:**
- `.squidsquad/vault/BRIEFING.md` — active context summary, auto-maintained (~50 lines)
- `.squidsquad/vault/galaxy/` — atomic knowledge notes (Zettelkasten): decisions, patterns, learnings, styles
- `.squidsquad/vault/projects/` — active project context
- `.squidsquad/vault/areas/` — ongoing concerns: preferences, conventions, values
- `.squidsquad/vault/resources/` — reference material, external docs
- `.squidsquad/vault/archives/` — shipped features, closed decisions

**What changes here:** Adding new knowledge types, changing how agents consolidate learnings, modifying the BRIEFING.md update protocol, tuning confidence decay.

**How knowledge flows:**
1. Agents observe your preferences, decisions, and patterns during work
2. At cycle end, agents reflect and write vault notes
3. On next cycle, all agents read BRIEFING.md and adapt behavior
4. Over time, the squad becomes closer to how you think and work

The vault follows the **PARAG** structure (Projects, Areas, Resources, Archives, Galaxy) and is fully git-tracked — every change has a commit, every note has version history.

---

## How Layers Interact at Runtime

A single agent cycle flows through all six layers:

```
 ┌─ L6 Memory ──────── Agent reads BRIEFING.md for context
 │
 ├─ L5 Soul ─────────── Agent's personality shapes all decisions
 │
 ├─ L4 Sub-skills ───── Capabilities available (tracker, vault, git protocols)
 │
 ├─ L3 Behavior ─────── Ralph Loop: triage → work → verify → deliver
 │    │
 │    │  cycle_pre.py ◄─── L1 Transport (git pull, read queue)
 │    │
 │    ├── Agent reasons, reads code, writes code, runs tests
 │    │
 │    │  cycle_post.py ◄── L1 Transport (commit, push, transitions)
 │    │
 │    └── Agent writes vault notes ──► L6 Memory
 │
 ├─ L2 Orchestration ── /loop triggers next cycle, harness monitors agents
 │
 └─ L1 Transport ────── Mechanical operations bookend the creative work
```

**The cycle runner** (`cycle_pre.py` / `cycle_post.py`) makes the transport layer explicit: mechanical work happens in Python scripts, creative work happens in the agent. All agents use the cycle runner — the layer boundary is always enforced.

---

## Agent Roles

Each role is a different configuration of the behavior and soul layers, assembled from shared and role-specific sub-skills:

| Agent | Behavior (L3) | Soul (L5) | Mode |
|-------|--------------|-----------|------|
| **Worker** | Bug triage, feature implementation, tests | Pragmatic engineer, correctness-first | Autonomous |
| **PM** | Human check-in, feature intake, backlog, pipeline health | Process guardian, user-centric | Interactive |
| **Verifier** | E2E tests, verification, regression testing | Skeptical tester, zero-tolerance for gaps | Autonomous |
| **DM** | Delivery packaging, docs, CHANGELOG, version bumps | User-first communicator, last-mile owner | Autonomous |

---

## Feature Lifecycle

Features flow through the behavior layer with human approval gates at key transitions:

```
Pending → Planning → Planned → Approved → In Progress → Pending Test → Pending Ship → Shipped
   │         │          │          │           │    │           │              │            │
   │     PM runs     Human      Human     Worker HITL loop  Verifier checks DM delivers   Done
   │     research    reviews    approves    builds  ↓↑          it            docs+changelog
   │     + planning   plan     execution     it  Pending
   │                                             Human Review
  You or PM                                    / Human Setup
  files it
```

Status transitions are GitHub Issue label changes (L1 transport). The decision of *when* to transition is behavior layer logic. The *criteria* for transitioning come from the soul layer's quality bar.

---

## Coordination Model

Agents coordinate through two channels: **git** (the audit trail) and the **event bus** (real-time coordination). Git carries the durable state — Issue comments, status transitions, code. The event bus carries ephemeral signals — PR merges, verification results, cycle completions — so agents can react within seconds instead of waiting for the next cycle.

```
Agent A                    Git Repository                   Agent B
   │                            │                              │
   ├── git push ───────────────►│                              │
   │                            │◄──────────────── git pull ───┤
   │                            │                              │
   │        Event Bus (Harness)                                │
   │   ├── emit(pr-merged) ────────────────► read(pr-merged) ─┤
   │   │   (milliseconds)                    (next cycle_pre)  │
```

Git coordination latency is one cycle interval. Event bus coordination is near-instant — agents read events at cycle start via `cycle_pre.py`. High-confidence patterns (like PR merge → ship) trigger mechanical reactions automatically. If the event bus is unreachable, agents fall back gracefully to git-only polling. External chat adapters (Telegram, Slack, Discord) plug into the event bus as additional consumers.

---

## Changing Things at Each Layer

| If you want to... | Change at layer | Example |
|---|---|---|
| Add a new git operation | L1 Transport | Add `npm publish` to `git_ops.py` |
| Change cycle timing | L2 Orchestration | Edit `Iteration Interval` in `.squidsquad/config.md` |
| Add a new agent capability | L3 Behavior (via L4) | Write a new sub-skill, add to manifest |
| Change how an agent prioritizes work | L3 Behavior | Edit the Ralph Loop step order |
| Make an agent more cautious | L5 Soul | Edit SOUL.md quality bar section |
| Teach the squad a new preference | L6 Memory | Write a vault note (or just tell PM) |
| Add a shared protocol | L4 Sub-skill | Write a common sub-skill, deploy to all roles |
| Change agent restart behavior | L2 Orchestration | Edit harness intent API or Ctrl+C handling |

**Rule of thumb:** If you're changing *what* happens, you're in L3/L4. If you're changing *how it feels*, you're in L5/L6. If you're changing *when or whether* it happens, you're in L2. If you're changing the mechanical *how*, you're in L1.

---

## Key Design Decisions

- **Git as the audit trail, event bus for real-time** — all durable state lives in git (files in the repo, GitHub Issues). The in-memory event bus on the harness handles ephemeral coordination signals. If the bus is down, agents fall back to git-only polling. No external databases, no persistent queues.
- **Composition over inheritance** — roles are assembled from sub-skills, not inherited from a base class. This prevents the "god template" problem.
- **Souls are separate from behavior** — you can change an agent's personality without redeploying its template. This enables project-level customization.
- **Transport is deterministic** — the cycle runner (`cycle_pre.py` / `cycle_post.py`) handles all mechanical operations. Agents focus on creative work only.
- **Memory is git-tracked** — vault notes have full version history. No opaque databases, no vector stores. Knowledge is just markdown files with frontmatter.
