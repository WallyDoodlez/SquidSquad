# Contributing to SquidSquad

Thanks for your interest in contributing to SquidSquad! This guide covers how to report bugs, propose features, and submit pull requests.

## Reporting Bugs

Found something broken? [Open an issue report](https://github.com/WallyDoodlez/SquidSquad/issues/new?template=issue-report.yml) — the template will guide you through the right format (version, OS, steps to reproduce, expected vs actual behavior).

**Running SquidSquad locally?** You can also report issues from inside a Claude Code session using the `/squidsquad-issue` command — it automatically attaches sanitized config and diagnostic context.

## Proposing Features

Have an idea? [Open a task request](https://github.com/WallyDoodlez/SquidSquad/issues/new?template=task-request.yml) — describe the problem it solves, your proposed solution, and any alternatives you considered.

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
3. Install dev dependencies: `pip install -r requirements-dev.txt`
4. Run tests: `python tests/run_tests.py static` (safe, no side effects)
5. Read [SKILL.md](./SKILL.md) to understand the architecture

> **Note**: `python tests/run_tests.py` without arguments also runs integration tests that interact with GitHub Issues. Use `static` for local development.

## What lives in this repo

This repo contains the **core SquidSquad skill**: the coordination framework, agent templates, sub-skills, scripts, and shared infrastructure. Sub-skills live in `references/sub-skills/` — see the [Sub-Skill Guide](docs/sub-skill-guide.md) for how to create and contribute them.

## Questions?

Open an issue or check the existing [issues](https://github.com/WallyDoodlez/SquidSquad/issues) for context.
