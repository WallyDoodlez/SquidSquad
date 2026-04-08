# squidsquad

Bootstrap [SquidSquad](https://github.com/WallyDoodlez/SquidSquad) onto your project.

SquidSquad is an autonomous AI dev team that coordinates through markdown, not meetings. It spins up Claude Code agents — one per dev role you define, plus PM and QA — that work on your codebase in parallel.

## Usage

```bash
npx squidsquad
```

Run this from inside a git repository. The bootstrapper will:

1. Verify prerequisites (Node.js 18+, Python 3.8+, GitHub CLI, Claude Code CLI)
2. Install the SquidSquad skill for Claude Code
3. Print next-step instructions

After running, start a new Claude Code session and invoke `/squidsquad-setup` to configure your project.

## Prerequisites

- [Node.js 18+](https://nodejs.org/)
- [Python 3.8+](https://www.python.org/downloads/)
- [GitHub CLI (`gh`)](https://cli.github.com/) — authenticated
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code/overview)
- A git repository

## What It Does

The bootstrapper is intentionally thin. It checks your environment, installs the SquidSquad skill, and hands off to the skill's interactive setup wizard. The wizard handles everything else: project config, agent roles, boot scripts, GitHub Issues labels, and more.

## License

[AGPL-3.0](https://github.com/WallyDoodlez/SquidSquad/blob/main/LICENSE)
