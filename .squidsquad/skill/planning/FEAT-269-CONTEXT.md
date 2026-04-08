# FEAT-269 Context — npx Installer Bootstrapper

## Summary

Thin Node.js CLI package `squidsquad` on npm. Users run `npx squidsquad` to bootstrap SquidSquad onto their project. It checks prerequisites, installs the skill, and prints next-step instructions. The skill's own setup flow handles everything else.

## Decisions (Locked)

1. **Package name**: `squidsquad` — confirmed available on npmjs.com
2. **Scope**: Thin bootstrapper — prerequisite checks + fetch SKILL.md & slash command + prompt to launch setup
3. **Post-install handoff**: Prompt "Launch SquidSquad installation now? (Y/n)". Yes → exec `claude /squidsquad-setup`. No → print instructions to run `/squidsquad-setup` manually. (REVISED: human overrode original "do not auto-launch" decision on 2026-04-08)
4. **Flags**: None — one command, one purpose. No `--version`, `--upgrade`, `--help` beyond basic usage.
5. **Package location**: `packages/cli/` (standard monorepo convention)
6. **Publishing**: Manual `npm publish` for v1. Automated CI publishing is a future enhancement.
7. **Dependencies**: Zero npm runtime dependencies — Node.js built-ins only (`child_process`, `fs`, `path`)
8. **Node.js version**: 18+ (via `engines` field + runtime check)
9. **Prerequisites checked**: Python 3.8+, gh CLI (authenticated), Claude CLI, git repo
10. **Already installed**: Detect `.squidsquad/` dir → print message and exit cleanly (not an error)
11. **No full repo clone**: npx fetches only SKILL.md (→ project root) and squidsquad-setup.md (→ `.claude/commands/`). No clone to `~/.claude/skills/` or anywhere else. (ADDED 2026-04-08)
12. **Setup fetches remotely**: `/squidsquad-setup` flow must fetch `references/` (scripts, templates, agent instructions) from GitHub on the fly during the wizard. gh CLI is already a prereq. (ADDED 2026-04-08)

## Acceptance Criteria

1. Running `npx squidsquad` in a git repo with all prerequisites fetches SKILL.md and the slash command into the project
2. Missing Python → clear error message with install link, exit 1
3. Missing gh CLI → clear error message with install link, exit 1
4. gh not authenticated → clear error message ("run gh auth login"), exit 1
5. Missing Claude CLI → clear error message with install link, exit 1
6. Not a git repo → clear error message, exit 1
7. Already has `.squidsquad/` → informational message, exit 0
8. Node.js < 18 → clear error message, exit 1
9. After fetching files, prompts "Launch SquidSquad installation now? (Y/n)" — Yes launches `claude /squidsquad-setup`, No prints manual instructions
10. Package has zero npm runtime dependencies
11. `packages/cli/package.json` has correct `bin` field, `engines` field, and `name: squidsquad`
12. Works on Windows (PowerShell + Git Bash), macOS, and Linux
13. SKILL.md is placed at the project root, squidsquad-setup.md at `.claude/commands/`
14. No full repo clone — only the two seed files are fetched by npx
15. `/squidsquad-setup` fetches `references/` from GitHub during the wizard (separate rework)

## Dev Discretion

- Exact wording of error messages and success output
- Whether to use ESM or CJS for the CLI script
- Python detection strategy (try `python3` then `python`, parse version)
- How to invoke `claude install-skill` (exact CLI args, repo URL format)

## Side Effect Mitigations

- Cross-platform Python detection: check both `python3` and `python`, verify version >= 3.8
- Windows path handling: use `path.join()`, no hardcoded `/`
- `claude install-skill` format: test exact invocation before implementation

## Files to Create

- `packages/cli/package.json`
- `packages/cli/index.js` (or `cli.js`)
- `packages/cli/README.md` (npm listing)
- `packages/cli/.npmignore` (or use `files` field)

## Files to Update

- `README.md` — add `npx squidsquad` as primary install path
- `SKILL.md` — mention npx as recommended install method
- `.gitignore` — add `node_modules/` if not present
