# Installer Architecture (v1 draft)

> **Status**: v1 draft, 2026-05-23. Architecture companion to the step-by-step runbook at [`references/wizard/WIZARD.md`](../references/wizard/WIZARD.md). This doc defines *how* the installer is structured; the runbook defines *what* the installer does at each step.
> **Companion docs**: [`ARCHITECTURE.md`](ARCHITECTURE.md) (overall system), [`AGENT-RUNTIME.md`](AGENT-RUNTIME.md) (what runs after install), [`COMPOSE-ARCHITECTURE.md`](COMPOSE-ARCHITECTURE.md) (how composed CLAUDE.md is generated; the installer invokes this), [`sub-skill-catalog.md`](sub-skill-catalog.md) (sub-skills the installer wires up).

---

## 1. Goal & scope

The SquidSquad installer turns a fresh git repo into a working multi-agent setup. It runs as an **ephemeral Claude Code agent** that walks the user through configuration, generates `.squidsquad/`, composes per-role CLAUDE.md outputs, sets up the tracker, and boots the harness.

### 1.1 Terminology — categorical roles vs team preset

This doc uses the four **categorical role classes** from SquidSquad's architecture:

- **PM** — the project manager (singleton; one per install).
- **workers** — the engineering specialists (plural class; one or more per install — e.g. one generalist worker, or two stack-specialized workers).
- **verifiers** — the verification specialists (plural class; typically one, but the model supports multiple).
- **DM** — the delivery manager (singleton; one per install).

The **team preset** is the concrete roster chosen at install — which actual workers and verifiers to instantiate. The default preset has one worker named `worker` and one verifier named `verifier`, alongside the singleton `pm` and `dm` (post-#6274 rename — see AGENT-RUNTIME §10 revision log). Other shipped presets include stack-specialized ones (e.g. workers `fe` + `be`, or `web` + `ios` + `api`). Operators may also define custom presets.

Throughout this doc, **prose talks about the categorical classes** (PM, workers, verifiers, DM). File-layout examples use `<worker-role>/`, `<verifier-role>/`, `pm/`, `dm/` placeholders since concrete names depend on the chosen preset.

### 1.2 Per-agent clone isolation (mandatory)

**Every agent runs in its own git clone of the project repo.** This is a base architectural commitment — not a configurable mode. The installer always sets up per-alias clones (one clone per installed agent instance); there is no flag to disable clone isolation.

Why: agents work autonomously and concurrently. If they shared one working tree they would step on each other's `git pull`, `git checkout`, branch switches, and uncommitted state. Per-agent clones make each agent's working tree disjoint while still coordinating through the same remote (the source-of-truth git repo) and forge (GitHub Issues).

The clones live wherever the operator places them on disk; their paths are registered in `~/.squidsquad/clones/<alias>` (one file per alias, contents = absolute path to that alias's clone). The harness reads this registry at boot, and `start.sh` uses it to sync all clones with `git pull` before booting the squad.

In scope:

- How the installer is structured (agent + helpers + runbook)
- The phases an install passes through
- Inputs (human conversation + repo state) and outputs (`.squidsquad/` tree + GitHub labels + booted harness)
- The upgrade flow (vs first install)
- Idempotency and recovery

Out of scope:

- Step-by-step install instructions — see [`references/wizard/WIZARD.md`](../references/wizard/WIZARD.md)
- What agents *do* after install — see [`AGENT-RUNTIME.md`](AGENT-RUNTIME.md)
- How sub-skills compose into CLAUDE.md outputs — see [`COMPOSE-ARCHITECTURE.md`](COMPOSE-ARCHITECTURE.md)
- The L1-L4 model itself — see [COMPOSE-ARCHITECTURE.md §2](COMPOSE-ARCHITECTURE.md)

---

## 2. The installer's mental model

```mermaid
flowchart LR
    User(["Human operator"])
    Installer["Installer agent<br/>(ephemeral Claude Code session)"]
    Helpers[("Helper scripts<br/>(JSON-out)")]
    Runbook[("WIZARD.md<br/>step-by-step runbook")]
    Repo[("Target git repo")]
    Squad["Running SquidSquad<br/>(harness + agents)"]

    User -.->|"invokes via /squidsquad-setup"| Installer
    Installer -->|"reads runbook"| Runbook
    Installer -->|"calls per phase"| Helpers
    Installer <-.->|"converses"| User
    Installer -->|"Phase 8 commit"| Repo
    Repo -->|"start.sh"| Squad

    style Installer fill:#dff
    style Squad fill:#dfd
```

Three commitments:

1. **Ephemeral agent.** The installer is a one-shot Claude Code session. It boots, talks to the human, runs helpers, commits the final state, prints "SquidSquad ready", and exits. No background process, no daemon, no long-lived install state.
2. **Two halves — pure conversation, then writes-and-commit.** Phases 0–4 (per §4 below) are pure conversation + helper queries — no writes to the target repo. From Phase 5 onward the installer writes to the local filesystem; Phase 8 is the atomic git commit + push that publishes everything. The user can abort cleanly through Phase 4; aborting between Phase 5 and Phase 8 is also clean but requires the cleanup path in §11.2.
3. **Idempotent re-runs.** Re-running the installer detects an existing `.squidsquad/` and routes to the upgrade flow (§10). Helpers like `shared_fs.py init` are idempotent — safe to run on re-installs.

> **Numbering note.** This doc's "Phases 0–9" are an architectural decomposition of the install flow. The companion runbook [`WIZARD.md`](../references/wizard/WIZARD.md) uses its own "Step 0 / 0a / 0b / 1 / 1b / 2 / 3 / 4 / 5 / 5b / 5c / 5d / 6 / 7" numbering that maps roughly onto these phases. When this doc references a `Step <N>` it means the WIZARD step; `Phase <N>` is always this doc's numbering.

---

## 3. Inputs and outputs

### 3.1 Inputs

| Source | What the installer reads |
|---|---|
| **Human conversation** | Project domain, **team preset** (which workers and verifiers to install — see §1.1), loop interval, model routing preferences, tracker backend (GitHub Issues default, Forgejo alt), git workflow preferences. **NOT collected at install: tool/MCP/CLI configuration** — those are per-agent decisions made post-install (see §8). |
| **Repo state** | Git existence + branch + history; existing `.squidsquad/` (triggers upgrade flow); language/stack hints from filesystem |
| **Environment** | `gh` CLI installed + authenticated; Python 3 + `pip`; OS (Windows, macOS, Linux); `claude` CLI on PATH |
| **`~/.squidsquad/`** | Cross-install shared filesystem — existing secrets, clone registry, prior config |

### 3.2 Outputs

| Destination | What the installer writes |
|---|---|
| `.squidsquad/config.md` | Project config — iter interval, ship threshold, `event-driven:` mode flag (global; selects polling vs event-driven manifest per [AGENT-RUNTIME.md §2](AGENT-RUNTIME.md) + [COMPOSE-ARCHITECTURE.md §6.5](COMPOSE-ARCHITECTURE.md)), model routing, tracker backend, git workflow. Also includes the install's **SquidSquad version stamp** (`squidsquad_version: <semver>` field; written at Phase 5 from the installer's source release tag; read by the upgrade flow §10 step 1) and the **`## Aliases` registry section** mapping each install-time alias to its role-class + L3 domain (used by the harness for `/work/assign` alias-existence validation — see [AGENT-RUNTIME.md §7.3](AGENT-RUNTIME.md)). |
| `.squidsquad/<alias>/` | Per-alias agent directory (CLAUDE.md composed, working-state.md skeleton, planning/, iterations/) — one per alias in the chosen team preset: PM, each worker, each verifier, DM. *Note: no separate `SOUL.md` per alias — `SOUL.md` is a filename shorthand for the soul-slot source at `references/roles/<role-class>/SOUL.md`; its content is composed into `CLAUDE.md §3 Soul`. The v1 per-alias sidecar is retired per [COMPOSE-ARCHITECTURE.md §5.3](COMPOSE-ARCHITECTURE.md).* |
| `.squidsquad/project/` | L4 project-local files — one unified `<role-class>.md` per role-class (pm.md, `<worker-class>.md`, `<verifier-class>.md`, dm.md) with H2 slot sections. Initial `## Project Context` block in each is seeded from Phase 1 conversational answers (per §4.8 step 4); other slots start empty and accumulate at runtime via `l4-curation` (see [COMPOSE-ARCHITECTURE.md §5.5 + §7](COMPOSE-ARCHITECTURE.md)). |
| `.squidsquad/vault/` | Shared memory layer skeleton (BRIEFING.md + the five vault dirs: projects/, areas/, resources/, archives/, galaxy/). Vault architecture documented in [`VAULT-ARCH.md`](VAULT-ARCH.md). |
| `.squidsquad/.local-config` | Per-clone alias→path mapping for `start.sh` to sync clones |
| `~/.squidsquad/secrets` | API keys for external models (restricted permissions, never committed to repo) |
| `~/.squidsquad/clones/` | Per-alias clone-path registry. One file per alias (`pm`, each worker, each verifier, `dm`) whose contents is the absolute path to that alias's clone. Always created — clone isolation is mandatory (see §1.2), not a configurable mode. |
| **Forge (GitHub)** | Issue labels created via `gh label create` — status/role/type/priority/severity taxonomy |
| **Git commit** | Single atomic install commit on `main` (or the operator's chosen branch) |

> **Runtime files (not installer outputs):** `.squidsquad/.harness-port`, `.squidsquad/.harness-state.json`, `.squidsquad/.event-state.json` appear under `.squidsquad/` post-install but are **harness-owned**, written when the harness boots (not by the installer). Schemas are documented in [`HARNESS-ARCH.md`](HARNESS-ARCH.md) §7 + [`AGENT-RUNTIME.md`](AGENT-RUNTIME.md) §5. Listed here as a pointer because operators inspecting the directory post-install will see them.

---

## 4. Phases of install

```mermaid
flowchart TB
    Start([User invokes /squidsquad-setup])
    P0["Phase 0<br/>Prerequisite check"]
    P0a["Phase 0a<br/>Shared filesystem init"]
    P0b{"Phase 0b<br/>Existing install?"}
    P1["Phase 1<br/>Conversation<br/>(no writes)"]
    P2["Phase 2<br/>Configuration synthesis"]
    P3["Phase 3<br/>Review screen"]
    P4{"Phase 4<br/>User approves?"}
    P5["Phase 5<br/>Atomic write<br/>(scaffold + L4 + labels)"]
    P6["Phase 6<br/>Compose CLAUDE.md per role"]
    P7["Phase 7<br/>Tracker setup<br/>(initial issues)"]
    P8["Phase 8<br/>Commit + push"]
    P9(["Print 'SquidSquad ready' + exit"])
    Upgrade["Upgrade flow §10"]
    Abort(["Abort — zero trace"])

    Start --> P0 --> P0a --> P0b
    P0b -->|"no — fresh install"| P1
    P0b -->|"yes — existing"| Upgrade
    P1 --> P2 --> P3 --> P4
    P4 -->|"yes"| P5 --> P6 --> P7 --> P8 --> P9
    P4 -->|"no"| Abort

    style P0 fill:#dfe7fd
    style P0a fill:#dfe7fd
    style P5 fill:#fff3b0
    style P8 fill:#fff3b0
    style P9 fill:#dfd
    style Abort fill:#fdd
    style Upgrade fill:#dff
```

### 4.1 Phase 0 — Prerequisite check

Verify the environment can run a SquidSquad install:

- `gh` CLI installed AND authenticated (`gh auth status`) — required for tracker
- Python 3 + `pip` — required for helpers
- `claude` CLI on PATH — required to spawn agents
- Git repo present + clean working tree (or operator-acknowledged)

Helper: `references/scripts/wizard.py check-gh` returns a JSON envelope with `ok: true | false` and a `stage: ready | installed | authenticated` field. The installer agent acts on the JSON, never invents environment checks.

### 4.2 Phase 0a — Shared filesystem init

`~/.squidsquad/` is the cross-install shared filesystem (one per user, not per repo). The installer creates if missing:

```
~/.squidsquad/
├── secrets        # API keys, restricted perms (0600)
├── config         # cross-install config
└── clones/        # per-alias clone-path registry (one file per alias; mandatory per §1.2)
```

Helper: `references/scripts/shared_fs.py init`. Idempotent — re-runs are safe.

### 4.3 Phase 0b — Re-run detection

If `.squidsquad/` exists in the target repo, this is an upgrade, not a fresh install. The installer routes to the upgrade flow (§10). Otherwise it proceeds to Phase 1.

### 4.4 Phase 1 — Conversation (no writes)

The installer talks to the human in domain terms — never internal jargon, never file paths, never script names. It collects:

- **Project details**: name, domain, audience, primary language/stack
- **Adaptive context questions**: branched based on stack and domain (e.g. mobile app vs CLI vs web service have different follow-ups)
- **Team preset**: which preset roster to install. The installer offers a small set of named presets (e.g. a generalist preset with one worker + one verifier; a multi-stack preset with two workers + one verifier; a frontend+backend preset; a multi-platform preset). The wizard suggests a preset based on the project domain and asks the human to confirm or pick another. Custom presets are supported but not the default path.
- **Loop interval**: cycle cadence (default 30 min for polling, irrelevant in event mode)
- **Model routing** (optional): which subagent task types route to which external model
- **Forge backend** (optional): default GitHub Issues; alternate Forgejo
- **Git workflow preferences**: branch model, commit prefix convention

Notably **NOT collected**: tool/MCP/CLI configuration. The installer does not ask "which design tool do you want?" or "which delivery target?". Tool setup is a per-agent runtime concern (see §8) — the human tells each agent post-install what tools it needs, and the agent persists that decision via L4 writes ([COMPOSE-ARCHITECTURE.md §7](COMPOSE-ARCHITECTURE.md)).

This phase writes nothing. All answers are held in the installer agent's conversation context. The user can abort with zero trace.

### 4.5 Phase 2 — Configuration synthesis

The installer assembles a single in-memory **install spec** from the conversation answers — a structured representation of the install:

```yaml
team_preset: <preset-name>     # e.g. "default", "frontend-backend", "multi-platform"
workers: [<worker-role>, …]    # concrete worker names from the preset
verifiers: [<verifier-role>, …] # concrete verifier names from the preset
domain: "developer tooling"
loop_interval: 30
event-driven: no
tracker_backend: github
model_routing: { ... }
git_workflow: { ... }
```

Still no writes — the spec is in memory.

### 4.6 Phase 3 — Review screen

The installer shows the user the install spec in plain language: "I'm about to set up SquidSquad with the <preset-name> preset (PM + N workers + M verifiers + DM); GitHub Issues tracker; 30-min polling; deepseek-v4-pro for research; squidsquad-style commit prefixes". No tool/MCP wiring appears here — see §8 for the post-install tool-setup model.

### 4.7 Phase 4 — Approval gate

The installer presents the spec from §4.6 and waits for one of three responses:

- **Approve** (`p` / `proceed` / `yes` / Enter): the installer proceeds to Phase 5. Writes begin.
- **Edit** (`e` / `edit`): the installer routes back to a specific Phase 1 question (the user names which detail to change — team preset, loop interval, tracker, etc.) and re-walks the affected portion of the conversation. The spec is updated; the review screen redisplays.
- **Abort** (`a` / `abort` / `n` / `no`): the installer exits with a one-line "no changes made" message. No files written, no commit, no forge labels created.

The accepted-response set is parsed case-insensitively. Ambiguous input prompts a re-ask rather than guessing. This is the **last clean abort point** — beyond Phase 4 the installer has written to the local filesystem, and abort requires the §11.2 cleanup path.

### 4.8 Phase 5 — Atomic local write

Once approved, the installer:

1. **Cleans up** any prior partial state (if a previous interrupted install left artifacts).
2. **Serializes the install spec** to a temporary location for the scaffold step.
3. **Scaffolds `.squidsquad/`** — creates the per-alias agent dirs (CLAUDE.md placeholders, working-state.md skeletons, planning/, iterations/), vault skeleton, project-local L4 directory, and `.squidsquad/config.md`. `.squidsquad/config.md` includes the **`squidsquad_version:` field** stamped with the SquidSquad source release this installer ships with (read at upgrade time per §10 step 1). No per-alias `SOUL.md` files (the v1 sidecar is retired; SOUL.md content is composed into `CLAUDE.md §3 Soul` per [COMPOSE-ARCHITECTURE.md §5.3](COMPOSE-ARCHITECTURE.md)). No tool/MCP wiring (per §8).
4. **Seeds L4 Project Context** — for each role-class in the chosen preset, writes the Phase 1 project-intake answers (domain, audience, primary language/stack, repositories of record, external systems, project-specific tone notes) into `.squidsquad/project/<role-class>.md` under the `## Project Context` H2 section. This is the single unified L4 file per role-class (per [COMPOSE-ARCHITECTURE.md §3.3 + §7.3](COMPOSE-ARCHITECTURE.md) and the "two complementary sources" callout in [§5.5](COMPOSE-ARCHITECTURE.md)). Other L4 slots (Identity / Soul / Instructions / etc.) start empty at install time and are populated at runtime by the `l4-curation` sub-skill (per [COMPOSE-ARCHITECTURE.md §7](COMPOSE-ARCHITECTURE.md)).

   > **Historical context (no installer code needed):** earlier installs used a multi-file L4 seed pattern (`references/sub-skills/project/<role>-instructions.md`, `<role>-responsibility.md`, `<role>-soul-directives.md`, `shared-*.md`, `setup-upgrade-gate.md`). That pattern is retired and replaced by the unified `<role-class>.md` model above. The installer does **not** carry migration code for the legacy pattern — fresh installs never see it, and existing installs are migrated by a separate one-time tool (out of scope for this doc). This callout exists only to disambiguate the docs; an implementer reading §4.8 should write the unified-file path and not the legacy multi-file path.
5. **Ensures GitHub labels** — creates the status/role/type/priority/severity label taxonomy via `gh label create` (idempotent per-label check).

Writes are local but not yet committed. Helpers handle the mechanical work; the installer agent acts on JSON outputs only.

### 4.9 Phase 6 — Compose per-role CLAUDE.md

For each role in the chosen team preset (PM, each worker, each verifier, DM), the installer invokes:

```bash
python references/scripts/compose.py deploy <role>
```

`compose.py` reads the L1-L3 sub-skill sources + L4 project-local files and emits `.squidsquad/<alias>/CLAUDE.md` per the [compose pipeline](COMPOSE-ARCHITECTURE.md). The composed output is a thin orchestration layer that references sub-skills — see [COMPOSE-ARCHITECTURE.md §4.5](COMPOSE-ARCHITECTURE.md). (The `compose.py deploy <role>` CLI accepts the alias as its argument; the param name `<role>` in the helper signature predates the alias concept.)

### 4.10 Phase 7 — Tracker setup

Beyond the labels created in Phase 5, the installer may seed initial issues — e.g. issue #1 with the project's roadmap or onboarding tasks. This is configurable per-install and is the only place where the installer writes to the forge beyond labels.

### 4.11 Phase 8 — Commit + push

A single atomic commit on `main` (or the operator's chosen branch) containing the full `.squidsquad/` tree. Commit message follows the convention `wizard: SquidSquad install — <team_preset>`. Push to origin.

### 4.12 Phase 9 — Print "ready" message and exit

The installer prints a one-line confirmation with next steps — typically how to invoke `start.sh` to boot the harness — and exits its Claude Code session. No background process; the human is now in control.

---

## 5. File layout produced

The full `.squidsquad/` tree post-install. PM and DM dirs are always present (singletons); each chosen worker and verifier from the team preset gets its own dir. The names `pm`, `verifier`, `worker`, `dm` shown below are the *default-preset* names (post-#6274 rename — see AGENT-RUNTIME §10 revision log); other presets use different concrete names (e.g. `fe`, `be`, `web`, `ios` for workers).

```
.squidsquad/
├── config.md                    # project config (interval, threshold, routing, tracker, git workflow, team preset)
├── pm/                          # PM (singleton — always present)
│   ├── CLAUDE.md                # composed orchestration (compose.py deploy pm)
│   ├── working-state.md         # crash-recovery checkpoint (skeleton)
│   ├── enhancements.md          # product backlog seed
│   ├── planning/                # RESEARCH/CONTEXT artifacts
│   ├── iterations/              # iter-N.md cycle logs
│   └── migrations/              # legacy migration logs
├── <worker-role>/               # one per worker in the preset (default: worker)
│   ├── CLAUDE.md
│   ├── working-state.md
│   ├── planning/
│   └── iterations/
├── <verifier-role>/             # one per verifier in the preset (default: verifier); adds verifier-log.md
│   ├── CLAUDE.md
│   ├── working-state.md
│   ├── verifier-log.md
│   ├── planning/
│   └── iterations/
├── dm/                          # DM (singleton — always present)
│   ├── CLAUDE.md
│   ├── working-state.md
│   └── iterations/
├── project/                     # L4 — one unified file per role-class
│   ├── pm.md                    # H2 slot sections; ## Project Context seeded from Phase 1
│   ├── <worker-class>.md        # one per worker class in the preset
│   ├── <verifier-class>.md      # one per verifier class in the preset
│   └── dm.md                    # H2 slot sections; ## Project Context seeded from Phase 1
├── vault/                       # shared memory (PM + workers R/W, verifiers + DM read-only)
│   ├── BRIEFING.md
│   ├── projects/
│   ├── areas/
│   ├── resources/
│   ├── archives/
│   └── galaxy/
├── .local-config                # per-clone alias→path map (read by start.sh)
└── (runtime) .harness-port, .harness-state.json, .event-state.json — created when the harness boots
```

And the per-user shared filesystem (not part of any single repo):

```
~/.squidsquad/
├── secrets         # API keys (chmod 0600)
├── config          # cross-install config
└── clones/         # per-alias clone-path registry — one file per alias, contents = absolute path
```

---

## 6. Helper scripts (the installer's mechanical layer)

The installer agent never invents behavior the helpers already implement. Every helper prints a JSON envelope with `ok: true | false` and a payload — the installer acts on the JSON.

| Helper | Purpose |
|---|---|
| `references/scripts/wizard.py` | Main wizard helper with sub-commands per install step (`check-gh`, `detect-stack`, `scaffold`, `enrich-l4`, `ensure-labels`, `serialize-spec`, etc.) |
| `references/scripts/shared_fs.py` | Initializes and manages `~/.squidsquad/` (secrets, clones registry, cross-install config) |
| `references/scripts/compose.py` | Generates `.squidsquad/<role>/CLAUDE.md` from L1-L4 sources — see [COMPOSE-ARCHITECTURE.md](COMPOSE-ARCHITECTURE.md) |
| `references/scripts/forgejo_setup.py` | Forgejo backend init (alternate tracker; see §9) |
| `references/scripts/tracker.py` | The tracker abstraction layer — agents use this at runtime; the installer uses its label-creation paths at Phase 5 |
| `start.sh` | Post-install boot script — ensures Python deps, syncs all clones, runs the harness |

> **Runtime-shipped components (not installer-invoked):** the SquidSquad source tree also ships `references/scripts/event_poll.py` (per-agent event-bus sidecar; harness-spawned in event-driven mode — see [AGENT-RUNTIME.md §7.0](AGENT-RUNTIME.md) + [HARNESS-ARCH.md §7.2](HARNESS-ARCH.md)) and `references/scripts/harness.py` itself. The installer does NOT invoke these — they're part of the runtime. They're mentioned here because they live alongside the installer's helper scripts under `references/scripts/` and operators inspecting that directory will see them.

---

## 7. The installer agent (Q-new21)

The installer is a Claude Code session activated via the `squidsquad-setup` skill (or `/squidsquad-setup` slash command). Its full runbook is at [`references/wizard/WIZARD.md`](../references/wizard/WIZARD.md) — 700+ lines of per-step instructions.

Key contracts:

- **Reads the runbook**, doesn't improvise. Every step has explicit success/failure pathways.
- **Calls helpers for mechanical work** (file I/O, gh API, label creation). Never replicates helper logic in conversation.
- **Speaks in domain terms** — never mentions internal files, status labels, or script names unless inside a troubleshooting block.
- **One question at a time.** No multi-question forms; conversational pacing.
- **Ephemeral**: exits after Phase 9. The harness, agents, and ongoing operations are handled by [AGENT-RUNTIME.md](AGENT-RUNTIME.md) and are no longer the installer's concern.

---

## 8. Tool/MCP/CLI setup is per-agent and post-install

SquidSquad's install does NOT pre-wire tool integrations. There is no "capability" concept in the install — no design-tool selection, no delivery-target selection, no MCP/CLI bundling per role. The installer leaves every agent **tool-naked at first boot**.

### 8.1 Why

The space of role × tool combinations is large and project-specific (designer worker uses Figma here, Sketch there, local HTML somewhere else; a `worker` may need `kubectl` here, `gcloud` there, neither in a third install). Predefining role+capability bundles would either be too narrow to cover real installs, or too broad to be useful. Trying to capture it via PM-driven "choose your capabilities" conversation at install time produces vague, low-fidelity decisions before the human knows what they need.

### 8.2 The model: agent learns its own tools post-install

After install, each running agent can be told by the human:

> "From now on, when you do design work, use the Figma MCP server at `<URL>`. Here's the API key."
> "When you deploy, use `gcloud` not `kubectl`. The project ID is `<id>`."
> "Install the `playwright` MCP server and use it for E2E browser tests."

The agent treats this as a runtime L4 write per [COMPOSE-ARCHITECTURE.md §7](COMPOSE-ARCHITECTURE.md):

1. Agent classifies the directive (`append` / `insert-before` / `insert-after` / `replace` on its `instructions` or `project-context` slot).
2. DeepSeek audit + mini-CQ ([COMPOSE-ARCHITECTURE.md §7.4](COMPOSE-ARCHITECTURE.md)) gates the write.
3. If approved, the agent persists the directive to a new L4 file in `.squidsquad/project/` with proper frontmatter, then triggers a recompose.
4. The next session boots with the new tool/MCP/CLI wired into its CLAUDE.md as if it had always been there.

API keys and secrets stay in `~/.squidsquad/secrets` (created by the installer's Phase 0a `shared_fs.py init`); the L4 file references them by name, not by value.

### 8.3 What the installer does NOT do

- No `capabilities/` sub-skill set in the install scaffold.
- No `setup.md` walk per tool.
- No `common/capability-check` sub-skill in any role's compose manifest.
- No `Capabilities:` section in `.squidsquad/config.md`.

The existing `references/sub-skills/capabilities/` directory and `common/capability-check.md` are slated for removal — they are architectural deadwood from the prior model. Tracker: follow-up issue against the worker class (default-preset assignee: `skill`) when this doc lands.

### 8.4 What if an agent needs a tool it doesn't know about yet?

The agent surfaces the gap to the human via the normal `/work/assign` → PM routing with `event_context="process-concern"` (see [AGENT-RUNTIME.md §7.3](AGENT-RUNTIME.md)). PM either prompts the human for direction or surfaces it at the next check-in. The human's directive becomes an L4 write per §8.2. No installer involvement.

---

## 9. Tracker backend selection

The default tracker backend is **GitHub Issues** — the canonical tracker described throughout SquidSquad's docs and used by the team in `.squidsquad/`.

`references/scripts/tracker.py` is the abstraction layer that decouples agent code from any specific tracker backend — agents always call `tracker.py`, never `gh` directly for status transitions or comments. Non-GitHub backends are planned post-v1. As of this doc:

- **GitHub Issues** (default): the installer creates the standard label taxonomy via `gh label create` in Phase 5.
- **Forgejo** (experimental): `references/scripts/forgejo_setup.py` provides the alternate-backend init flow. The installer offers this during the forge-backend conversation step ([WIZARD.md Step 5c](../references/wizard/WIZARD.md)) if the human explicitly requests it. This conversation happens during this doc's Phase 1.

The choice is recorded in `.squidsquad/config.md` under `Tracker Backend`. Agents read it at boot and route their tracker calls accordingly through `tracker.py`.

---

## 10. Upgrade flow

When the installer detects an existing `.squidsquad/` at Phase 0b, it routes here instead of the fresh-install path.

The upgrade model is **upgrade = sequential migration**: every release that breaks the L4 file schema or the `.squidsquad/config.md` schema ships a per-version migration file at `references/migrations/v<N-1>-to-v<N>.md`. The upgrade flow walks them in version order against the operator's current L4 + config, recomposes, and restarts.

```mermaid
flowchart LR
    Existing(["Existing .squidsquad/"])
    Pull["Pull source updates<br/>into references/"]
    ReadV["Read installed version<br/>from config.md squidsquad_version:"]
    Walk["Walk migrations in order<br/>v_installed → v_current<br/>(three-gate per step)"]
    Recompose["Run compose.py deploy-all<br/>regenerate all CLAUDE.md"]
    Restart["Stop + restart all agents<br/>via harness HTTP API"]
    Done(["Upgrade complete"])

    Existing --> Pull --> ReadV --> Walk --> Recompose --> Restart --> Done
    style Done fill:#dfd
```

**Steps:**

1. **Pull**: latest SquidSquad sources into `references/` (L1-L3 sub-skills, role files, manifests, helper scripts, and any new `migrations/v*-to-v*.md` files shipped with this release).
2. **Read installed version**: one-line read of `.squidsquad/config.md`'s `squidsquad_version:` field (written at install time per §3.2 + §4.8). The installer's own version comes from `references/VERSION` (a semver string shipped in source). If the operator's `squidsquad_version:` field is absent — possible on installs predating the version-stamp convention — treat as `pre-1.0` and walk all migration files in order. If installer-version ≤ installed-version, there's nothing to upgrade; print "already current" and exit.
3. **Walk migrations**: for each version step between installed → current (e.g. `1.2→1.3`, `1.3→1.4`, `1.4→1.5`), find the matching `references/migrations/v<N-1>-to-v<N>.md` file. If a version step has no migration file, **skip it** — that release shipped no schema break, so there's nothing for the operator to migrate. For each found migration file, apply its instructions to the current L4 + config under the **three-gate model** (same gating as `l4-curation`, per [COMPOSE-ARCHITECTURE.md §7.4](COMPOSE-ARCHITECTURE.md)):
   1. **DeepSeek audit**: a deepseek-class model reviews the proposed L4 / config edit against the migration prose
   2. **Mini-CQ**: one-line plain-language confirmation to the human ("Migration v1.4 → v1.5 wants to rename `event_driven:` to `event-driven:` in your config — OK?"); rejection aborts that step with no file change
   3. **Compose dry-run**: `compose.py deploy-all --check` validates the migrated content composes cleanly before any write
   
   Migrations are stepped through one at a time — failure at any gate aborts that step (and the rest of the walk) cleanly; nothing partial is written.
4. **Recompose**: `compose.py deploy-all` regenerates every role's CLAUDE.md from the now-current source + migrated L4. The composed outputs reflect both the new sub-skill versions and the migrated L4 customizations.
5. **Restart**: each affected agent so they pick up the new CLAUDE.md. The installer is an ephemeral Claude Code session but has full Bash tooling — it makes these HTTP calls via `curl` (or equivalent) against the harness's localhost port (read from `.squidsquad/.harness-port` per [HARNESS-ARCH.md §6](HARNESS-ARCH.md)). "Ephemeral" refers to lifetime, not capability: the installer can do anything its Claude Code tooling permits before it exits at Phase 9. The installer calls the harness's per-agent lifecycle endpoints in sequence:
   ```
   POST /agents/{role}/stop    # graceful stop; harness handles ack-stop / timeout
   POST /agents/{role}/start   # boot with new composed CLAUDE.md
   ```
   for each agent. The `{role}` path parameter is the harness's published URL-template name, but the **value passed is the alias** (e.g. `pm`, `frontend-1`, `verifier`) — the harness vocabulary note ([HARNESS-ARCH.md §9](HARNESS-ARCH.md)) explains the legacy parameter-name vs value-semantic mismatch. The full rename to `{alias}` is tracked in [#10358](https://github.com/WallyDoodlez/SquidSquad/issues/10358) but is out of scope on that task to limit blast radius (per AGENT-RUNTIME §4.3). If the harness is not running, the installer instead invokes `start.sh` from the repo root (which boots the harness, which in turn boots the agents per `.local-config`). Either way, the next session each agent starts is reading the new composed CLAUDE.md. In event-driven mode the harness also respawns each agent's `event_poll.py` sidecar on agent restart (per [HARNESS-ARCH.md §7.2](HARNESS-ARCH.md) `boot_agent`); the installer doesn't need to manage `event_poll` directly.

   **In-flight-work handling.** Before stopping each agent, the harness checks whether the agent has an active iteration (i.e., it is in the creative phase between `cycle_pre.py` and `cycle_post.py`). If so, the harness waits for the agent's `ack-stop` event — the agent finishes its current iteration, calls `cycle_post.py` (which commits and pushes `.squidsquad/<alias>/working-state.md` + any in-flight changes), and then exits via the normal exit-42 path. If the iteration does not complete within a configurable timeout (default 5 minutes), the harness logs a warning and proceeds with the stop; on next boot the agent reads `.squidsquad/<alias>/working-state.md` to recover from the checkpoint (see AGENT-RUNTIME §5 state-persistence map + §6.5 context-pressure exit-42 model). No in-flight state is lost because `.squidsquad/<alias>/working-state.md` is the durable checkpoint that survives restarts.

### 10.1 Migration file format

Migration files are **prose for the installer's LLM to consume**, not structured rules. One file per version step that breaks schema, at `references/migrations/v<N-1>-to-v<N>.md`. Example:

```markdown
# Migration: v1.4 → v1.5

## config.md changes

- The `event_driven:` field was renamed to `event-driven:` (underscore → hyphen).
  If the operator's config has the underscore form, change the key to hyphen,
  value untouched. Mechanical; apply deterministically.

## L4 changes

- The `## Vault` slot is now L1-exclusive (per #10372). If any L4 file has a
  `## Vault` H2, surface to the operator: "this rule no longer maps to anything
  in the new framework. Options: convert to `## Project Context` append, file
  as upstream feature request, or delete." Judgment call; await operator choice.
```

Migrations describe both **mechanical** changes (deterministic renames, additive defaults — the LLM applies them straight through) and **judgment-call** changes (slot retirements, rule re-routing — the LLM surfaces options to the operator and waits for a choice). The same migration file can mix both.

If the release does NOT break L4 or config schema, **no migration file is needed** — the version walk simply skips that step.

### 10.2 What stays untouched during upgrade

(This subsection's "untouched" invariants are scoped to the **upgrade flow** described in §10. Fresh install — §4.8 Phase 5 — legitimately creates these files for the first time; "untouched during upgrade" is not the same as "never written".)

- `.squidsquad/project/` — L4 project-local customizations. Migrations may *modify* L4 contents, but only through the three-gate model in step 3; the upgrade flow never bulk-overwrites or regenerates L4 files. (Fresh install creates these files in Phase 5 step 4 from Phase 1 project-intake answers.)
- `.squidsquad/vault/` — shared memory layer (never touched by upgrade; created at fresh install by `vault-init` per VAULT-ARCH §7.1)
- `.squidsquad/<alias>/working-state.md`, `iterations/`, `planning/` — agent state
- `.squidsquad/config.md` — project configuration. Migrations may modify specific fields under the three-gate model; the installer never blindly overwrites. (Fresh install writes this file from Phase 1 + Phase 2 conversational output.)
- GitHub Issue labels — already present from prior install

### 10.3 What's regenerated

- `.squidsquad/<alias>/CLAUDE.md` — composed orchestration. The Soul section (§3) is recomposed from the latest `references/roles/<role-class>/SOUL.md` source plus any L4 `## Soul` append, per [COMPOSE-ARCHITECTURE.md §3.2 + §5.3](COMPOSE-ARCHITECTURE.md). No separate per-alias SOUL.md file exists (sidecar retired).
- `.squidsquad/config.md` `squidsquad_version:` field — updated to the current installer version after a successful walk (the only field the installer writes unconditionally; everything else moves through migrations).

### 10.4 Edge cases

- **Missing version stamp** (operator on a pre-version-stamp install): treat as `pre-1.0` and walk all available migrations in order. The first migration that runs writes `squidsquad_version:` to the current version on completion.
- **Missing migration file for a version step**: that release shipped no schema break — skip it silently. No error.
- **Operator aborts mid-walk** (mini-CQ rejection at step k): the walk aborts at step k; no further steps run; no recompose; no restart. The L4 / config changes from steps 1..k-1 (which were already gated through and written) persist; the version stamp is *not* advanced to current. Next upgrade run picks up at step k. This makes partial-upgrade safe.
- **DeepSeek audit rejects a step** (LLM judgment misalignment): same as operator abort — clean stop at step k. Operator can investigate, edit the migration file or their L4 manually, then re-run upgrade.
- **Compose dry-run failure at step k**: the migration produced L4 / config that doesn't compose. Same clean-stop semantics. Bug-level: this should not happen if migration files and L4 are well-formed; treat as a release-quality regression and file upstream.
- **Skipped versions** (operator on v1.0 jumping to v1.5): same flow — walk v1.0→1.1, 1.1→1.2, …, 1.4→1.5 in order. Each step is independently gated; the operator approves each. No "diff two versions of the source tree" computation is needed.

### 10.5 Migration files are framework-shipped, not operator-written

Operators on consuming installs never write migration files — they consume them as part of the source `pull` in step 1. The responsibility for writing migration files belongs to whoever **ships SquidSquad releases**. For SquidSquad's own self-development repo, that responsibility lives in L4 DM (tracked separately).

---

## 11. Idempotency & recovery

### 11.1 Safe re-run guarantees

The installer is designed to be safe to re-run:

- **Phases 0–4** make no changes the user can see in the target repo. (Phase 0a `shared_fs.py init` writes to `~/.squidsquad/` but is idempotent — creates dirs only if absent — and is shared across all installs, not specific to this one.)
- **Phase 5 atomic write** is the first phase that writes to the target repo. It uses a "scaffold then write" pattern — failures partway leave the filesystem in a state the next re-run can clean up via WIZARD's Step 7.1 ("Full rebuild cleanup if applicable") cleanup path.
- **Phase 5 label creation on the forge** is per-label idempotent (`gh label create` skips existing labels).
- **Phase 6 compose** is deterministic *for a given set of inputs* — the same L1-L3 sources + L4 file always produce the same composed CLAUDE.md. During an upgrade (§10), the L1-L3 sources change because the installer pulls newer SquidSquad releases, so the composed output legitimately changes; that is not a determinism violation, just a reflection of the input change. Re-running Phase 6 against an unchanged source set is safely idempotent.
- **Phases 5–7** are pre-commit local + forge writes. A `git status` after Phase 5 shows untracked `.squidsquad/` files; forge labels created in Phase 5 / initial issues in Phase 7 are visible on GitHub immediately. The atomic git commit + push happens at Phase 8.

### 11.2 Interrupted install recovery

If the installer is interrupted mid-Phase-5 (filesystem partially scaffolded), re-running detects the partial state and offers a "clean rebuild" option that wipes `.squidsquad/` (preserving `vault/` and `project/`) and starts Phase 5 fresh.

If the installer is interrupted between Phase 7 and Phase 8 (forge labels created, no commit yet), re-running detects the no-commit state and offers to commit the existing scaffold rather than redoing it.

### 11.3 What never gets wiped

Across both upgrade and clean-rebuild, these are always preserved:

- `.squidsquad/vault/` — shared memory; lossy here is irrecoverable
- `.squidsquad/project/` — L4 customizations; lossy here means the install loses its bespoke configuration
- `.squidsquad/<alias>/working-state.md`, `iterations/`, `planning/` — agent state

---

## 12. Open questions & gaps

- **G1** — Migration steps for pre-#9925 installs (before the four-layer responsibility model). The upgrade flow assumes the existing install already has the L1-L4 structure; pre-#9925 installs would need a one-off migration. Not yet specified.
- **G2** — L4 backfill from the human's auto-memory directory (`~/.claude/projects/<repo>/memory/`) — referenced from [COMPOSE-ARCHITECTURE.md §10.4](COMPOSE-ARCHITECTURE.md) but not yet implemented as an installer step. Open: should the installer offer to import these on upgrade, or is this a separate one-off tool?
- **G3** — Multi-tenant install (one repo hosting multiple SquidSquad teams) — likely deferred. Today's model is one SquidSquad install per repo.
- **G4** — Atomic install across Phase 5–8. Today the scaffold (Phase 5) writes locally before the commit (Phase 8); a hard crash between them leaves the filesystem written but no git history. The interrupted-install recovery path in §11.2 handles this, but the model isn't truly atomic.
- **G5** — ✅ MOOT (rev: capability removal). The previous concern about "capability hot-swap at install time" is no longer applicable — tool/MCP/CLI configuration is per-agent post-install per §8, not an install-time concern. Adding or swapping a tool is a runtime L4 write, not a re-run-the-installer flow.

---

## 13. References

- [`references/wizard/WIZARD.md`](../references/wizard/WIZARD.md) — the step-by-step installer runbook (700+ lines)
- [`references/scripts/wizard.py`](../references/scripts/wizard.py) — main wizard helper
- [`references/scripts/shared_fs.py`](../references/scripts/shared_fs.py) — shared filesystem init
- [`references/scripts/compose.py`](../references/scripts/compose.py) — compose pipeline
- [`references/scripts/forgejo_setup.py`](../references/scripts/forgejo_setup.py) — Forgejo backend (alt tracker)
- [`start.sh`](../start.sh) — post-install boot script
- [`AGENT-RUNTIME.md`](AGENT-RUNTIME.md) — what runs after install
- [`COMPOSE-ARCHITECTURE.md`](COMPOSE-ARCHITECTURE.md) — composed CLAUDE.md generation
- [`sub-skill-catalog.md`](sub-skill-catalog.md) — sub-skills the installer wires up
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — overall system architecture

---

## 14. Revision log

- **2026-05-23 (v1 draft)** — initial draft. Consolidates the install flow into one architecture doc, distinct from the step-by-step WIZARD.md runbook. Locks the two-phase (conversation, then atomic commit) model, the ephemeral-installer-agent commitment, and the simple "pull latest sources + recompose" upgrade flow. Open gaps in §12 carry forward to follow-up issues.
- **2026-05-23 (v1 draft, capability removal)** — §8 rewritten. SquidSquad no longer has a "capability" framework at install time. Tool/MCP/CLI configuration is per-agent post-install: the human tells each agent what tools to use, the agent persists via L4 writes per [COMPOSE-ARCHITECTURE.md §7](COMPOSE-ARCHITECTURE.md). All references in §3 (inputs), §4 (Phase 1 conversation, Phase 5 atomic write), and §5 (file layout) updated to drop capability mentions. The prior `references/sub-skills/capabilities/` directory and `common/capability-check.md` are marked as architectural deadwood; follow-up task against `worker` (skill) to remove them.
- **2026-05-23 (v1 draft, R1 fixes)** — DS round-1 surfaced 8 findings (4 ERROR, 3 WARNING, 1 LOW). All applied: (1) 3 broken §7→§10 cross-refs for the upgrade flow location; (2) Phase 3 review screen example still leaked "Figma design; local delivery" — replaced with capability-free spec; (3) §11.1 "Phases 0–6 make no changes" rewritten honestly — Phases 0–4 don't touch the target repo, Phases 5–7 are pre-commit local + forge writes, Phase 8 is the atomic commit; (4) Step vs Phase numbering clash — added an explicit numbering-note callout at the end of §2, replaced "Step 7 commit" in the diagram with "Phase 8 commit"; (5) "Phase 5c" for Forgejo → "WIZARD Step 5c" (the wizard's step number, mapped into this doc's Phase 1 conversation); (6) §10 upgrade flow expanded with a user-confirm gate showing a changeset summary, and an explicit harness-restart specification (`POST /agents/<role>/stop` + `POST /agents/<role>/start` per role, falling through to `start.sh` if the harness isn't running); (7) NEW §4.8 Phase 4 dedicated approval section — describes the Approve / Edit / Abort prompt format and the "last clean abort point" semantics; (8) §3.2 outputs row for runtime harness files now lists `.harness-port` + `.harness-state.json` + `.event-state.json` together with a "harness-owned, not installer-written" note. Phase numbering renumbered downstream: old §4.7 (Phase 4–5 bundled) split into §4.7 Phase 4 + §4.8 Phase 5; §4.8–4.11 shifted to §4.9–4.12. DS artifact: `.squidsquad/pm/planning/REVIEW-INSTALLER-ARCH-DEEPSEEK-1.md`.
- **2026-05-23 (v1 draft, clone isolation mandatory + secret-file clarity)** — Two small clarifications. (a) NEW §1.2: clone isolation is a hard architectural commitment, not a configurable mode. The installer always creates the per-role clone-path registry at `~/.squidsquad/clones/`. All conditional phrasing ("if clone isolation enabled", "when enabled") removed across §3.2 outputs row, §4.2 ~/.squidsquad tree, and §5 layout footer. (b) `~/.squidsquad/clones/` was described as containing the clones themselves; corrected — it contains a *registry* (one file per role with the absolute path to that role's clone). Clones live wherever the operator places them on disk.
- **2026-05-23 (v1 draft, categorical roles + R2 fixes)** — Two related changes.
  - **Categorical roles**: prose now talks about the four categorical role classes (**PM / workers / verifiers / DM**) rather than specific concrete role names (`be`, `fe`, `skill`, `qa`, `dev`, etc.). The concrete roster — `pm/dev/qa/dm` for the default preset, `pm/fe/be/qa/dm` for the frontend-backend preset, etc. — is now framed as a *team preset* selected during install. NEW §1.1 introduces this terminology. §3.1 inputs row now says "team preset (which workers and verifiers)" rather than "team shape (which dev roles)". §4.4 Phase 1 conversation reframes "Intent + specialist roster" as "Team preset" with the wizard offering a small named set (default, frontend-backend, multi-platform, custom). §4.5 install spec uses `team_preset:` + `workers:` + `verifiers:` keys. §4.6 review screen example uses preset-shape language ("PM + N workers + M verifiers + DM"). §4.9 compose iterates "PM, each worker, each verifier, DM" not concrete names. §5 file layout uses `<worker-role>/` + `<verifier-role>/` placeholders alongside the always-present `pm/` and `dm/`; explicit note that the default-preset names shown are illustrative.
  - **R2 fixes**: DS round-2 returned 3 new findings (1 ERROR, 2 WARNING) on top of R1. Applied: (1) dead `(MEMORY)` link targets in §3.2 and §9 replaced with inline descriptions (clone isolation principle, tracker abstraction principle); (2) Phase 7 flowchart node "(labels + initial issues)" → "(initial issues)" — labels were already documented as Phase 5 work; (3) §12 G4 reference to "Phase 5.1" → "§11.2" (the interrupted-install recovery path; "Phase 5.1" was not a real section ID). DS artifact: `.squidsquad/pm/planning/REVIEW-INSTALLER-ARCH-DEEPSEEK-2.md`.
