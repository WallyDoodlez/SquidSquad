# FEAT-PM-4083 Context — L4 Project Customization & Layer Lifecycle

## Scope

Define the full operational lifecycle of the 4-layer system: how layers are set up on fresh installs, how changes propagate between agents, and how existing installs upgrade to the layered architecture. Also adds a hard gate checklist for setup/upgrade verification.

Three phases:
- **Phase A**: Setup wizard integration for layered installs
- **Phase B**: L4 propagation mechanism (PM writes → recompose → reboot)
- **Phase C**: Upgrade path from pre-layer to post-layer installs

## Locked Decisions (human decided)

### Phase A — Setup
- Wizard asks project type during setup: "What type of project? [ios/web/android/fullstack/skill/custom]"
- Selected preset applies L3 for ALL roles at once (e.g., selecting "ios" installs dev-ios + pm-ios + qa-ios + dm-ios)
- One question, full team composition

### Phase B — Propagation
- PM writes to L4 project sub-skill files directly
- PM runs `compose.py deploy-all` to rebuild all agent templates
- PM runs `reboot_agent.py` for affected agents
- PM owns the full flow — explicit, not automatic
- No file watchers, no auto-detect, no daemon required

### Phase C — Upgrade
- `/squidsquad-upgrade` auto-detects pre-layer installs (no `references/roles/base/` directory)
- Extracts existing `## Project Adaptation` from each role's SOUL.md into L4 SOUL source files
- Sets up L1-L3 from new templates
- Recomposes all agents
- Zero content loss — accumulated Project Adaptation signals preserved in L4
- soul_adaptation.py writes to L4 going forward
- Preset selection: upgrade asks "What type of project?" (same as fresh setup) or defaults to "skill" if auto-detectable

### Setup/Upgrade Verification Gate
- Hard gate — explicit checklist before any agent marks pending-test
- All agents on this project get the gate via L4 (dev, QA, DM)
- Checklist covers setup/upgrade mechanics only (wizard.py, compose.py, /squidsquad-upgrade, includes.yml, manifest)
- Documentation updates (README, SKILL.md, CHANGELOG) are DM's responsibility, not part of this gate
- Agent must post structured checklist output as an issue comment (evidence for QA)

## Dev Discretion

- Checklist format (markdown table vs bullet list in issue comment)
- Whether to also build a helper script that scans the diff for setup-impacting changes (optional, not required)
- How wizard.py presents the preset question (interactive menu, flag, or AskUserQuestion)
- How upgrade detects pre-layer state (directory check, version check, or both)
- Whether preset selection during upgrade is interactive or inferred from existing config

## Side Effect Mitigations (required)

- Upgrade must not clobber existing SOUL.md Project Adaptation content — extract first, then recompose
- Upgrade must be idempotent — running it twice on a post-layer install is a no-op
- Fresh setup must work with no presets selected (custom = L1+L2 only, no L3)
- Propagation (compose + reboot) must handle agents being mid-cycle — wait for idle per existing reboot contract

## Out of Scope

- Harness/supervisor (#4221) — propagation uses existing compose.py + reboot_agent.py
- Documentation updates — DM's job
- New presets beyond what #3465 ships — this task uses existing presets
- Auto-detect propagation (file watcher, cycle-start check) — explicit PM flow only
