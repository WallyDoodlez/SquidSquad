# New Project Setup — SquidSquad Web UI

Hey Claude, I want to start a new project and use SquidSquad to help me build it.

## The Project

I'm building a web-based dashboard for SquidSquad — it lets you see agent status, file bugs/features, browse the vault, and view iteration logs. Think of it as a control panel for SquidSquad.

## What I Need You To Do

1. Create a new GitHub repo called `squidsquad-web` under my account (WallyDoodlez). Public repo.

2. Install the SquidSquad skill from `github.com/WallyDoodlez/SquidSquad`. Follow the installation docs in that repo's SKILL.md — it explains how to set up SquidSquad on a new project.

3. Run through the setup flow. Here's what I want:
   - Project name: squidsquad-web
   - One dev agent: `skill` (full-stack)
   - Default aliases
   - 30 minute cycles
   - No E2E tests yet

4. Seed these as initial features to build:
   - **Dashboard**: real-time agent status view (role, active/stalled/idle, current task, last cycle)
   - **Issue viewer**: list GitHub Issues with labels, status, priority
   - **File bug/feature form**: submit bugs or features that PM picks up
   - **Vault browser**: browse vault notes, view frontmatter, follow wikilinks
   - **Iteration log timeline**: view what happened per agent over time

5. For tech stack, I'm thinking modern and lightweight. Suggest something that makes sense for this kind of dashboard and ask me to confirm before committing.

6. Boot the agents and let them start building.

## Important

- Follow the SquidSquad docs in the repo, don't make up how it works
- If anything in the setup is confusing or breaks, note it — those are bugs I need to fix in SquidSquad itself
- This is also a test of the SquidSquad setup experience, so be honest about friction points
