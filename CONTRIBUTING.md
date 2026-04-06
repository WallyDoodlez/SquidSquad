# Contributing to SquidSquad

Thanks for your interest in contributing to SquidSquad! This guide covers how to report bugs, propose features, and submit pull requests.

## Reporting Bugs

Found something broken? [Open an issue](https://github.com/WallyDoodlez/SquidSquad/issues/new) with:

- **Title**: Short description of the problem
- **Steps to reproduce**: What you did, what happened, what you expected
- **Environment**: OS, Claude Code version, SquidSquad version (from `.squidsquad/config.md`)
- **Logs**: Any `[🦑]` step marker output or error messages

## Proposing Features

Have an idea? [Open an issue](https://github.com/WallyDoodlez/SquidSquad/issues/new) describing:

- **What** you want SquidSquad to do
- **Why** it would be valuable (what problem it solves, who benefits)
- **How** you imagine it working (optional, but helpful)

Feature requests are triaged by the maintainer. Approved features enter the backlog and get picked up through the normal SquidSquad workflow.

## Submitting Pull Requests

1. Fork the repo and create a branch from `main`
2. Make your changes
3. Run the test suite: `python tests/run_tests.py`
4. Commit with a clear message describing what changed and why
5. Open a PR against `main`

### What makes a good PR

- **Focused**: One fix or feature per PR
- **Tested**: Existing tests pass, new behavior has tests where practical
- **Documented**: Update README.md, CHANGELOG.md, or SKILL.md if your change affects user-facing behavior

### Code style

- See [SKILL.md](./SKILL.md) for the full skill specification and architecture
- Commit messages follow the pattern: `role: description` (e.g. `skill: fix bug in tracker.py`)
- Python scripts live in `references/scripts/` and use subprocess list form (no `shell=True`)

## Development Setup

1. Clone the repo
2. Ensure you have Python 3.x, `gh` CLI (authenticated), and Claude Code CLI installed
3. Run tests: `python tests/run_tests.py`
4. Read [SKILL.md](./SKILL.md) to understand the architecture

## What lives in this repo

This repo contains the **core SquidSquad skill**: the coordination framework, agent templates, scripts, and shared infrastructure. Sub-skills (third-party extensions) live in their own repositories and are not contributed here.

## Questions?

Open an issue or check the existing [issues](https://github.com/WallyDoodlez/SquidSquad/issues) for context.
