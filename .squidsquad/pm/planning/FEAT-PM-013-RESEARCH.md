# FEAT-PM-013 Research — Setup Flow Improvements

## Summary

The current SquidSquad setup flow splits work between a Node CLI (`npx squidsquad`) and an interactive Claude session (`/squidsquad-setup`). The CLI handles prerequisites, file fetching, and committing, then launches Claude which runs the WIZARD.md runbook. The problem: the wizard mixes mechanical scaffolding (directory creation, config serialization, label creation, boot script generation, template composition) with interactive decisions (agent selection, stack questions, loop interval). This means Claude spends tokens on deterministic work that a script could handle, and failures in mechanical steps require debugging inside a conversational LLM session.

The proposed restructure follows the transport-vs-behavior layering from #2070: scripts own all scaffolding (transport), Claude owns only the interactive conversation (behavior). A new `setup.py` (or extended `wizard.py`) would take a config spec as input and produce a complete `.squidsquad/` tree deterministically and idempotently. Claude's wizard role shrinks to: ask questions, collect answers into a spec JSON, hand the spec to the script, print post-setup instructions.

This is a significant refactor touching the CLI entry point, the wizard runbook, wizard.py, compose.py, and the slash command. The payoff is faster installs, fewer failure modes, repeatability (re-run from config), and a clean upgrade path where `/squidsquad-upgrade` becomes "re-run setup with existing config."

## Current Flow Audit

### Phase 1: `npx squidsquad` (Node CLI — `packages/cli/index.js`)

| Step | What it does | Type | Produces |
|------|-------------|------|----------|
| Banner | Print squid ASCII art | MECHANICAL | Terminal output |
| Check existing | Abort if `.squidsquad/` exists | MECHANICAL | Early exit |
| checkNodeVersion | Verify Node 18+ | MECHANICAL | Pass/fail |
| checkPython | Verify Python 3.8+ | MECHANICAL | Pass/fail |
| checkGhCli | Verify gh installed + authenticated | MECHANICAL | Pass/fail |
| checkClaudeCli | Verify claude CLI installed | MECHANICAL | Pass/fail |
| Fetch manifest | Download `references/installer-files.txt` | MECHANICAL | File list |
| Fetch all files | Download 119 files from GitHub raw | MECHANICAL | Files on disk |
| Create slash command | Write `.claude/commands/squidsquad-setup.md` | MECHANICAL | Slash command file |
| Git commit | Stage and commit all fetched files | MECHANICAL | Git commit |
| Repo scan | Run `repo_scan.py --save` | MECHANICAL | `.squidsquad/.repo-scan.json` |
| Ask launch | Prompt "Launch SquidSquad setup now?" | INTERACTIVE | y/n |
| Launch Claude | `claude --dangerously-skip-permissions /squidsquad-setup` | MECHANICAL | Claude session |

### Phase 2: `/squidsquad-setup` (Claude session — WIZARD.md runbook)

| Step | What it does | Type | Produces |
|------|-------------|------|----------|
| Step 0 — gh check | `wizard.py check-gh` | MECHANICAL (already done by CLI) | Redundant check |
| Step 0a — shared FS | `shared_fs.py init` | MECHANICAL | `~/.squidsquad/` directory |
| Step 0b — re-run detection | `wizard.py check-existing` | MECHANICAL | Exists/not decision |
| Step 1 — project details | `wizard.py repo-info` + confirm with user | MIXED — detection is mechanical, confirmation is interactive | Project name, repo slug |
| Step 1b — adaptive context | 3-5 questions about project | INTERACTIVE | Project description, domain context, conventions |
| Step 2 — intent + roster | Show roles, classify free-text intent | INTERACTIVE | Preset selection (software-dev/design) |
| Step 3 — preset confirmation | Show pipeline, ask y/n/a | INTERACTIVE | Confirmed preset |
| Step 4 — setup requirements | Walk manifest-driven questions per role | INTERACTIVE | Per-agent config (variant, stack, test command) |
| Step 5 — loop interval | Ask interval + context threshold | INTERACTIVE (with defaults) | Loop config |
| Step 5b — model routing | Discover providers, ask about routing | MIXED — discovery is mechanical, selection is interactive | Model routing config |
| Step 5c — forge backend | Ask GitHub vs Forgejo | INTERACTIVE (rarely used) | Forge config |
| Step 6 — review screen | Render summary, ask P/V/E/A | INTERACTIVE | User confirmation |
| Step 7.1 — cleanup | Delete existing if full rebuild | MECHANICAL | Clean slate |
| Step 7.2 — serialize spec | Build JSON install spec | MECHANICAL | Spec JSON |
| Step 7.3 — scaffold | `wizard.py scaffold spec.json .` | MECHANICAL | `.squidsquad/` tree |
| Step 7.4 — labels | `wizard.py ensure-labels` | MECHANICAL | GitHub labels |
| Step 7.5 — commit + push | `git add`, `git commit`, `git push` | MECHANICAL | Git commit |
| Step 7.6 — ready message | Print boot instructions | MECHANICAL | Terminal output |

### Classification Summary

**Purely MECHANICAL** (can be fully scripted):
- All prerequisite checks (already mostly in CLI)
- Shared filesystem init
- Re-run detection
- Repo info detection
- Repo scan (already in CLI)
- Model provider discovery
- Spec serialization to JSON
- Directory scaffolding via `wizard.py scaffold`
- CLAUDE.md composition via `compose.py deploy`
- Boot script generation via `compose.py boot`
- GitHub label creation
- Config.md generation from spec
- Git commit + push
- Post-setup instructions

**Purely INTERACTIVE** (need Claude):
- Adaptive context questions (Step 1b)
- Intent classification and roster (Step 2)
- Preset confirmation (Step 3)
- Setup requirements walk — variant, stack, test commands (Step 4)
- Loop interval (Step 5 — though defaults could be pre-filled)
- Review and confirmation (Step 6)

**MIXED** (mechanical detection + interactive confirmation):
- Project name/repo (detect, then confirm)
- Model routing (discover, then ask)
- Forge backend (ask, then script handles deployment)

## Known Issues

Issues encountered during external project deployment:

1. **#2009 — Boot scripts were wrong**: Boot script generation had bugs. Fixed, but highlights that compose.py boot is fragile and should be tested deterministically, not generated ad-hoc during an LLM conversation.

2. **#2008 — statusLine was wrong**: Status line configuration was incorrect in generated files. Again, a mechanical generation bug that is harder to debug when it happens inside a Claude session.

3. **#2006 — No PR Flow question**: The wizard did not ask about PR flow during setup. Approved and now included, but illustrates that adding a new question requires editing the wizard runbook AND the manifest, when it should just be a manifest change.

4. **#2006 — No post-setup instructions**: After setup completed, the user got no guidance on what to do next. The "ready" message in Step 7.6 exists but was either skipped or insufficient.

5. **Redundant gh check**: Step 0 in the wizard re-checks gh auth, which the CLI already verified. Wastes a Claude turn on something already confirmed.

6. **Config schema mismatch**: The existing `config.md` in this repo uses Architecture Version 1 (flat format), while `wizard.py build_config_md` generates Architecture Version 2 (nested agent format). A new install on an existing project would produce a v2 config that existing agents may not parse correctly.

7. **No validation of generated output**: After `wizard.py scaffold` runs, there is no validation step to confirm that CLAUDE.md files were composed correctly, boot scripts are syntactically valid, or config.md parses back to the same spec.

8. **No rollback on failure**: If Step 7.3 succeeds but Step 7.4 (labels) fails, the user has a partial install. The wizard says "don't rollback" but this is still confusing.

9. **Repo scan happens before Claude launches but results are not shown to the user**: The CLI runs `repo_scan.py --save` but the wizard does not surface the scan results during the adaptive questions. The scan data is only used during scaffold to seed SOUL.md responsibilities.

10. **119-file fetch is slow**: Downloading 119 files one-by-one via `gh api` is slow (each is an HTTP request). A tarball or zip download would be much faster.

## Proposed Restructure

### New Flow: Script-First, Claude-Minimal

```
npx squidsquad
  |
  +-- Phase 1: Prerequisites (same as today, Node CLI)
  |     - Check Node, Python, gh, claude
  |     - Detect git root
  |
  +-- Phase 2: Fetch files (same as today, Node CLI)
  |     - Download manifest + files
  |     - Commit
  |
  +-- Phase 3: Auto-detect (NEW — run before Claude)
  |     - repo_scan.py --save (already done)
  |     - wizard.py repo-info -> save to .repo-info.json
  |     - shared_fs.py init
  |     - wizard.py check-existing -> save to .install-state.json
  |     - model_router.py list-providers -> save to .providers.json
  |     - Generate default spec from scan + repo-info
  |
  +-- Phase 4: Interactive (Claude session — MUCH shorter)
  |     - Read auto-detected defaults
  |     - Ask ONLY the interactive questions (1b, 2, 3, 4, 5, 6)
  |     - Write answers to spec JSON
  |
  +-- Phase 5: Scaffold (script — NOT Claude)
  |     - wizard.py scaffold spec.json .
  |     - wizard.py ensure-labels
  |     - git commit + push
  |     - Print post-setup instructions
```

### Key Changes

1. **Pre-compute defaults before Claude launches**: Run repo scan, repo-info, provider discovery, and existing-install detection as Node CLI steps. Save results to temp JSON files. Claude reads them instead of running the commands.

2. **Claude's wizard shrinks to ~5 questions**: With defaults pre-filled from scan results, Claude asks: (1) confirm project name, (2) describe project + 2-3 context questions, (3) what are you building (intent), (4) confirm pipeline, (5) confirm review screen. Most have smart defaults the user just presses Enter to accept.

3. **Scaffold runs as a post-Claude script**: After Claude writes the spec JSON, the CLI (or a `setup.py finish` command) handles scaffold, labels, commit, push, and prints instructions. If Claude crashes during the interactive phase, the user re-runs and their answers are re-asked — but nothing is partially written to disk.

4. **Idempotent from config**: `wizard.py scaffold` already takes a spec JSON. If we save the spec JSON as `.squidsquad/.install-spec.json`, then `npx squidsquad` can detect it on re-run and offer to regenerate from it. This makes upgrade trivial.

### Data Flow

```
repo_scan.py ──┐
repo-info    ──┤
providers    ──┼── defaults.json ──> Claude (interactive) ──> spec.json ──> scaffold
existing     ──┘
```

## Interactive Questions

Complete list of questions the wizard should ask, with defaults:

### Always Asked

| # | Question | Default | Source |
|---|----------|---------|--------|
| 1 | Confirm project name | From `gh repo view` or directory name | Auto-detected |
| 2 | What does your project do? | From `gh repo view --json description` | Auto-detected, needs elaboration |
| 3 | Tech stack / test commands / conventions (adaptive Q2-Q3) | From repo scan | Auto-detected, confirm |
| 4 | What are you building? (intent classifier) | None — must ask | Free text |
| 5 | Confirm pipeline (y/n/a) | y | Derived from intent |

### Conditional on Preset

| # | Question | When | Default |
|---|----------|------|---------|
| 6 | Include a designer? | software-dev preset | No |
| 7 | Dev variant (both/fullstack/be/fe)? | software-dev preset | both (if scan shows FE+BE), fullstack otherwise |
| 8 | Stack per dev agent | software-dev, per agent | From repo scan |
| 9 | Test command per dev agent | software-dev, per agent | From repo scan (jest/pytest/etc.) |

### Optional / Advanced

| # | Question | Default |
|---|----------|---------|
| 10 | Loop interval (minutes) | 10 |
| 11 | Context pressure threshold | 80 |
| 12 | Model routing (y/N) | No |
| 13 | If model routing yes: provider + model | First available provider, its default model |
| 14 | Forge backend (GitHub/Forgejo) | GitHub |
| 15 | PR flow (y/N) | No |
| 16 | Working branch name | main (from current branch) |
| 17 | State branch name | squid-squad |

### Derived (Not Asked, Computed)

- Agent list (from preset + variant + designer choice)
- Agent aliases (default to agent id)
- Flags: improvement_scan=yes, vault_remember=yes, diagnostics=yes
- Tools: designer.tool=null (deferred), dm.tool=local_delivery
- Architecture version: 2
- SquidSquad version: from SKILL.md frontmatter

## Auto-Detection

What the repo scan can detect mechanically (already implemented in `repo_scan.py`):

| Category | Detection Method | Wizard Use |
|----------|-----------------|------------|
| Languages | File extension counting | Suggest dev variant (e.g., .py + .ts = both) |
| Package managers | Marker files (package.json, pyproject.toml, etc.) | Pre-fill stack |
| Frameworks | Config files (next.config.js, manage.py, etc.) | Pre-fill stack |
| Test frameworks | Config files (jest.config.js, conftest.py, etc.) | Pre-fill test command |
| CI/CD | Workflow files (.github/workflows, etc.) | Inform DM responsibilities |
| Deploy targets | Config files (Dockerfile, vercel.json, etc.) | Inform DM responsibilities |
| Monorepo markers | lerna.json, pnpm-workspace.yaml, etc. | Suggest multi-agent dev |
| Git remote | `git remote get-url origin` | Pre-fill repo slug |
| Description | `gh repo view --json description` | Seed Q1 in adaptive questions |
| Current branch | `git branch --show-current` | Default working branch |

### Additional Detection Opportunities

1. **Test command inference**: If `package.json` has a `test` script, extract it. If `pyproject.toml` has `[tool.pytest]`, suggest `pytest`. If `Makefile` has a `test` target, suggest `make test`.
2. **Existing CI test commands**: Parse `.github/workflows/*.yml` for `run: npm test` or similar patterns.
3. **Project structure**: If `src/frontend/` and `src/backend/` exist, suggest `both` variant. If only `src/` exists, suggest `fullstack`.
4. **Existing CLAUDE.md**: If a project-level CLAUDE.md already exists, note that SquidSquad will use `.squidsquad/*/CLAUDE.md` (not the root one) so the user's existing file is preserved.

## Agent Selection Guide

### Minimal Viable Setup

Every install gets:
- **PM** (always_installed: true) — coordinates the team, talks to human
- **QA** (always_installed: true) — verifies work
- **DM** (always_installed: true) — handles delivery

These three are infrastructure roles and are not shown in the roster. The user does not choose them.

### Specialist Selection

The wizard should guide based on intent:

| Intent | Specialists Added | Pipeline |
|--------|------------------|----------|
| software-dev (default) | Dev (1-2 agents) | PM -> [Designer] -> Dev -> QA -> DM |
| software-dev + design | Dev + Designer | PM -> Designer -> Dev -> QA -> DM |
| design only | Designer | PM -> Designer -> DM |

### Recommendation Logic

1. If repo scan detects code (any language files > 10): default to `software-dev`
2. If repo scan detects both frontend and backend markers: default to `both` variant
3. If repo is empty or has only docs: ask intent, no strong default
4. Designer is opt-in for software-dev (most projects do not need it)
5. For a first-time user, the simplest path is: `software-dev` with `fullstack` variant = PM + 1 dev + QA + DM = 4 agents

### Guided Selection UX

Instead of listing all options, the wizard should propose based on scan:

> I scanned your repo and found: Next.js + TypeScript in the frontend, FastAPI + Python in the backend, with pytest and jest for testing.
>
> I'd suggest two dev agents:
>   - **fe** — Next.js + TypeScript (jest)
>   - **be** — FastAPI + Python (pytest)
>
> Plus PM, QA, and DM (always present). Sound right?

This is much better than asking "which variant do you want?" cold.

## Impact Analysis

- **Files touched**:
  - `packages/cli/index.js` — add Phase 3 auto-detection, Phase 5 post-Claude scaffold
  - `references/wizard/WIZARD.md` — significantly shorten, remove mechanical steps
  - `references/scripts/wizard.py` — add `generate-defaults` command, `finish-install` command
  - `references/scripts/repo_scan.py` — add test command inference, structure detection
  - `.claude/commands/squidsquad-setup.md` — update to reflect shorter wizard
  - `references/installer-files.txt` — may need new scripts added

- **Behavior changes**:
  - Setup is faster (less Claude token usage, less round-trips)
  - Defaults are smarter (repo scan informs suggestions)
  - Scaffold happens outside Claude (more reliable, deterministic)
  - Config spec is saved (enables idempotent re-runs)

- **Dependencies**:
  - repo_scan.py must run before Claude
  - wizard.py must support a `generate-defaults` command
  - Claude's wizard must read pre-computed defaults instead of running commands
  - Post-Claude finish step must be orchestrated by the CLI

## Side Effects

1. **Risk: CLI complexity increases**: Moving scaffold logic to the CLI means the CLI needs to run Python scripts and handle their errors. Currently the CLI is pure Node; this would add a Python orchestration dependency to the CLI itself. Mitigation: keep the CLI thin and have it call `wizard.py finish-install spec.json` as a single command.

2. **Risk: Two-phase install can leave the user in limbo**: If Claude finishes the interactive phase and writes spec.json, but the user closes the terminal before Phase 5 runs, they have a spec but no scaffold. Mitigation: on next `npx squidsquad`, detect `.install-spec.json` and offer to resume from it.

3. **Risk: Backward compatibility with existing installs**: Existing installs have v1 config.md. If `npx squidsquad` is run on a repo with an existing `.squidsquad/`, the CLI currently aborts. This is correct behavior — upgrade should use `/squidsquad-upgrade`.

4. **Risk: Repo scan may give wrong defaults**: If the scan detects Jest but the user actually uses Vitest (both config files present), the default will be wrong. Mitigation: always ask for confirmation, never silently apply defaults.

## Edge Cases

1. **Empty repo**: No files to scan, no remote, no description. All defaults are empty. Wizard must handle gracefully — skip scan-informed suggestions, ask everything from scratch.

2. **Monorepo**: Multiple package.json files, multiple languages. Scan should detect monorepo markers and suggest multi-agent setup. The variant question becomes more nuanced.

3. **Non-GitHub remote**: If the repo uses GitLab or Bitbucket, `gh repo view` fails. The wizard falls back to git remote parsing but labels will fail. Forge backend question becomes critical.

4. **Existing SquidSquad install**: The CLI already handles this (abort + point to upgrade). No change needed.

5. **No internet**: File fetch fails. The CLI already handles this with error messages.

6. **Windows vs Linux/macOS**: Boot scripts are already templated for both. repo_scan.py and wizard.py work cross-platform. The CLI uses Node which is cross-platform. No new edge cases.

7. **Python not available**: The CLI checks for Python 3.8+. If missing, it aborts with install instructions. This is correct.

8. **Claude session crashes mid-wizard**: Today, this leaves no trace (nothing written before Step 7). In the new flow, nothing is written until Phase 5, which is the same guarantee. The user re-runs and re-answers questions.

9. **User aborts at review screen**: Same as today — no trace. Spec JSON could be saved to a temp file for resume, but this is optional.

10. **Re-running setup on a repo where only some labels were created**: `ensure-labels` is already idempotent. No issue.

## Upgrade & Migration

### Upgrade Path

The proposed restructure creates a natural upgrade path:

1. **Fresh install**: `npx squidsquad` runs full flow (Phase 1-5).
2. **Upgrade**: `/squidsquad-upgrade` reads existing `config.md`, generates a spec JSON from it, re-runs `wizard.py scaffold` with `overwrite_existing=True`. CLAUDE.md files are regenerated, SOUL.md and working-state.md are preserved.
3. **Re-configure**: User wants to change agents or settings. `npx squidsquad --reconfigure` (or `/squidsquad-setup` with `regenerate` action) reads existing config, lets user edit answers, re-scaffolds.

### If spec.json is saved

If we save the install spec as `.squidsquad/.install-spec.json`:
- Upgrade becomes: read spec, bump version, re-scaffold
- Reconfigure becomes: read spec, edit interactively, re-scaffold
- The spec is the single source of truth, config.md is a generated view of it

### Migration for existing installs

Existing installs have v1 config.md (flat format). A migration path is needed:
- `wizard.py migrate-config` could parse v1 config.md and produce a spec JSON
- Or: `/squidsquad-upgrade` already handles this by reading config.md and regenerating

### Interaction with `/squidsquad-upgrade`

Currently, `/squidsquad-upgrade` is a parallel-agent approach that regenerates templates per role. With the new setup flow:
- Simple upgrades (new SquidSquad version, same config): `wizard.py scaffold` with existing spec
- Config changes (add/remove agents): re-run interactive wizard with pre-filled spec
- Both can be idempotent: scaffold from spec always produces the same output

## Open Questions

- **Q1**: Should the spec JSON be committed to the repo (`.squidsquad/.install-spec.json`) or kept local? — **Why**: If committed, it enables team-wide reproducibility but adds a file that might confuse users. If local-only, upgrade must reconstruct the spec from config.md every time.

- **Q2**: Should Phase 5 (scaffold) run inside the Claude session or as a separate process after Claude exits? — **Why**: Running inside Claude means the wizard can show errors interactively. Running outside means less token usage and more reliability. A hybrid approach (Claude writes spec, CLI scaffolds, reports back) might be best.

- **Q3**: How much of the repo scan should be surfaced to the user? — **Why**: Showing "I detected Next.js + TypeScript" builds trust. Showing a full JSON dump is overwhelming. The wizard should pick the top 3-5 most relevant detections to mention.

- **Q4**: Should the wizard support a `--non-interactive` mode for CI/scripted installs? — **Why**: If the spec JSON format is stable, `npx squidsquad --spec spec.json` could skip the Claude session entirely. Useful for teams deploying SquidSquad to many repos.

- **Q5**: How should model routing key setup integrate with the new flow? — **Why**: Key setup requires the user to edit `~/.squidsquad/secrets`, which is a side-channel action. The wizard currently guides this interactively. In a script-first flow, the script could open the secrets file and prompt.

- **Q6**: The 119-file fetch is slow. Should we switch to a tarball/zip download? — **Why**: Single HTTP request vs 119. Major UX improvement. Could use `gh api` to download a tar.gz of the `references/` subtree.

## Recommendation

**Proceed with the restructure, but in phases:**

**Phase A — Pre-compute defaults (low risk, high value)**: Extend the CLI to run repo scan, repo-info, provider discovery, and shared-fs init BEFORE launching Claude. Save results to temp JSON files. Update WIZARD.md to read these files instead of running the commands. This alone removes ~4 mechanical steps from the Claude session.

**Phase B — Save install spec (medium risk, high value)**: After Claude finishes the interactive phase (Step 6 approval), save the spec JSON to `.squidsquad/.install-spec.json`. This enables idempotent re-runs and simplifies upgrade.

**Phase C — Post-Claude scaffold (medium risk, high value)**: Move Step 7 (scaffold, labels, commit, push) out of the Claude session. The CLI orchestrates this after Claude exits. Claude's job becomes: ask questions, write spec JSON, exit.

**Phase D — Smart defaults from scan (low risk, medium value)**: Use repo scan data to pre-fill variant, stack, and test command questions. Show the user what was detected and let them confirm or override.

**Phase E — Upgrade integration (depends on B+C)**: Once spec JSON is saved, `/squidsquad-upgrade` can read it, bump the version, and re-scaffold without re-asking questions.

Each phase is independently shippable and testable. Phase A is the lowest-hanging fruit and should ship first.
