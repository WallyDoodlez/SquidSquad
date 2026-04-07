# FEAT-269 Context — npx Installer Bootstrapper

## Summary

Thin Node.js CLI package `squidsquad` on npm. Users run `npx squidsquad` to bootstrap SquidSquad onto their project. It checks prerequisites, installs the skill, and prints next-step instructions. The skill's own setup flow handles everything else.

## Decisions (Locked)

1. **Package name**: `squidsquad` — confirmed available on npmjs.com
2. **Scope**: Thin bootstrapper only — prerequisite checks + `claude install-skill` + print instructions
3. **Post-install handoff**: Print instructions telling user to start a new Claude session or run `/clear`, then invoke `/squidsquad-setup`. Do NOT auto-launch Claude.
4. **Flags**: None — one command, one purpose. No `--version`, `--upgrade`, `--help` beyond basic usage.
5. **Package location**: `packages/cli/` (standard monorepo convention)
6. **Publishing**: Manual `npm publish` for v1. Automated CI publishing is a future enhancement.
7. **Dependencies**: Zero npm runtime dependencies — Node.js built-ins only (`child_process`, `fs`, `path`)
8. **Node.js version**: 18+ (via `engines` field + runtime check)
9. **Prerequisites checked**: Python 3.8+, gh CLI (authenticated), Claude CLI, git repo
10. **Already installed**: Detect `.squidsquad/` dir → print message and exit cleanly (not an error)

## Acceptance Criteria

1. Running `npx squidsquad` in a git repo with all prerequisites installs the SquidSquad skill
2. Missing Python → clear error message with install link, exit 1
3. Missing gh CLI → clear error message with install link, exit 1
4. gh not authenticated → clear error message ("run gh auth login"), exit 1
5. Missing Claude CLI → clear error message with install link, exit 1
6. Not a git repo → clear error message, exit 1
7. Already has `.squidsquad/` → informational message, exit 0
8. Node.js < 18 → clear error message, exit 1
9. After successful install, prints instructions: "Start a new Claude session or run /clear, then run /squidsquad-setup"
10. Package has zero npm runtime dependencies
11. `packages/cli/package.json` has correct `bin` field, `engines` field, and `name: squidsquad`
12. Works on Windows (PowerShell + Git Bash), macOS, and Linux

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
