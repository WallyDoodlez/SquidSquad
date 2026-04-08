# FEAT-269 Test Plan — npx Installer Bootstrapper

## Test Cases

### Prerequisites

| TC | Description | Steps | Expected | Type |
|----|-------------|-------|----------|------|
| TC-01 | Node.js version check rejects < 18 | 1. Set up environment with Node.js 16. 2. Run `npx squidsquad`. | Prints error message stating Node.js 18+ is required. Exits with code 1. | unit |
| TC-02 | Node.js 18+ passes runtime check | 1. Ensure Node.js 18+ is installed. 2. Run `npx squidsquad` (other prereqs may fail — that is fine). | No Node.js version error is printed. Process continues to next prerequisite check. | unit |
| TC-03 | Missing Python detected | 1. Ensure neither `python3` nor `python` is on PATH. 2. Run `npx squidsquad`. | Prints error mentioning Python 3.8+ is required with install link (python.org). Exits with code 1. | unit |
| TC-04 | Python version < 3.8 detected | 1. Ensure only Python 3.7 is on PATH. 2. Run `npx squidsquad`. | Prints error stating Python 3.8+ is required. Exits with code 1. | unit |
| TC-05 | Python 3.8+ passes check (python3 binary) | 1. Ensure `python3 --version` returns 3.8+. 2. Run `npx squidsquad`. | No Python error. Process continues to next prerequisite check. | unit |
| TC-06 | Python 3.8+ passes check (python binary fallback) | 1. Ensure `python3` is absent but `python --version` returns 3.8+. 2. Run `npx squidsquad`. | No Python error. Process continues to next prerequisite check. | unit |
| TC-07 | Missing gh CLI detected | 1. Ensure `gh` is not on PATH. 2. Run `npx squidsquad`. | Prints error mentioning gh CLI is required with install link (cli.github.com). Exits with code 1. | unit |
| TC-08 | gh CLI not authenticated | 1. Ensure `gh` is installed but `gh auth status` exits non-zero. 2. Run `npx squidsquad`. | Prints error: "Run `gh auth login` first" (or equivalent). Exits with code 1. | unit |
| TC-09 | Missing Claude CLI detected | 1. Ensure `claude` is not on PATH. 2. Run `npx squidsquad`. | Prints error mentioning Claude Code CLI is required with install link (docs.anthropic.com). Exits with code 1. | unit |
| TC-10 | Not a git repo | 1. Create a temp directory (not a git repo). 2. Run `npx squidsquad` from that directory. | Prints error: "Run this command from inside a git repository" (or equivalent). Exits with code 1. | unit |

### Happy Path

| TC | Description | Steps | Expected | Type |
|----|-------------|-------|----------|------|
| TC-11 | Full install succeeds with all prerequisites | 1. Ensure Node.js 18+, Python 3.8+, gh (authenticated), Claude CLI, and git repo are available. 2. Ensure `.squidsquad/` does not exist. 3. Run `npx squidsquad`. | All prerequisite checks pass. `claude install-skill` executes successfully. Prints post-install instructions containing: "Start a new Claude session or run /clear, then run /squidsquad-setup". Exits with code 0. | integration |
| TC-12 | Post-install instructions are printed | 1. Complete a successful install (TC-11 conditions). 2. Capture stdout. | Output contains the exact handoff instructions: mentions starting a new Claude session or running `/clear`, and mentions `/squidsquad-setup`. | integration |
| TC-13 | claude install-skill is invoked with correct repo URL | 1. Complete a successful install (TC-11 conditions). 2. Observe or mock the `claude install-skill` invocation. | The command passes the SquidSquad repo URL (`github.com/WallyDoodlez/SquidSquad` or equivalent format the Claude CLI expects). | integration |

### Error Cases

| TC | Description | Steps | Expected | Type |
|----|-------------|-------|----------|------|
| TC-14 | claude install-skill fails | 1. All prereqs present. 2. Mock or cause `claude install-skill` to exit non-zero. 3. Run `npx squidsquad`. | Prints a clear error explaining that skill installation failed. Does NOT print the success/handoff instructions. Exits with code 1. | integration |
| TC-15 | Each prerequisite error includes an actionable message | 1. For each missing prerequisite (Python, gh, Claude CLI, git repo, gh auth, Node version), trigger the error. 2. Capture the error output. | Each error message includes: (a) what is missing, (b) how to fix it (install link or command to run). No generic "something went wrong" messages. | smoke |
| TC-16 | Multiple missing prerequisites — first failure exits | 1. Remove Python and gh from PATH. 2. Run `npx squidsquad`. | Prints an error for the first missing prerequisite encountered and exits with code 1. Does not continue checking remaining prerequisites after a failure (or alternatively, reports all missing prerequisites — either approach is acceptable as long as exit code is 1). | unit |

### Cross-Platform

| TC | Description | Steps | Expected | Type |
|----|-------------|-------|----------|------|
| TC-17 | Windows PowerShell — happy path | 1. On Windows, open PowerShell. 2. Ensure all prereqs (Node 18+, Python via `python` binary, gh, claude, git repo). 3. Run `npx squidsquad`. | All checks pass. `claude install-skill` runs. Instructions printed. Exit code 0. | integration |
| TC-18 | Windows Git Bash — happy path | 1. On Windows, open Git Bash. 2. Ensure all prereqs. 3. Run `npx squidsquad`. | All checks pass. `claude install-skill` runs. Instructions printed. Exit code 0. | integration |
| TC-19 | macOS — happy path | 1. On macOS terminal. 2. Ensure all prereqs (Python via `python3`). 3. Run `npx squidsquad`. | All checks pass. `claude install-skill` runs. Instructions printed. Exit code 0. | integration |
| TC-20 | Linux — happy path | 1. On Linux terminal. 2. Ensure all prereqs (Python via `python3`). 3. Run `npx squidsquad`. | All checks pass. `claude install-skill` runs. Instructions printed. Exit code 0. | integration |
| TC-21 | Windows Python detection uses `python` not `python3` | 1. On Windows where only `python` is on PATH (common Windows config). 2. Run `npx squidsquad`. | Python check succeeds by falling back to `python` binary. No Python error. | unit |
| TC-22 | No hardcoded path separators | 1. Review `packages/cli/index.js` (or equivalent). 2. Search for hardcoded `/` in file path construction. | All file path operations use `path.join()` or equivalent. No hardcoded forward-slash path separators. | unit |

### Edge Cases

| TC | Description | Steps | Expected | Type |
|----|-------------|-------|----------|------|
| TC-23 | Already installed — .squidsquad/ exists | 1. Ensure `.squidsquad/` directory exists in the git repo. 2. Run `npx squidsquad`. | Prints informational message (e.g., "SquidSquad is already installed"). Does NOT run `claude install-skill`. Exits with code 0 (not an error). | smoke |
| TC-24 | Skill already installed but no .squidsquad/ | 1. Ensure `claude install-skill` was previously run but `.squidsquad/` does not exist. 2. Run `npx squidsquad`. | Proceeds with full install (reinstalling is harmless). `claude install-skill` runs. Instructions printed. Exit code 0. | integration |
| TC-25 | Run from subdirectory of a git repo | 1. Navigate to a subdirectory within a git repo. 2. Run `npx squidsquad`. | `git rev-parse --show-toplevel` succeeds. Install proceeds normally. `.squidsquad/` detection uses the repo root, not the current subdirectory. | integration |
| TC-26 | package.json has zero runtime dependencies | 1. Read `packages/cli/package.json`. 2. Check `dependencies` field. | The `dependencies` field is either absent or an empty object `{}`. No runtime npm dependencies. `devDependencies` may exist (acceptable). | unit |
| TC-27 | package.json has correct bin field | 1. Read `packages/cli/package.json`. 2. Check `bin` field. | The `bin` field maps `squidsquad` to the CLI entry point (e.g., `"bin": { "squidsquad": "./index.js" }` or equivalent). | unit |
| TC-28 | package.json has correct engines field | 1. Read `packages/cli/package.json`. 2. Check `engines` field. | The `engines` field specifies `"node": ">=18"` (or equivalent constraint). | unit |
| TC-29 | package.json has correct name field | 1. Read `packages/cli/package.json`. 2. Check `name` field. | The `name` field is `"squidsquad"`. | unit |
| TC-30 | Offline / npm registry unreachable | 1. Disconnect from network. 2. Run `npx squidsquad`. | npx itself fails with its standard network error. No special handling needed from our code — this is npx behavior. | smoke |

## Coverage Matrix

| Acceptance Criteria | Test Cases |
|---------------------|------------|
| AC-1: `npx squidsquad` in a git repo with all prerequisites installs the skill | TC-11, TC-12, TC-13 |
| AC-2: Missing Python — clear error with install link, exit 1 | TC-03, TC-04, TC-15 |
| AC-3: Missing gh CLI — clear error with install link, exit 1 | TC-07, TC-15 |
| AC-4: gh not authenticated — clear error ("run gh auth login"), exit 1 | TC-08, TC-15 |
| AC-5: Missing Claude CLI — clear error with install link, exit 1 | TC-09, TC-15 |
| AC-6: Not a git repo — clear error, exit 1 | TC-10, TC-25 |
| AC-7: Already has `.squidsquad/` — informational message, exit 0 | TC-23 |
| AC-8: Node.js < 18 — clear error, exit 1 | TC-01, TC-02 |
| AC-9: After successful install, prints handoff instructions | TC-12 |
| AC-10: Zero npm runtime dependencies | TC-26 |
| AC-11: package.json has correct bin, engines, and name fields | TC-27, TC-28, TC-29 |
| AC-12: Works on Windows (PowerShell + Git Bash), macOS, Linux | TC-17, TC-18, TC-19, TC-20, TC-21, TC-22 |

## Smoke Tests (for dev agent to run before marking Pending Test)

1. **Package structure**: Verify `packages/cli/package.json` exists with `name: "squidsquad"`, `bin` field pointing to the CLI entry, `engines.node >= 18`, and no `dependencies` (or empty object).
2. **Shebang and executable**: Verify the CLI entry point has a `#!/usr/bin/env node` shebang line and is executable.
3. **Not a git repo error**: Run `node packages/cli/index.js` from a temp non-git directory. Confirm it prints a git repo error and exits 1.
4. **Already installed detection**: Create a `.squidsquad/` directory in a git repo, run the CLI. Confirm it prints an informational message and exits 0.
5. **Missing prerequisite message quality**: Temporarily rename `gh` (or use a PATH that excludes it), run the CLI in a git repo. Confirm the error message names `gh`, includes an install link, and exits 1.
6. **Happy path dry run**: In a git repo with all prerequisites, run the CLI. Confirm all checks pass, `claude install-skill` is invoked, and the handoff instructions ("Start a new Claude session or run /clear, then run /squidsquad-setup") are printed.
7. **No hardcoded path separators**: Search `packages/cli/` source files for path construction. Confirm `path.join()` is used and no hardcoded `/` appears in path building logic.
