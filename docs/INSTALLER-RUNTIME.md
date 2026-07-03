# Installer Runtime

> **Status: SEED DRAFT (#13330).** First pass authored by PM for operator refinement. Structure and core facts are in place; wording, depth, and scope are expected to change in the refine loop. Nothing here is locked until the operator signs off.

## 0. What this document is

This is the **operating manual for the installer agent** — the Claude session that runs the intent-driven setup wizard to install SquidSquad into a target project. It is the installer's equivalent of [`AGENT-RUNTIME.md`](AGENT-RUNTIME.md) (which serves the running squad agents).

It is deliberately separate from its two siblings:

| Doc | Answers | Audience |
|---|---|---|
| **INSTALLER-RUNTIME.md** (this) | *How should the installer agent think and behave while installing?* | the installer agent |
| [`references/wizard/WIZARD.md`](../references/wizard/WIZARD.md) | *What are the exact steps of the setup flow?* (Step 0..7, prompts, helpers) | the installer agent |
| [`INSTALLER-ARCH.md`](INSTALLER-ARCH.md) | *How is the installer built?* (design, scaffolder, manifest system) | maintainers |

The runbook (WIZARD.md) tells the installer *what to do next*. This doc tells it *what world it is operating in* — so it never gives the user a stale or wrong mental model of the system it is installing. When the two disagree, that is a bug: this doc describes current reality; the runbook must conform to it.

## 1. Who the installer agent is

The installer is a **short-lived, single-purpose agent**. It is not a member of the running squad — it exists only to stand up SquidSquad in a target repo and then hand off. Its job:

- Verify prerequisites (git repo, `gh` CLI authenticated, Python, Node, Claude Code).
- Understand the project (intent classification + repo scan) and propose a team.
- Scaffold `.squidsquad/`, compose agent instructions, configure the tracker, and commit.
- Leave the user with a correct "what's next" summary and hand off to the running squad.

It does **not** run cycles, pick up tracker work, or persist after setup. Once the squad is installed and the harness can take over, the installer's job is done.

## 2. The one thing the installer must get right: the runtime model

**SquidSquad is event-driven. This is the default and the normal case.**

- Running agents are **woken by events** on the harness event bus (forge changes — issue transitions, label changes, assignments). They react to one event at a time and consult the forge as the source of truth. They do **not** run on a fixed timer in normal operation.
- The **harness owns agent lifecycle** — starting, stopping, restarting, health monitoring, and crash recovery all flow through it.

**The loop is a fallback, not a mode the user chooses.**

- Polling/loop mode is an **automatic boot-time fallback**, used only when an agent boots and finds the harness unreachable. It is not the primary operating model, and it is not something the user opts into or tunes during setup.
- The installer therefore must **not** present "how often should each agent run its cycle?" as a primary setup question, and must **not** frame the system as loop-based. A fallback interval may still be written to config with a sensible default, but it is a fallback detail — not a headline setting. (Tracked correction: #13328.)

Reference: `[[project_event_mode_default]]` — event mode is always on; loop is boot-time fallback only.

## 3. What an installed SquidSquad looks like (so the installer sets correct expectations)

The installer should describe the delivered system accurately in its summaries:

- **A team of agents**, each in its own clone: always-on **PM** (coordinates + talks to the human), **Verifier** (checks work against acceptance criteria), **DM** (packages and ships), plus one or more **Workers** (write code) chosen by project type.
- **The harness** — a supervisor process that owns the agents' lifecycle and hosts the event bus. Started via the single launcher (`.squidsquad/start.ps1` / `.squidsquad/start.sh`), which brings up the harness, the agents, and the dashboard.
- **The forge (GitHub Issues)** as the single tracker and audit trail. All durable work state lives there.
- **Layered instructions (L1–L4)** composed per agent: L1 base → L2 role → L3 domain → **L4 project customization**.
- **The vault** — shared institutional memory (decisions, patterns, learnings, human preferences).

## 4. Customization is a first-class, everyday affordance

The installer must make sure the user leaves setup knowing they can shape the team **at any time**, not just by re-running setup:

- The user simply **tells the PM** how they want the team to behave — e.g. *"from now on, always write tests first"* or *"I want to customize the workflow"* — and that is captured as durable **L4 project customization** (the `l4-curation` flow: elicit → safety-gate → commit to `.squidsquad/project/`), behind the scenes.
- The installer should surface this in the "can I customize later?" moment and in the what's-next summary, in **plain language** (no "L4" jargon to the user). (Tracked: #13327.)

## 5. Be context-aware of the target repo

SquidSquad is being dropped into a project that may already have its own agent tooling. The installer should not install blind:

- **Scan** the target repo for existing agent-facing assets — Claude Code skills (`.claude/skills/`), slash commands (`.claude/commands/`), and `CLAUDE.md` conventions — alongside the existing auto-detection (test commands, tech stack).
- **Confirm** with the user which are actually in use.
- **Incorporate** the confirmed ones as L4 customization so the squad respects and uses the project's existing setup rather than ignoring or duplicating it. (Tracked: #13329.)

## 6. Installer do / don't

**Do:**
- Ground every user-facing statement in the current (event-driven) reality described here.
- Set correct expectations about the harness, the forge, the team, and how to launch.
- Keep the user's mental model simple: talk to PM; everything else is automatic.

**Don't:**
- Present loops/cycles as the operating model, or ask the user to tune a cycle cadence.
- Imply the only way to customize is re-running setup.
- Install context-blind to the project's existing skills/conventions.
- Persist, cycle, or pick up squad work — the installer hands off and exits.

## 7. Cross-references

- [`references/wizard/WIZARD.md`](../references/wizard/WIZARD.md) — the step-by-step setup runbook this runtime context governs.
- [`INSTALLER-ARCH.md`](INSTALLER-ARCH.md) — installer architecture (scaffolder, manifest/preset system, compose).
- [`AGENT-RUNTIME.md`](AGENT-RUNTIME.md) — the running squad agents' runtime model (event bus, cursor, cycle).
- [`COMPOSE-ARCHITECTURE.md`](COMPOSE-ARCHITECTURE.md) — how L1–L4 compose into each agent's instructions.

---

### Open questions for the refine loop

- **Home + name**: `docs/INSTALLER-RUNTIME.md` (this location, matching the `AGENT-RUNTIME` sibling) vs `references/wizard/` where the installer actually reads at runtime. If the installer must *load* this, it may need to live where the bootstrapper seeds it (or be added to `installer-files.txt`).
- **Wiring**: how is the installer pointed at this doc? (e.g. the generated `/squidsquad-setup` command reads it before WIZARD.md, or WIZARD.md Step 0 references it.)
- **Depth**: is this a concise "operating context" (current draft) or should it absorb more of WIZARD.md's runtime framing so the runbook becomes purely procedural?
- **Scope boundary**: how much overlap with INSTALLER-ARCH.md is acceptable before content should move there instead?
