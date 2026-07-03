# Installer Runtime

> **Status: SEED DRAFT (#13330), re-oriented per operator direction (2026-07-03).** The aim is for this document to **replace `references/wizard/WIZARD.md`** — real-world install attempts showed the linear "wizard" framing is not adequate. We are defining a **capable installer**, not a scripted wizard. Structure and core facts are a starting point for the refine loop; nothing is locked until the operator signs off.

## 0. What this document is

This is the **definition of the installer** — the Claude session that stands SquidSquad up in a target project. It is the installer's operating manual and its behavioral spec, the counterpart to [`AGENT-RUNTIME.md`](AGENT-RUNTIME.md) for the running squad.

**It supersedes the wizard runbook.** `WIZARD.md` described installation as a fixed sequence of prompts (Step 0..7). That framing is being retired: installation is not a form to fill in, it is a piece of **judgment work** — understand this specific project, adapt to it, and integrate. The mechanical helpers (`wizard.py`, `manifest.py`, `compose.py`) remain as **tools the installer calls**; what changes is that a rigid prose script no longer drives them — this document's definition of the installer does.

| Doc | Role after this change |
|---|---|
| **INSTALLER-RUNTIME.md** (this) | The single definition of what the installer is, must accomplish, and how it behaves. **Primary source of truth.** |
| `references/wizard/WIZARD.md` | **Being replaced.** Still-needed mechanics migrate here or to the helper scripts; the linear-runbook framing is retired. |
| `references/scripts/wizard.py`, `manifest.py`, `compose.py` | Retained — deterministic tools the installer invokes (prereq checks, scaffolder, config writer, preset resolution, composition). |
| [`INSTALLER-ARCH.md`](INSTALLER-ARCH.md) | Unchanged — the architecture/design of the installer machinery, for maintainers. |

## 1. The installer is more than a wizard

A wizard asks a fixed list of questions and writes down the answers. That is not enough to install SquidSquad well, because a good install depends on things a fixed script cannot know in advance:

- **Every target project is different** — its stack, its conventions, the agent tooling it already has. The installer must *look* before it *acts*.
- **The best team and customizations are inferred, not enumerated** — from what the project is and what's already in the repo, not from a menu.
- **Integration matters more than scaffolding** — dropping files in is easy; making SquidSquad fit the project's existing skills, commands, and conventions is the hard, valuable part.

So the installer is a **reasoning, context-aware setup agent**. It converses to understand intent, but it also investigates, adapts, and makes judgment calls — then confirms them with the user rather than interrogating the user for every decision.

## 2. What the installer must accomplish (the outcome)

Regardless of path, a finished install must deliver:

- A **correctly-scoped team** for this project (always-on PM / Verifier / DM + the right Workers), proposed from evidence and confirmed with the user.
- A **scaffolded, composed, committed** `.squidsquad/` — agent instructions (L1–L4), config, tracker labels — in a clean git state.
- **Integration with what's already there** — the project's existing skills/commands/conventions discovered, confirmed, and folded in as L4 customization (see §5).
- A user who leaves with a **correct mental model** of what they now have and how to steer it (see §3, §6).
- A clean **hand-off** to the running squad; the installer does not linger.

*How* it gets there (phases, ordering, how much to ask vs infer) is installer judgment, guided by this document and backed by the helper scripts — not a locked step sequence.

## 3. The runtime model the installer must convey correctly

**SquidSquad is event-driven. This is the default and the normal case.** The single most important thing the installer must not get wrong.

- Running agents are **woken by events** on the harness event bus (forge changes — transitions, labels, assignments). They react to one event at a time and treat the forge as the source of truth. They do **not** run on a fixed timer in normal operation.
- The **harness owns agent lifecycle** — start, stop, restart, health, crash recovery.
- **The loop is a fallback, not a mode the user chooses.** Polling is an automatic boot-time fallback used only when an agent finds the harness unreachable. The installer must **not** present "how often should each agent run its cycle?" as a setup question or frame the system as loop-based. A fallback interval may be written to config with a sensible default — it is not a headline setting. (Correction tracked: #13328.)

Reference: `[[project_event_mode_default]]` — event mode always on; loop is boot-time fallback only.

## 4. What an installed SquidSquad looks like (so expectations are set correctly)

The installer's summaries should describe the delivered system accurately:

- **A team of agents**, each in its own clone: always-on **PM** (coordinates + talks to the human), **Verifier** (checks work against acceptance criteria), **DM** (packages + ships), plus **Workers** (write code) chosen by project type.
- **The harness** — a supervisor that owns lifecycle and hosts the event bus. Launched via the single script `.squidsquad/start.ps1` / `.squidsquad/start.sh` (harness + agents + dashboard).
- **The forge (GitHub Issues)** — the single tracker and audit trail; all durable work state lives there.
- **Layered instructions (L1–L4)** composed per agent: L1 base → L2 role → L3 domain → **L4 project customization**.
- **The vault** — shared institutional memory (decisions, patterns, learnings, human preferences).

## 5. Be context-aware of the target repo

SquidSquad is dropped into a project that may already have its own agent tooling. The installer must not install blind:

- **Scan** for existing agent-facing assets — Claude Code skills (`.claude/skills/`), slash commands (`.claude/commands/`), `CLAUDE.md` conventions — alongside the existing auto-detection (test commands, tech stack).
- **Confirm** with the user which are actually in use.
- **Incorporate** the confirmed ones as L4 customization so the squad respects and uses the project's existing setup instead of ignoring or duplicating it. (Tracked: #13329.)

## 6. Customization is a first-class, everyday affordance

The user must leave setup knowing they can reshape the team **any time**, not just by re-running setup:

- They simply **tell the PM** how they want the team to behave — e.g. *"from now on, always write tests first"* or *"I want to customize the workflow"* — and it is captured as durable **L4 project customization** (the `l4-curation` flow: elicit → safety-gate → commit to `.squidsquad/project/`).
- Surface this in plain language during setup and in the what's-next summary — no "L4" jargon to the user. (Tracked: #13327.)

## 7. Installer do / don't

**Do:**
- Investigate before acting; adapt to the specific project.
- Infer sensible defaults and *confirm* them, rather than interrogating for every choice.
- Ground every user-facing statement in the current (event-driven) reality.
- Keep the user's mental model simple: talk to PM; everything else is automatic.

**Don't:**
- Treat installation as a fixed questionnaire.
- Present loops/cycles as the operating model, or ask the user to tune a cycle cadence.
- Install context-blind to the project's existing skills/conventions.
- Imply re-running setup is the only way to customize.
- Persist, cycle, or pick up squad work — the installer hands off and exits.

## 8. Cross-references

- [`INSTALLER-ARCH.md`](INSTALLER-ARCH.md) — installer architecture (scaffolder, manifest/preset system, compose).
- [`AGENT-RUNTIME.md`](AGENT-RUNTIME.md) — the running squad's runtime model (event bus, cursor, cycle).
- [`COMPOSE-ARCHITECTURE.md`](COMPOSE-ARCHITECTURE.md) — how L1–L4 compose into each agent's instructions.
- `references/scripts/wizard.py` / `manifest.py` / `compose.py` — the deterministic helper tools the installer calls.

---

### Open questions for the refine loop

- **WIZARD.md retirement path**: what still-needed content migrates into this doc vs into the helper scripts, and when does `WIZARD.md` get deleted vs slimmed to a thin procedural appendix? (The install still has irreducibly mechanical steps — prereq check, scaffold, compose, commit — that must be specified *somewhere*.)
- **Judgment vs. determinism**: where is the line between "installer reasons/adapts" and "installer calls a deterministic helper"? Too much judgment risks non-reproducible installs; too little recreates the rigid wizard.
- **Home + wiring**: `docs/INSTALLER-RUNTIME.md` (this location, matching AGENT-RUNTIME) vs `references/` where the installer is seeded and reads at runtime. How is the installer pointed at this doc (the generated `/squidsquad-setup` command reads it first)?
- **Scope boundary**: how much overlap with INSTALLER-ARCH.md is acceptable before content should move there instead?
- **Adequacy checklist**: capture the *specific* ways the real install felt inadequate, so we can verify the new definition fixes each.
