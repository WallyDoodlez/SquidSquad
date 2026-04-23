# FEAT-PM-013 Test Plan — Setup Flow Improvements

## Test Cases

---

### Section A: Tarball Download (replaces 119 individual fetches)

---

### TC-1: Tarball fetch downloads and extracts all required files
- **Precondition**: Clean repo with no `.squidsquad/` directory. Network available. `gh` CLI authenticated. `npx squidsquad` invoked.
- **Steps**:
  1. Run `npx squidsquad` on a fresh repo
  2. Observe file fetch phase
  3. Compare files on disk to `references/installer-files.txt` manifest
- **Expected**: Single tarball downloaded via `gh api repos/{owner}/{repo}/tarball/{ref}`. All 119 files from the manifest are present on disk after extraction. No missing files. Fetch phase completes in under 10 seconds (vs. 60+ seconds for individual fetches).
- **Verification**: `diff <(sort references/installer-files.txt) <(find .squidsquad references -type f | sort)` shows no missing files from manifest. Network log shows 1 HTTP request for tarball (not 119).

### TC-2: Tarball extraction filters to relevant subtree only
- **Precondition**: Source repo contains files outside `references/` (e.g., `packages/`, `docs/`, `tests/`).
- **Steps**:
  1. Run `npx squidsquad` on a target repo
  2. List files written to disk
- **Expected**: Only files listed in `installer-files.txt` are extracted. No stray files from other parts of the SquidSquad source repo appear in the target repo.
- **Verification**: No files from `packages/`, `docs/`, or `tests/` directories of the source repo appear in the target.

### TC-3: Tarball fetch fails gracefully on network error
- **Precondition**: Network is unavailable or GitHub API returns 5xx.
- **Steps**:
  1. Run `npx squidsquad` with network disconnected (or mocked failure)
- **Expected**: CLI prints a clear error message: "Failed to download SquidSquad files. Check your network and try again." Exits with non-zero code. No partial files left on disk.
- **Verification**: Exit code != 0. `.squidsquad/` directory does not exist (or is empty).

### TC-4: Tarball fetch handles GitHub API rate limiting
- **Precondition**: GitHub API rate limit exhausted for the user's token.
- **Steps**:
  1. Run `npx squidsquad` when API rate limit is hit
- **Expected**: CLI detects 403/429 response, prints message about rate limiting, and suggests waiting or using a different token. No partial extraction.
- **Verification**: Error message mentions rate limit. No partial `.squidsquad/` directory.

---

### Section B: CLI Repo Scan Auto-Detection

---

### TC-5: Repo scan detects language, framework, tests, and git remote
- **Precondition**: Repo contains `package.json` (with `"test": "jest"`), `next.config.js`, `tsconfig.json`, `conftest.py`, `pyproject.toml`, and a git remote pointing to `github.com/user/myproject`.
- **Steps**:
  1. Run `npx squidsquad` (Phase 3 auto-detection)
  2. Read `.squidsquad/.repo-scan.json`
- **Expected**: JSON contains: languages detected (TypeScript, Python), frameworks (Next.js), test frameworks (Jest, pytest), package managers (npm, pip/poetry), git remote URL, project description from `gh repo view`.
- **Verification**: `python -c "import json; d=json.load(open('.squidsquad/.repo-scan.json')); assert 'TypeScript' in str(d); assert 'Next' in str(d); assert 'jest' in str(d) or 'Jest' in str(d)"`

### TC-6: Repo scan on empty repo produces valid but minimal output
- **Precondition**: Repo has only a `.git/` directory and possibly a README. No source files, no `package.json`, no remote description.
- **Steps**:
  1. Run `npx squidsquad` on the empty repo
  2. Read `.squidsquad/.repo-scan.json`
- **Expected**: Valid JSON with empty or minimal arrays/objects for languages, frameworks, test tools. No crash. Git remote present if configured, empty string if not. No false positive detections.
- **Verification**: `python -c "import json; d=json.load(open('.squidsquad/.repo-scan.json')); assert isinstance(d, dict)"` exits 0.

### TC-7: Repo scan detects monorepo markers
- **Precondition**: Repo contains `pnpm-workspace.yaml` and multiple `package.json` files in subdirectories (`packages/api/package.json`, `packages/web/package.json`).
- **Steps**:
  1. Run repo scan
  2. Read `.squidsquad/.repo-scan.json`
- **Expected**: Monorepo marker detected. Scan suggests multi-agent dev setup. Both frontend and backend markers identified from subdirectory analysis.
- **Verification**: Scan output includes monorepo detection flag or marker.

### TC-8: Repo scan handles conflicting test framework signals
- **Precondition**: Repo contains both `jest.config.js` and `vitest.config.ts`. `package.json` has `"test": "vitest"`.
- **Steps**:
  1. Run repo scan
  2. Read `.squidsquad/.repo-scan.json`
- **Expected**: Both test frameworks detected. The scan reports both — it does not guess which is "primary." The wizard will ask the user to confirm.
- **Verification**: Scan output includes both Jest and Vitest in test framework detections.

### TC-9: Repo scan infers test command from package.json scripts
- **Precondition**: `package.json` contains `"scripts": {"test": "jest --coverage"}`.
- **Steps**:
  1. Run repo scan
  2. Read `.squidsquad/.repo-scan.json`
- **Expected**: Test command inferred as `npm test` or `jest --coverage`. Scan output includes the inferred test command.
- **Verification**: Scan output contains a test command suggestion derived from `package.json`.

---

### Section C: Structured Scan Summary Shown to User

---

### TC-10: Wizard presents scan summary grouped by category
- **Precondition**: Repo scan completed with detections across languages, frameworks, test tools, CI/CD, and deploy targets. Claude session launched.
- **Steps**:
  1. Observe wizard output at start of interactive phase
- **Expected**: Wizard displays a structured summary like:
  ```
  Languages: TypeScript, Python
  Frameworks: Next.js, FastAPI
  Test tools: Jest, pytest
  CI/CD: GitHub Actions
  Deploy: Docker, Vercel
  ```
  All detected categories shown. User can correct any wrong detection before proceeding.
- **Verification**: Wizard output contains grouped detections. User is prompted to confirm or correct.

### TC-11: Scan summary handles zero detections gracefully
- **Precondition**: Empty repo with no detectable markers. Scan produced minimal output.
- **Steps**:
  1. Observe wizard output
- **Expected**: Wizard states "I didn't detect any specific frameworks or tools. Let's set things up from scratch." Proceeds to ask all questions without defaults.
- **Verification**: No crash. Wizard does not show empty categories — it skips them or shows a "nothing detected" message.

---

### Section D: CLI Model Routing Prompts

---

### TC-12: Provider discovery runs before Claude and results are available
- **Precondition**: User has API keys for OpenRouter and Anthropic configured. `model_router.py list-providers` returns both.
- **Steps**:
  1. Run `npx squidsquad` (Phase 3)
  2. Read provider discovery output (`.providers.json` or equivalent)
  3. Observe Claude wizard model routing question
- **Expected**: Discovery results saved to a JSON file before Claude launches. Wizard reads the file and presents: "Available providers: OpenRouter, Anthropic. Want to configure model routing?" No redundant discovery during Claude session.
- **Verification**: Provider JSON file exists before Claude session starts. Wizard reads it instead of running discovery commands.

### TC-13: No providers available — wizard skips model routing gracefully
- **Precondition**: No API keys configured. `model_router.py list-providers` returns empty list.
- **Steps**:
  1. Run `npx squidsquad`
  2. Observe wizard behavior for model routing question
- **Expected**: Wizard either skips model routing question entirely or presents it with a note: "No providers detected. You can configure this later." Default answer is "No."
- **Verification**: Wizard does not crash on empty provider list. Model routing defaults to disabled.

---

### Section E: --yes Mode (Accept All Defaults)

---

### TC-14: --yes mode accepts all defaults without prompting
- **Precondition**: Repo has detectable stack (Next.js + TypeScript, jest). Git remote configured.
- **Steps**:
  1. Run `npx squidsquad --yes`
  2. Observe output
  3. Check generated `.squidsquad/` tree
- **Expected**: No interactive prompts. CLI auto-detects everything, generates spec from defaults, scaffolds, commits, and prints post-setup instructions. Preset defaults to `software-dev` with `fullstack` variant. Loop interval defaults to 10 minutes. Model routing defaults to no. PR flow defaults to no.
- **Verification**: No user input required. `.squidsquad/config.md` exists with default values. `.squidsquad/.install-spec.json` exists.

### TC-15: --yes mode on empty repo uses sensible minimal defaults
- **Precondition**: Empty repo with no detectable stack.
- **Steps**:
  1. Run `npx squidsquad --yes`
  2. Check config.md
- **Expected**: Defaults applied: software-dev preset, fullstack variant, no test command (none detected), 10 min interval. No crash despite missing scan data.
- **Verification**: Config exists. No error output. All required fields have values.

### TC-16: --yes mode does not skip prerequisites
- **Precondition**: Python is not installed.
- **Steps**:
  1. Run `npx squidsquad --yes`
- **Expected**: CLI still checks prerequisites (Node, Python, gh, claude). Fails with clear error about missing Python. --yes does not bypass safety checks.
- **Verification**: Exit code != 0. Error message mentions Python requirement.

---

### Section F: .install-spec.json

---

### TC-17: Spec JSON committed to repo after setup
- **Precondition**: Full setup flow completed (interactive or --yes).
- **Steps**:
  1. Check `.squidsquad/.install-spec.json` exists
  2. Verify it is committed to git
  3. Read and parse its contents
- **Expected**: File exists, is valid JSON, and is committed. Contains all wizard answers: project name, preset, variant, agents, stack per agent, test commands, loop interval, model routing config, PR flow, branch names, architecture version, SquidSquad version.
- **Verification**: `git log --oneline -- .squidsquad/.install-spec.json` shows at least one commit. `python -c "import json; json.load(open('.squidsquad/.install-spec.json'))"` exits 0.

### TC-18: Spec JSON readable by upgrade flow
- **Precondition**: `.squidsquad/.install-spec.json` exists from a previous setup.
- **Steps**:
  1. Run `/squidsquad-upgrade` (or `wizard.py scaffold` with existing spec)
  2. Observe that spec is read and used
- **Expected**: Upgrade reads the existing spec, bumps the SquidSquad version field, and re-scaffolds from it. User is not re-asked questions that are already answered in the spec.
- **Verification**: Upgrade completes without re-asking interactive questions. New scaffold matches spec plus version bump.

### TC-19: Spec JSON round-trips correctly (serialize then deserialize produces same config)
- **Precondition**: Setup completed. `.install-spec.json` and `config.md` both exist.
- **Steps**:
  1. Read `.install-spec.json`
  2. Run `wizard.py scaffold .install-spec.json .` in a temp directory
  3. Compare generated `config.md` with original
- **Expected**: Generated config.md from spec matches the original config.md field-by-field. No data loss in the round-trip.
- **Verification**: Diff of config.md fields shows no differences.

---

### Section G: Scaffold Script Inside Claude Session

---

### TC-20: Scaffold runs as single script call inside Claude session
- **Precondition**: Claude wizard completed interactive phase. Spec JSON written. Claude session still active.
- **Steps**:
  1. Observe Claude calling `wizard.py scaffold spec.json .`
  2. Check output
- **Expected**: Single script call produces the full `.squidsquad/` tree: per-role directories, CLAUDE.md files (via compose.py), boot scripts, config.md, SOUL.md files. Claude reports success or failure interactively.
- **Verification**: All expected files exist. Claude prints a confirmation message.

### TC-21: Scaffold failure inside Claude produces interactive error message
- **Precondition**: `wizard.py scaffold` fails (e.g., permission denied on a directory, compose.py template missing).
- **Steps**:
  1. Trigger scaffold failure
  2. Observe Claude's response
- **Expected**: Claude catches the error, presents it clearly ("Scaffold failed: permission denied on .squidsquad/pm/"), and suggests remediation ("Check directory permissions and re-run /squidsquad-setup"). Does not leave a partial install without warning.
- **Verification**: Claude output includes the error description and suggested fix.

---

### Section H: Scaffold Idempotency

---

### TC-22: Re-running scaffold does not break existing setup
- **Precondition**: `.squidsquad/` already exists from a previous scaffold. SOUL.md files have been customized by agents (custom responsibilities added). working-state.md has active task context.
- **Steps**:
  1. Run `wizard.py scaffold spec.json .` again with the same spec
  2. Check SOUL.md, working-state.md, config.md
- **Expected**: CLAUDE.md files regenerated (these are templates, safe to overwrite). SOUL.md files preserved (user/agent customizations kept). working-state.md preserved. config.md regenerated from spec (or merged). Boot scripts regenerated. No duplicate directories created.
- **Verification**: `git diff` shows only expected CLAUDE.md regeneration. SOUL.md customizations intact. working-state.md unchanged.

### TC-23: Scaffold with modified spec produces correct delta
- **Precondition**: Previous setup had 1 dev agent (fullstack). New spec has 2 dev agents (fe + be).
- **Steps**:
  1. Run scaffold with the new spec
  2. Check directory structure
- **Expected**: New agent directories created (e.g., `.squidsquad/fe/`, `.squidsquad/be/`). Old `skill/` directory preserved if it was not in the new spec (scaffold does not delete directories it did not create). Config.md updated to reflect new agent roster.
- **Verification**: New agent directories exist with CLAUDE.md and SOUL.md. Config.md lists new agents.

### TC-24: Scaffold creates all required files for each role
- **Precondition**: Spec includes PM, QA, DM, and one dev agent (skill).
- **Steps**:
  1. Run scaffold
  2. List files per role directory
- **Expected**: Each role directory contains at minimum: `CLAUDE.md`, `SOUL.md`. PM additionally has `iterations/`, `planning/`, `qa-log.md`, `enhancements.md`. Boot scripts generated for each role. `config.md` at `.squidsquad/` root lists all agents.
- **Verification**: All expected files exist per role. No missing CLAUDE.md or SOUL.md.

---

### Section I: Existing Repo Detection

---

### TC-25: Existing .squidsquad/ directory detected — CLI aborts with upgrade message
- **Precondition**: Repo already has `.squidsquad/` directory from a previous install.
- **Steps**:
  1. Run `npx squidsquad`
- **Expected**: CLI detects existing install, prints "SquidSquad is already installed. Use /squidsquad-upgrade to update." Exits cleanly without modifying any files.
- **Verification**: Exit code 0 (informational exit). No files modified. Message mentions upgrade path.

### TC-26: Existing .install-spec.json detected — CLI offers resume
- **Precondition**: `.squidsquad/.install-spec.json` exists but scaffold was not completed (partial install, e.g., user closed terminal after Claude wrote spec but before scaffold ran).
- **Steps**:
  1. Run `npx squidsquad`
- **Expected**: CLI detects the spec file, offers "Previous setup was incomplete. Resume from saved config? (y/n)". If yes, runs scaffold from existing spec without re-asking questions.
- **Verification**: Scaffold completes from existing spec. No re-launch of Claude interactive session.

### TC-27: User customizations in config.md not overwritten by scaffold
- **Precondition**: User manually edited `config.md` to change loop interval from 10 to 15 minutes. `.install-spec.json` still has 10.
- **Steps**:
  1. Run scaffold from spec (e.g., during upgrade)
  2. Check config.md
- **Expected**: This depends on the locked decision from Phase 2 (spec is source of truth vs. config.md is source of truth). If spec is source of truth: config.md regenerated from spec (interval back to 10). If config.md is source of truth: spec should be updated first. Either way, the behavior must be documented and consistent.
- **Verification**: Config.md reflects the expected source of truth. No silent data loss.

---

### Section J: Windows Compatibility

---

### TC-28: Boot scripts generated correctly for Windows
- **Precondition**: Setup running on Windows 11. PowerShell available.
- **Steps**:
  1. Run full setup flow on Windows
  2. Check generated boot scripts
- **Expected**: Boot scripts use Windows-compatible paths (forward slashes or escaped backslashes). PowerShell scripts (.ps1) or batch files (.bat) generated alongside Unix shell scripts. File paths use `os.path.join` or equivalent (no hardcoded `/`).
- **Verification**: Boot scripts parse without syntax errors on Windows. `powershell -File .squidsquad/pm/boot.ps1 -WhatIf` (or equivalent dry-run) succeeds.

### TC-29: repo_scan.py works on Windows file system
- **Precondition**: Running on Windows. Repo contains mixed path separators.
- **Steps**:
  1. Run `python references/scripts/repo_scan.py --save`
  2. Read `.squidsquad/.repo-scan.json`
- **Expected**: Scan completes without path errors. File extension detection, marker file detection, and framework detection all work correctly. No `FileNotFoundError` from path separator issues.
- **Verification**: Script exits 0. JSON output is valid and contains detections.

### TC-30: wizard.py scaffold works on Windows
- **Precondition**: Running on Windows. Spec JSON uses forward slashes for paths.
- **Steps**:
  1. Run `wizard.py scaffold spec.json .` on Windows
  2. Check generated directory tree
- **Expected**: All directories and files created with correct Windows paths. No `PermissionError` or `OSError` from invalid path characters. Atomic file writes (tmp + rename) work on Windows (handles NTFS lock behavior).
- **Verification**: All expected files exist. No errors in script output.

### TC-31: Tarball extraction works on Windows
- **Precondition**: Running on Windows. Tarball downloaded from GitHub API.
- **Steps**:
  1. Run `npx squidsquad` on Windows
  2. Observe file extraction
- **Expected**: Tarball extracted correctly using Node.js tar library. File permissions not an issue (Windows ignores Unix perms). Long path names handled (Windows MAX_PATH considerations). No symlink issues.
- **Verification**: All 119 files extracted and present. No extraction errors.

---

### Section K: Post-Setup Instructions (#2006 Integration)

---

### TC-32: Post-setup instructions displayed after scaffold completes
- **Precondition**: Full setup completed successfully.
- **Steps**:
  1. Complete setup (interactive or --yes)
  2. Read final output
- **Expected**: Clear post-setup instructions printed, including:
  - How to boot agents (specific command per role)
  - How to check agent health
  - Where to find config (`config.md`)
  - Next steps (file a task, run `/squidsquad-setup` again for changes)
  - Link to documentation (if available)
- **Verification**: Output contains boot command, health check reference, and at least one "next step" suggestion.

### TC-33: Post-setup instructions include boot commands for all configured agents
- **Precondition**: Setup configured PM + skill + QA + DM.
- **Steps**:
  1. Read post-setup instructions
- **Expected**: Boot command shown for each configured agent. Commands reference correct boot script paths. If Windows, shows both PowerShell and bash variants.
- **Verification**: Each configured role has a boot command in the output.

---

### Section L: PR Flow Question (#2006 Integration)

---

### TC-34: Wizard asks PR Flow question during setup
- **Precondition**: Interactive setup flow. No --yes mode.
- **Steps**:
  1. Proceed through wizard to the optional/advanced questions
  2. Observe PR Flow question
- **Expected**: Wizard asks "Do you want to use PR flow? (y/N)" with default No. Explanation provided: "PR flow creates pull requests for dev work, requiring human review before merge."
- **Verification**: PR Flow question appears in the wizard flow. Default is No.

### TC-35: PR Flow answer persisted in spec and config
- **Precondition**: User answered "yes" to PR Flow question.
- **Steps**:
  1. Check `.install-spec.json`
  2. Check `config.md`
- **Expected**: `pr_flow: true` (or equivalent) in spec JSON. `PR Flow: yes` in config.md. Generated agent templates include PR monitoring instructions (Step 6b in PM template).
- **Verification**: Both files reflect PR Flow = yes. PM CLAUDE.md includes PR monitoring step.

### TC-36: PR Flow default (no) produces correct config
- **Precondition**: User accepted default No for PR Flow.
- **Steps**:
  1. Check config.md
- **Expected**: `PR Flow: no` in config.md. PM template skips Step 6b. No PR-related labels created (or labels exist but are unused).
- **Verification**: Config shows PR Flow: no. PM CLAUDE.md skips or guards PR monitoring step.

---

### Section M: Partial Failure Handling

---

### TC-37: Scaffold succeeds but label creation fails
- **Precondition**: `wizard.py scaffold` completed. `wizard.py ensure-labels` fails (e.g., gh auth lacks write permissions on the repo).
- **Steps**:
  1. Run setup flow where scaffold succeeds but labels fail
  2. Observe error handling
- **Expected**: Scaffold output preserved (not rolled back). Clear error message: "Labels could not be created. Run 'wizard.py ensure-labels' manually after fixing gh auth." Setup is usable — agents can boot but will encounter label errors on first tracker operations.
- **Verification**: `.squidsquad/` tree is complete. Error message about labels is clear. Re-running `wizard.py ensure-labels` alone succeeds after fixing auth.

### TC-38: Git commit after scaffold fails
- **Precondition**: Scaffold succeeded. `git commit` fails (e.g., pre-commit hook rejects, disk full).
- **Steps**:
  1. Trigger commit failure after scaffold
  2. Observe state
- **Expected**: All scaffolded files are on disk (unstaged or staged). Error message: "Files were scaffolded but the commit failed. Run 'git add .squidsquad && git commit' manually." No data loss.
- **Verification**: Files exist on disk. `git status` shows them as untracked or staged.

### TC-39: Claude session crashes after writing spec but before scaffold
- **Precondition**: Claude wrote `.install-spec.json` during interactive phase. Claude process terminated (crash, network, user kill).
- **Steps**:
  1. Simulate Claude crash after spec write
  2. Re-run `npx squidsquad`
- **Expected**: CLI detects `.install-spec.json` without a completed scaffold (missing config.md or incomplete directory tree). Offers to resume: "Previous setup was interrupted. Resume from saved answers? (y/n)". If yes, runs scaffold from spec.
- **Verification**: Resume completes successfully. No re-asking of interactive questions.

### TC-40: Network failure during git push (post-scaffold)
- **Precondition**: Scaffold and commit succeeded. `git push` fails due to network.
- **Steps**:
  1. Observe error handling
- **Expected**: Local commit preserved. Message: "Setup complete locally. Push failed — run 'git push' when network is available." Setup is fully functional locally.
- **Verification**: `git log --oneline -1` shows the setup commit. Files are committed.

### TC-41: Prerequisite check fails mid-flow (Python available at start, removed mid-install)
- **Precondition**: All prerequisites pass at start. Python becomes unavailable mid-flow (edge case, e.g., PATH change).
- **Steps**:
  1. Run `npx squidsquad`, then remove Python from PATH before scaffold
  2. Observe error
- **Expected**: Clear error when scaffold step tries to invoke Python. Message includes the specific command that failed and suggestion to verify Python installation.
- **Verification**: Error message references Python. No partial scaffold with missing files.

---

### Section N: Side Effect Regression Tests

---

### TC-42: Existing project CLAUDE.md not overwritten
- **Precondition**: Project has a root-level `CLAUDE.md` with custom user content. User runs SquidSquad setup.
- **Steps**:
  1. Run full setup flow
  2. Check root `CLAUDE.md`
- **Expected**: Root `CLAUDE.md` is unchanged. SquidSquad uses `.squidsquad/*/CLAUDE.md` for agent templates, not the root file. No merge, no overwrite, no rename of the user's file.
- **Verification**: `git diff CLAUDE.md` shows no changes (or only the SquidSquad auto-boot section appended, if that is the design).

### TC-43: Existing .claude/ directory not corrupted
- **Precondition**: User has an existing `.claude/` directory with custom commands.
- **Steps**:
  1. Run setup
  2. Check `.claude/` directory
- **Expected**: Only `.claude/commands/squidsquad-setup.md` added (or updated). No other files in `.claude/` modified or deleted.
- **Verification**: `git diff .claude/` shows only the squidsquad-setup.md addition.

### TC-44: Git history remains clean (single setup commit)
- **Precondition**: Fresh setup on a repo with existing commits.
- **Steps**:
  1. Run setup
  2. Check git log
- **Expected**: Setup produces 1-2 commits (file fetch + scaffold, or combined). No merge commits. No force-pushes. Commit messages are descriptive ("chore: add SquidSquad setup" or similar).
- **Verification**: `git log --oneline -5` shows clean commit history with descriptive messages.

### TC-45: ensure-labels is idempotent
- **Precondition**: Labels already exist on the GitHub repo from a previous setup.
- **Steps**:
  1. Run `wizard.py ensure-labels` again
- **Expected**: No duplicate labels created. Existing labels unchanged. No errors. Script exits 0.
- **Verification**: `gh label list` shows no duplicate labels. Exit code 0.

### TC-46: shared_fs.py init is idempotent
- **Precondition**: `~/.squidsquad/` directory already exists from a previous install on a different repo.
- **Steps**:
  1. Run `shared_fs.py init` again
- **Expected**: No error. Existing files in `~/.squidsquad/` preserved. Missing subdirectories created if needed. No data loss.
- **Verification**: Pre-existing files still present. Script exits 0.

### TC-47: Setup does not modify files outside .squidsquad/ and .claude/ (except CLAUDE.md auto-boot)
- **Precondition**: Repo has application code in `src/`, tests in `tests/`, etc.
- **Steps**:
  1. Run full setup flow
  2. Check git diff for files outside `.squidsquad/` and `.claude/`
- **Expected**: No application code modified. No test files modified. Only `.squidsquad/`, `.claude/commands/squidsquad-setup.md`, and potentially root `CLAUDE.md` (auto-boot section) touched.
- **Verification**: `git diff --name-only` shows only `.squidsquad/*`, `.claude/*`, and optionally `CLAUDE.md`.

---

### Section O: Upgrade Verification Tests

---

### TC-48: Upgrade from v1 config (flat format) to v2 (nested agent format)
- **Precondition**: Existing install with Architecture Version 1 config.md (flat format). No `.install-spec.json`.
- **Steps**:
  1. Run `/squidsquad-upgrade`
  2. Check config.md format
  3. Check agent behavior
- **Expected**: Config.md migrated to v2 format. Or: migration script generates a `.install-spec.json` from the v1 config, then re-scaffolds. Existing agent settings (loop interval, test commands, branch names) preserved in the new format.
- **Verification**: Config.md parses correctly by all agents. No agent errors on first cycle after upgrade.

### TC-49: Upgrade preserves SOUL.md customizations
- **Precondition**: Agent SOUL.md files have been customized (added responsibilities, scan criteria, etc.).
- **Steps**:
  1. Run upgrade
  2. Check SOUL.md files
- **Expected**: SOUL.md files unchanged. Only CLAUDE.md files (templates) regenerated. Working-state.md, iteration logs, and scan history preserved.
- **Verification**: `git diff .squidsquad/*/SOUL.md` shows no changes.

### TC-50: Upgrade preserves working-state.md (no active work lost)
- **Precondition**: Agent has an active task in working-state.md (`#2050`, status `in-progress`).
- **Steps**:
  1. Run upgrade
  2. Read working-state.md
- **Expected**: Working-state.md untouched. Agent resumes active task on next cycle after upgrade.
- **Verification**: `git diff .squidsquad/*/working-state.md` shows no changes.

### TC-51: Upgrade with .install-spec.json present uses it
- **Precondition**: `.install-spec.json` exists from original setup.
- **Steps**:
  1. Run upgrade
  2. Observe whether spec is read
- **Expected**: Upgrade reads spec, bumps SquidSquad version, re-scaffolds. No interactive questions. Config regenerated from updated spec.
- **Verification**: `.install-spec.json` version field updated. Config.md matches spec. CLAUDE.md files regenerated.

### TC-52: Non-upgraded install gracefully degrades (no breakage)
- **Precondition**: Install at version N. New SquidSquad version N+1 available but user has not upgraded.
- **Steps**:
  1. Boot agents on old version
  2. Observe behavior
- **Expected**: Agents continue working with their existing templates. No errors from missing new config fields (agents use defaults). No crashes from schema mismatches.
- **Verification**: Agents complete cycles without errors. No references to missing files or fields.

---

## Smoke Tests

- [ ] `npx squidsquad --help` exits 0 and shows usage information
- [ ] `npx squidsquad` on a fresh repo detects prerequisites (Node, Python, gh, claude)
- [ ] `npx squidsquad` on a repo with `.squidsquad/` aborts with upgrade message
- [ ] `python references/scripts/repo_scan.py --save` exits 0 and writes valid JSON
- [ ] `.squidsquad/.repo-scan.json` is valid JSON after scan
- [ ] `wizard.py scaffold` with a valid spec JSON exits 0
- [ ] `wizard.py ensure-labels` exits 0 (idempotent)
- [ ] `.squidsquad/.install-spec.json` is valid JSON after setup
- [ ] `config.md` contains all required fields after setup
- [ ] Each configured role has a `CLAUDE.md` file after scaffold
- [ ] Each configured role has a `SOUL.md` file after scaffold
- [ ] Boot scripts exist for each configured role after scaffold
- [ ] `python tests/run_tests.py` passes with setup flow changes in place
- [ ] Post-setup instructions are printed at the end of setup
- [ ] `--yes` mode completes without any user interaction

## Regression Risks

- **installer-files.txt drift**: If the manifest is not updated when new files are added to `references/`, tarball extraction will include the files but the manifest check will report them as unexpected. Watch for: new reference files not added to the manifest.
- **Tarball structure changes**: GitHub API tarball format includes a top-level directory with the commit SHA. If the extraction logic hardcodes path stripping, a GitHub API change could break extraction. Watch for: tarball path prefix assumptions.
- **repo_scan.py false positives on new frameworks**: As new framework config files are added to detection, existing repos may get new (incorrect) detections that change defaults. Watch for: scan results changing for repos that previously had stable detections.
- **spec JSON schema evolution**: As new setup questions are added (like PR Flow from #2006), the spec schema grows. Old spec files from previous installs may lack new fields. Scaffold must handle missing fields with defaults. Watch for: new spec fields without default values causing scaffold failures on upgrade.
- **config.md format coupling**: If config.md is generated from spec but agents parse config.md directly, any mismatch between the generator and parser breaks agents. Watch for: config.md generation changes that produce output agents cannot parse.
- **compose.py template sensitivity**: Scaffold calls compose.py to generate CLAUDE.md files. If compose.py expects templates in a specific order or format, changes to sub-skills or role manifests can silently produce wrong CLAUDE.md output. Watch for: compose.py changes that affect template rendering order or content.
- **wizard.py command surface growth**: Adding `generate-defaults`, `finish-install`, and `migrate-config` commands to wizard.py increases its complexity. If these share state or modify the same files, interaction bugs may emerge. Watch for: wizard.py commands that assume they are the only writer of a file.
- **Cross-platform path handling**: Windows paths with backslashes may be written into spec JSON or config.md. If these files are committed and read on Linux/macOS (or vice versa), path parsing breaks. Watch for: hardcoded path separators in generated files.
- **gh CLI version sensitivity**: Tarball download, label creation, and provider discovery all depend on `gh` CLI. Different `gh` versions may have different API behavior or output formats. Watch for: gh CLI version-specific behavior in new code paths.
- **Claude session token budget**: Moving scaffold inside the Claude session (Option B from Phase 2 Prep) means the wizard must have enough token budget remaining after interactive questions to run scaffold and present results. If the interactive phase consumes too many tokens, scaffold may fail due to context limits. Watch for: long interactive sessions that exhaust context before scaffold.
- **Partial .install-spec.json detection**: If the CLI detects `.install-spec.json` but not `.squidsquad/config.md`, it offers resume. But if the spec was written by a different SquidSquad version, the spec format may be incompatible. Watch for: spec version mismatches during resume.
- **Label taxonomy expansion**: If new labels are added to the taxonomy (e.g., for new roles), `ensure-labels` must handle the delta. If it only creates labels from a hardcoded list, new labels from an upgraded spec may be missed. Watch for: label creation not reading from spec or manifest.
