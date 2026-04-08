# squidsquad

Bootstrap [SquidSquad](https://github.com/WallyDoodlez/SquidSquad) onto your project.

SquidSquad is an autonomous AI dev team that coordinates through markdown, not meetings. It spins up Claude Code agents — one per dev role you define, plus PM and QA — that work on your codebase in parallel.

## Usage

```bash
npx squidsquad
```

Run this from inside a git repository. The bootstrapper will:

1. Verify prerequisites (Node.js 18+, Python 3.8+, GitHub CLI, Claude Code CLI)
2. Fetch `SKILL.md` and the `/squidsquad-setup` command into your project
3. Prompt to launch the setup wizard immediately

## Prerequisites

- [Node.js 18+](https://nodejs.org/)
- [Python 3.8+](https://www.python.org/downloads/)
- [GitHub CLI (`gh`)](https://cli.github.com/) — authenticated
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code/overview)
- A git repository

## What It Does

The bootstrapper is intentionally thin. It checks your environment, seeds two files into your project (`SKILL.md` at the root and a `/squidsquad-setup` slash command), then offers to launch Claude Code to run the interactive setup wizard. The wizard handles everything else: project config, agent roles, boot scripts, GitHub Issues labels, and more.

## License

[AGPL-3.0](https://github.com/WallyDoodlez/SquidSquad/blob/main/LICENSE)
