# Phase E Handoff — SquidSquad Web UI Demo Project

## What You're Doing

You are setting up a **new project** and using **SquidSquad** (a Claude Code skill) to build it with an autonomous multi-agent dev team. This simulates what a real user does when adopting SquidSquad on their own project.

The project: **SquidSquad Web UI** — a web-based dashboard for interacting with SquidSquad. It shows agent status, lets you file bugs/features, view the vault, and monitor the squad.

## Step 1 — Create the Repo

Create a new GitHub repo called `squidsquad-web` (or similar). Initialize with a basic README. Clone it locally.

```bash
gh repo create WallyDoodlez/squidsquad-web --public --clone
cd squidsquad-web
```

## Step 2 — Install SquidSquad

SquidSquad is a Claude Code skill. In a Claude Code session in the new repo, say:

```
Install the squidsquad skill from github.com/WallyDoodlez/SquidSquad
```

This installs the SKILL.md and references/ into your project. Then run the setup:

```
Set up SquidSquad
```

The setup flow will ask you:

1. **Project name**: squidsquad-web
2. **Dev agents**: `skill` (one full-stack dev agent is fine for this)
3. **Agent aliases**: defaults are fine
4. **Iteration interval**: 30 minutes
5. **E2E test command**: (none for now)
6. **Existing bugs/features to import**: see the seed list below

## Step 3 — Seed the Backlog

During setup (or after), file these as the initial features:

### Core Features
1. **Dashboard page** — real-time view of all agents: role, status (active/stalled/idle), current task, last cycle time. Reads from `.squidsquad/*/current-state` and git log.
2. **Bug/feature viewer** — list all GitHub Issues with labels, status, priority. Click to view details. Uses `gh` CLI or GitHub API.
3. **File bug/feature** — form to submit bugs or feature requests. PM picks them up via normal workflow.
4. **Vault browser** — browse vault notes (PARAG structure), view frontmatter, follow wikilinks. Read-only initially.
5. **Iteration log viewer** — view recent iteration logs per agent. Timeline view of what happened.

### Nice to Have
6. **CHANGELOG viewer** — rendered version history
7. **Config editor** — edit config.md from the UI (interval, scanning, vault-remember settings)
8. **Terminal recording embed** — show the asciinema recording from README

### Tech Stack Decision
The human prefers modern, lightweight web tech. Suggest:
- **Frontend**: React or Svelte (or even plain HTML + HTMX for simplicity)
- **Backend**: Python (FastAPI) or Node — reads from `.squidsquad/` files and `gh` CLI
- **Deployment**: Local dev server initially. Can deploy to Vercel/Railway later.

Ask the human during setup which stack they prefer.

## Step 4 — Boot the Squad

After setup, boot the agents:

```bash
# In separate terminals:
bash .squidsquad/start-skill.sh
bash .squidsquad/start-pm.sh
```

The PM will start cycling, the skill-lead will pick up approved features. You (the human) interact with PM to prioritize, approve, and review.

## Step 5 — Let It Run

This is the demo. SquidSquad builds the web UI autonomously:
- PM files and plans features
- Skill-lead implements them
- PM verifies and ships
- The vault captures decisions and patterns
- The whole process is visible in git history

## What Success Looks Like

1. SquidSquad setup completes cleanly on a fresh repo
2. Agents boot and start cycling
3. At least 2-3 features ship via the normal workflow
4. The web UI is functional (shows agent status at minimum)
5. The git history tells the story of AI agents building software

## What to Watch For (QA)

- Setup flow errors or confusing prompts
- Boot script failures on fresh install
- Agent coordination issues (merge conflicts, stale data)
- Missing docs that a new user would need
- Any moment where you're confused about what to do next — that's a UX bug

## Connection to Going Public

This demo project:
- Proves SquidSquad works outside its own repo (#3 requirement)
- Becomes the terminal recording for the README (#2)
- Is a real product (web UI) not a throwaway demo
- Tests the setup flow, boot scripts, agent coordination end-to-end
- Any bugs found get filed back to the main SquidSquad repo
