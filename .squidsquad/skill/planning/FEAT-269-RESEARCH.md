# FEAT-269 Research — npx Installer Bootstrapper

## Summary

SquidSquad currently requires users to run `claude install-skill` from the SquidSquad repo, which registers SKILL.md as a Claude Code skill. Once installed, the user invokes the skill (via `/squidsquad-setup`) and the agent walks through a 9-step interactive setup: gathering project details, creating the `.squidsquad/` folder structure, generating config/templates/boot scripts, seeding GitHub Issues labels, and committing. The entire setup flow is driven by the Claude agent reading SKILL.md instructions — it is not a standalone script.

The proposed `npx squidsquad` bootstrapper would be a thin Node.js CLI package living in the repo (e.g. `packages/cli/`) that automates the prerequisite checks and skill installation, then hands off to the existing skill-driven setup flow. The bootstrapper does NOT replicate the 9-step setup — it only ensures the environment is ready and triggers the skill. This is a clean separation: the npm package handles machine-level prerequisites (Python 3, gh CLI, Claude CLI, git repo), while the skill handles project-level configuration (agents, config.md, boot scripts, labels).

The main complexity lies in cross-platform prerequisite detection (Windows/macOS/Linux), the mechanics of programmatically triggering `claude install-skill`, and deciding how to handle edge cases like existing installations. The package itself is straightforward — a single `bin` entry in package.json pointing to a CLI script, with zero npm dependencies (using only Node.js built-ins like `child_process` and `fs`).

## Impact Analysis

- **Files created**:
  - `packages/cli/package.json` — npm package manifest with `bin` field
  - `packages/cli/index.js` (or `cli.js`) — main CLI entry point
  - `packages/cli/README.md` — npm package README (shown on npmjs.com)
  - `packages/cli/.npmignore` or `files` field in package.json — controls what gets published
- **Files touched**:
  - `.gitignore` — may need `node_modules/` entry (already absent, would be needed if dev dependencies are added)
  - `SKILL.md` — Setup Instructions should mention `npx squidsquad` as the recommended install path
  - `README.md` — update installation instructions to lead with `npx squidsquad`
- **Behavior changes**: No changes to existing setup flow. The npx command is a new entry point that converges to the same skill-driven setup.
- **Dependencies**: Zero runtime npm dependencies (Node.js built-ins only). The bootstrapper requires Node.js 18+ (for stable `child_process.execSync` and ES module support), Python 3 (checked at runtime), gh CLI (checked at runtime), Claude CLI (checked at runtime), and git (checked at runtime).

## Side Effects

- **Risk 1**: npm package name `squidsquad` may already be taken on npmjs.com — Severity: H — Mitigation: Check `npm view squidsquad` before committing to the name. If taken, consider `@squidsquad/cli` or `create-squidsquad`.

- **Risk 2**: `claude install-skill` behavior may change across Claude CLI versions — Severity: M — Mitigation: The bootstrapper should detect Claude CLI version and fail gracefully with a message if the command is unavailable. Pin to documented CLI behavior only.

- **Risk 3**: Windows path handling in Node.js `child_process` — Severity: M — Mitigation: Use `path.join()` and avoid hardcoded `/` separators. Test with both PowerShell and Git Bash on Windows. The boot script templates already handle Windows (`.ps1` variants exist).

- **Risk 4**: Python detection across platforms — Severity: M — Mitigation: Check both `python3` and `python` (Windows often only has `python`). Verify version >= 3.8 by parsing `python --version` output.

- **Risk 5**: Network dependency during npx execution — Severity: L — Mitigation: npx fetches the package from npm registry, which requires internet. This is standard npx behavior and not unique to this tool. Document it.

## Edge Cases

- **No git repo**: Detect with `git rev-parse --show-toplevel`. Print clear error: "Run this command from inside a git repository." Exit code 1.

- **No Python 3**: Try `python3 --version`, then `python --version`. If neither works or version < 3.8, print: "Python 3.8+ is required. Install from python.org." Exit code 1.

- **No gh CLI**: Try `gh --version`. If missing, print: "GitHub CLI (gh) is required. Install from https://cli.github.com/." Exit code 1. Note: gh is not strictly required for SquidSquad to function (tracker works without it for basic operation), but the setup flow creates labels via `gh label create`, so it is a hard prerequisite for setup.

- **gh not authenticated**: Try `gh auth status`. If exit code != 0, print: "GitHub CLI is not authenticated. Run `gh auth login` first." Exit code 1.

- **No Claude CLI**: Try `claude --version`. If missing, print: "Claude Code CLI is required. Install from https://docs.anthropic.com/claude-code." Exit code 1.

- **Already has `.squidsquad/`**: Detect the directory. Print: "This project already has SquidSquad installed. To upgrade, run `/squidsquad-upgrade` from a Claude session." Exit code 0 (not an error).

- **Running from wrong directory (no git root)**: Same as "no git repo" case — `git rev-parse --show-toplevel` fails.

- **Node.js version too old**: The `engines` field in package.json can specify `>=18`. npx will warn but not block. Add a runtime check at the top of the CLI script.

- **Skill already installed**: `claude install-skill` may be idempotent (re-installing overwrites). The bootstrapper should proceed — reinstalling is harmless.

- **Offline / npm registry unreachable**: Standard npx failure. No special handling needed.

## Integration Risks

- **`claude install-skill` mechanics**: This command clones/fetches the SquidSquad repo and registers SKILL.md as a skill. The npx bootstrapper needs the SquidSquad repo URL (hardcoded or configurable). If the user has already cloned SquidSquad locally, `claude install-skill` can point to the local path instead. The bootstrapper must decide: always use the remote URL (simpler, always latest) vs. detect local clone (faster, works offline). Recommendation: always use remote URL `github.com/WallyDoodlez/SquidSquad`.

- **Handoff to skill setup flow**: After `claude install-skill` completes, the user needs to invoke the setup skill. Two options: (a) the bootstrapper prints instructions ("Now run `/squidsquad-setup` in Claude"), or (b) the bootstrapper programmatically launches `claude` with the setup command. Option (b) is better UX but more complex — it requires spawning Claude interactively and passing the right arguments. The boot scripts show the pattern: `claude --dangerously-skip-permissions --append-system-prompt "..." "start the loop"`. A similar approach could work: `claude "run /squidsquad-setup"`.

- **SKILL.md version coupling**: The npx package has its own version (in its package.json), while SquidSquad has its version in SKILL.md frontmatter. These can diverge. The bootstrapper version should track the SquidSquad version loosely — it is a thin wrapper, so its version is less critical. But the npm package should be re-published when the install flow changes.

- **Compose.py and config.py dependency**: The setup flow uses Python scripts (`compose.py`, `config.py`, `tracker.py`) extensively. These scripts live in `references/scripts/` inside the SquidSquad repo, which gets cloned into the target project via `claude install-skill`. The bootstrapper itself does NOT call these scripts — the skill setup flow does. But the bootstrapper must ensure Python is available because the skill will need it moments later.

- **Boot script dependency on `references/` directory**: Boot scripts (`start-role.sh/.ps1`) call `python references/scripts/config.py` at runtime. This means the `references/` directory from the SquidSquad skill repo must be accessible at the project root. This is how skills work — `claude install-skill` makes the skill's files available. The bootstrapper should verify this after installation.

## Upgrade & Migration

- **New config values**: none — the npx bootstrapper does not modify config.md
- **New files**: `packages/cli/package.json`, `packages/cli/index.js`, `packages/cli/README.md`, `packages/cli/.npmignore`
- **Template changes**: none
- **Upgrade steps**: N/A — the npx bootstrapper is a new artifact. Existing installs are unaffected. Users who installed via `claude install-skill` directly continue to work. The npx path is an alternative entry point, not a replacement.
- **Graceful degradation**: Users without Node.js/npm can still use `claude install-skill` directly. The npx bootstrapper is additive.

## Open Questions

- **Q1**: What is the exact npm package name? — **Why**: If `squidsquad` is taken on npmjs.com, the entire UX ("npx squidsquad") changes. Alternatives: `@squidsquad/cli`, `create-squidsquad`, `squidsquad-cli`. The scoped name `@squidsquad/cli` requires an npm org. `create-squidsquad` follows the create-* convention but implies project scaffolding (which this is not — it installs a skill, not a project template).

- **Q2**: Should the bootstrapper launch Claude with `/squidsquad-setup` automatically, or just print instructions? — **Why**: Auto-launch is better UX but adds complexity (interactive process spawning, terminal control). Print-instructions is simpler but adds a manual step. The boot scripts show that spawning `claude` from a script is a solved pattern in this repo.

- **Q3**: Should the bootstrapper support `--version` / `--upgrade` flags for SquidSquad management? — **Why**: Scope creep risk. The bootstrapper's job is "get SquidSquad installed." Version management is the skill's job (`/squidsquad-upgrade`). Adding flags makes the CLI thicker than intended.

- **Q4**: Where in the repo should the package live — `packages/cli/`, `npm/`, or root-level? — **Why**: Affects monorepo tooling, publishing workflow, and whether the root needs a `package.json` or `workspaces` config. `packages/cli/` is the cleanest (standard monorepo convention) but adds a directory level. Root-level `package.json` would conflict with the repo's identity as a Python/markdown project.

- **Q5**: How does `claude install-skill` actually resolve the repo? — **Why**: The bootstrapper needs to pass the correct repo identifier. If it uses `claude install-skill github.com/WallyDoodlez/SquidSquad`, that needs to be the exact format the CLI expects. This should be tested against the actual Claude CLI before implementation.

- **Q6**: Should the npm package be published to npmjs.com as part of CI, or manually? — **Why**: Automated publishing (via GitHub Actions on tag) is more reliable but requires npm token secrets and CI setup. Manual publishing is simpler for v1 but error-prone.

## Recommendation

**Feasible with caveats.** The core bootstrapper is simple — prerequisite checks + `claude install-skill` + handoff. The main risks are: (1) npm name availability, (2) the exact mechanics of `claude install-skill` from a script context, and (3) cross-platform Python detection. All are solvable but need verification before implementation begins. Recommend a spike to confirm `claude install-skill <repo-url>` works reliably from a Node.js `child_process.execSync` call on all three platforms, and to check npm name availability, before writing the full implementation.
