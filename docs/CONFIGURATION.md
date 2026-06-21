# SquidSquad Configuration Reference

This is the complete reference for everything you can configure in a SquidSquad install. All settings live in one file:

```
.squidsquad/config.md
```

It's plain Markdown — sections are `## Headings` and each setting is a `- **Field**: value` bullet. SquidSquad reads it through `config.py`; the compose pipeline and every agent's scripts pull their settings from here, so a typo or a removed field can change how the whole team behaves.

## How to edit it safely

- **Most settings are read live.** Changing a value takes effect the next time an agent or the compose pipeline reads it — you generally don't need to restart anything for tuning values (intervals, thresholds, model choices). Changes that affect an agent's composed instructions (agents/aliases, test commands) require a recompose + reboot to take hold.
- **A few settings are system-managed — don't hand-edit them** (see [System-managed](#system-managed-dont-hand-edit)). The ship counter in particular is kept in a separate file now; the value in `config.md` is ignored.
- **Keep the field names exact.** Lookups match on the field name; renaming or misspelling a field makes it fall back to a default (or break the feature).
- **Values are read as text.** `yes`/`no` for toggles, plain numbers for counts, `30m`-style for durations where noted.

When in doubt, change one thing at a time and watch the squad's behavior.

---

## Quick map

| Group | Sections | You set this… |
|---|---|---|
| [Identity & versioning](#identity--versioning) | SquidSquad Version, Tracker, Architecture Version | at install |
| [Agents & aliases](#agents--aliases) | Agents, Aliases | at install |
| [Project](#project) | Project | at install |
| [Test commands](#test-commands) | Test Commands | at install |
| [Git](#git) | Git Protocol, Git Branches | at install |
| [Cadence & resources](#cadence--resources) | Iteration Interval, Context Pressure, Agent Effort | tune anytime |
| [Delivery & versioning](#delivery--versioning) | Auto Merge, PR Flow, Auto Versioning | tune anytime |
| [Improvement scanning](#improvement-scanning) | Improvement Scanning | tune anytime |
| [Vault (memory)](#vault-memory) | Vault Optimize, Vault Remember | tune anytime |
| [Approval & diagnostics](#approval--diagnostics) | Mandatory Human Approval, Diagnostics | tune anytime |
| [Model routing](#model-routing) | Model Routing | tune anytime |
| [Harness & events](#harness--events) | Harness, Event Reactions | mostly automatic |
| [Forge backend](#forge-backend) | Forge Backend | at install |
| [System-managed](#system-managed-dont-hand-edit) | (counter, deprecated keys) | don't touch |

---

## Identity & versioning

| Field | Example | What it controls |
|---|---|---|
| `SquidSquad Version` | `0.44.0` | The installed framework version. Updated by the version-bump process at release; don't edit by hand. |
| `Tracker` | `github-issues` | Which issue tracker backs the forge. Today only `github-issues` is supported. |
| `Architecture Version` | `1` | Internal config-schema version for upgrade handling. Leave as-is. |

## Agents & aliases

Defines which agent roles run and what each one is called.

```
## Agents
- **Workers**: skill
- **PM**: always present
- **QA**: always present
- **DM**: present

## Aliases
- **skill**: skill
- **pm**: pm
- **dm**: dm/skill
- **qa**: qa
```

| Field | What it controls |
|---|---|
| `Workers` | Comma-separated list of worker agents (one per specialization, e.g. `skill`, `web`, `ios`). This is the canonical field. *(Older installs may still say `Dev Agents` — that name is deprecated; see [System-managed](#system-managed-dont-hand-edit).)* |
| `PM` / `QA` / `DM` | Whether the coordinator, verifier, and delivery roles are present. |
| `Aliases` block | Maps each alias to its role class. The form `dm: dm/skill` gives the DM a domain specialization (`skill`). Routing on the forge targets these aliases. |

> Changing agents/aliases changes composed instructions — recompose (`compose.py deploy <alias>`) and reboot the affected agents afterward.

## Project

| Field | Example | What it controls |
|---|---|---|
| `Name` | `SquidSquad` | Project name, used in docs/prompts. |
| `Repo` | `github.com/owner/repo` | The repository the squad works in. |
| `Intent Description` | `(not set)` | Optional one-line statement of what the project is for; surfaced to agents for context. |

## Test commands

How the squad runs your tests.

| Field | Example | What it controls |
|---|---|---|
| `<worker> Tests` | `python tests/run_tests.py` | The command a given worker runs for its test suite (one line per worker, keyed by the worker's name, e.g. `skill Tests`). |
| `E2E Tests` | `(none)` | Optional end-to-end test command run during verification. `(none)` disables it. |

## Git

```
## Git Branches
- **Working Branch**: main
- **State Branch**: squid-squad
- **Branch Pattern**: squidsquad/task/{number}
```

| Field | What it controls |
|---|---|
| `Working Branch` | The branch finished work lands on (usually `main`). |
| `State Branch` | The branch that holds squad operational state, kept separate from code. |
| `Branch Pattern` | The naming template for per-task feature branches; `{number}` is the issue number. |
| `Git Protocol` block | Plain-language reminders (pull before work, push after each unit, append-only discussion). Informational. |

## Cadence & resources

| Field | Example | What it controls |
|---|---|---|
| `Iteration Interval` → `Minutes` | `30` | How often a polling-mode agent runs a cycle. (In event mode agents wake on activity instead, but this still sets the idle self-check cadence.) |
| `Context Pressure` → `Threshold` | `70` | The percent-of-context level at which an agent checkpoints and restarts for a fresh session. Lower = restart sooner. |
| `Agent Effort` | `effort-pm: high` | Per-agent effort/quality level (`effort-<alias>`). Higher means more thorough, more expensive cycles. |

## Delivery & versioning

| Field | Example | What it controls |
|---|---|---|
| `Auto Merge` → `Enabled` | `yes` | Whether verified PRs are merged automatically by the squad. |
| `PR Flow` → `Enabled` | `yes` | Whether work goes through feature branches + pull requests (the standard flow). |
| `Auto Versioning` → `Ship Threshold` | `10` | How many shipped items accumulate before a version bump is cut. |
| `Auto Versioning` → `Shipped Since Last Bump` | — | **System-managed — do not edit.** The live counter lives in `.squidsquad/.ship-counter`; the value here is ignored (see [System-managed](#system-managed-dont-hand-edit)). |

## Improvement scanning

When idle, agents scan for process/doc/quality improvements.

| Field | Example | What it controls |
|---|---|---|
| `Enabled` | `yes` | Master switch for idle improvement scans. |
| `Improvement Scan Cool-Down` | `30m` | Minimum time between idle scans. |
| `Idle Scan Burst` | `3` | Maximum scans in one sustained-idle stretch before a cool-down resets the burst. |

## Vault (memory)

The vault is the squad's shared long-term memory.

| Field | Example | What it controls |
|---|---|---|
| `Vault Optimize` → `Threshold` | `20` | How many entries accumulate before a compaction/de-dup pass runs. |
| `Vault Remember` → `Writes Per Cycle` | `2` | Max new memory entries an agent may write per cycle. |
| `Vault Remember` → `BRIEFING Token Budget` | `2000` | Size budget for the auto-maintained briefing summary agents read at boot. |
| `Vault Remember` → `Confidence Decay Days` | `60` | How long before a memory's confidence decays without reinforcement. |

## Approval & diagnostics

| Field | Example | What it controls |
|---|---|---|
| `Mandatory Human Approval` → `Enabled` | `yes` | Whether new features require a human approval gate before the squad builds them. Strongly recommended `yes`. |
| `Diagnostics` → `Enabled` | `yes` | Whether the squad collects local diagnostics. |
| `Diagnostics` → `Upstream Reporting` | `ask` | Whether diagnostics may be sent upstream: `ask` (prompt first), or other policy values. |

## Model routing

Which AI model handles each kind of work. Values are model identifiers; `claude` selects the default Claude model.

| Field | Example | Used for |
|---|---|---|
| `Default Model` | `claude` | General agent work when nothing more specific applies. |
| `Research Model` | `deepseek-v4-pro` | Research-heavy tasks. |
| `Discussion Prep Model` | `claude` | Preparing task discussions. |
| `Test Plan Model` | `claude` | Deriving test plans. |
| `QA Execution Model` | `claude` | Running verification. |
| `Comprehension Model` | `claude` | Comprehension/coverage checks. |
| `Improvement Scan Model` | `claude` | Idle improvement scans. |
| `Code Review Model` | `deepseek-v4-pro` | Automated code review. |
| `Fallback Model` | `claude` | Used when a chosen model is unavailable. |
| `API Timeout Seconds` | `120` | Per-request timeout for model calls. |

## Harness & events

The harness supervises agent lifecycle and the event bus that wakes agents.

| Field | Example | What it controls |
|---|---|---|
| `Harness` → `Enabled` | `yes` | Whether the supervising harness runs (enables event-driven wake mode). |
| `Harness` → `Port` | `7373` | The local port the harness serves on. Also written to `.squidsquad/.harness-port`. |
| `Event Reactions` block | — | Per-role lists of which events each agent emits and reacts to. Consumed by the compose pipeline and event validation. Usually left at the shipped defaults — edit only if you're changing the event wiring. |

## Forge backend

| Field | Example | What it controls |
|---|---|---|
| `Forge Backend` → `Provider` | `github` | The backend powering the tracker/forge. |
| `Forge Backend` → `Endpoint` | `https://api.github.com` | API endpoint for that provider. |

## Other feature toggles

| Field | Example | What it controls |
|---|---|---|
| `Cycle Runner` → `Enabled` | `yes` | Whether the standard cycle-runner wraps each agent cycle. |
| `Agent Compose` → `Enabled` | `no` | Toggles an agent-compose code path. Defaults `no`; leave off unless you know you need it. |

---

## System-managed (don't hand-edit)

These appear (or used to appear) in `config.md` but are **not** operator settings:

- **`Auto Versioning` → `Shipped Since Last Bump`** — the live "shipped since last version bump" counter now lives in `.squidsquad/.ship-counter`. The value inside `config.md` is **vestigial and ignored** on read; editing it does nothing. The delivery role updates the counter file automatically.
- **`Dev Agents`** — **deprecated** alias for `Workers`. The compose pipeline still reads it as a fallback but emits a warning each time. New/cleaned installs should use `Workers:` instead.

### Legacy keys with no active effect

`config.py` recognizes a few historical keys that have **no active consumer** in the current codebase and are **not** part of a normal `config.md`. If you see them in an older file, they're inert and safe to remove: `Poll Interval`, `Queue Cap`, `Scan Cooldown`, `Scan Idle Timeout`, `Timeout Minutes`, `Max Retries`.

---

_This reference reflects the configuration surface as of SquidSquad 0.44.0. If you change which agents run or how the squad is wired, also recompose and reboot the affected agents so their instructions match._
