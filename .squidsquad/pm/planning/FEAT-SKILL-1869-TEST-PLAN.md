# FEAT-SKILL-1869 Test Plan — 3-Branch Architecture + State Bus

## Test Cases

### TC-1: Fresh install creates all 3 branches (happy path)
- **Precondition**: Clean repo with no `.squidsquad-state/` directory. No `stag` or `squid-squad` branches on local or remote. `git` >= 2.15. Setup CLI not yet run.
- **Steps**: Run the setup CLI (squidsquad-setup). Accept default branch names (`stag`, `squid-squad`). Let boot scripts run.
- **Expected**: Three branches exist: `main` (unchanged), `stag` (working branch, checked out in agent clones), `squid-squad` (orphan branch with no shared history with main). `squid-squad` contains the initial directory structure (`.squidsquad/{role}/iterations/`, `.squidsquad/{role}/planning/`, `.squidsquad/vault/`, etc.). `.squidsquad-state/` worktree directory exists at repo root, checked out to `squid-squad`. All three branches are pushed to remote.
- **Verification**: `git branch -a | grep -E "stag|squid-squad"` shows both branches locally and on remote. `git log --oneline squid-squad | head -1` shows the initial commit. `git merge-base main squid-squad` fails (no common ancestor — orphan). `ls .squidsquad-state/.squidsquad/vault/` shows vault directories.

### TC-2: Agent cycle reads/writes state via worktree (happy path)
- **Precondition**: 3-branch setup complete. State worktree at `.squidsquad-state/` exists. Agent (skill or PM) is running.
- **Steps**: Trigger one full Ralph Loop cycle. Observe where iteration logs, working-state.md, and scan-history.md are written.
- **Expected**: Iteration log written to `.squidsquad-state/.squidsquad/{role}/iterations/iter-N.md`. Working-state.md written to `.squidsquad-state/.squidsquad/{role}/working-state.md`. State files committed and pushed to `squid-squad` branch (not `main` or `stag`). Local `.gitignore`d runtime files (current-state, .health, .pid) still written to `.squidsquad/{role}/` in the main worktree.
- **Verification**: `git log -1 --oneline squid-squad` shows the state commit. `git log -1 --oneline stag` does NOT show a state commit. `cat .squidsquad-state/.squidsquad/{role}/working-state.md` returns current working state. `cat .squidsquad/{role}/current-state` returns runtime state (local, not on any branch).

### TC-3: PR targets working branch (happy path)
- **Precondition**: 3-branch setup complete. Config.md contains `Working Branch: stag`. Agent has completed a code change on a feature branch.
- **Steps**: Agent runs `git_ops.py` to create a PR for the code change.
- **Expected**: PR base branch is `stag`, not `main`. `gh pr view --json baseRefName` returns `stag`. Feature branch was branched from `stag`.
- **Verification**: `gh pr list --json baseRefName,headRefName | jq '.[0].baseRefName'` returns `"stag"`. `git log --oneline stag..HEAD` shows the feature commits.

### TC-4: Main is never touched by agents (happy path)
- **Precondition**: 3-branch setup complete. Multiple agent cycles have run. Code changes and state changes have been committed.
- **Steps**: Compare `main` branch HEAD before and after 5+ agent cycles.
- **Expected**: `main` branch HEAD SHA is unchanged. No agent commits appear on main. `git log main` shows only pre-setup commits.
- **Verification**: Record `git rev-parse main` before test. After cycles, `git rev-parse main` returns the same SHA. `git log main --since="1 hour ago" --oneline` returns empty.

### TC-5: State branch auto-created on first boot (edge case)
- **Precondition**: Repo has `.squidsquad/config.md` with `State Branch: squid-squad` configured, but the `squid-squad` branch does NOT exist locally or on remote (simulating first boot of a new clone or fresh install). No `.squidsquad-state/` worktree.
- **Steps**: Run a boot script (`start-{role}.sh` or `start-{role}.ps1`).
- **Expected**: Boot script detects missing state branch. Creates orphan branch `squid-squad` with initial directory structure. Pushes to remote. Creates worktree at `.squidsquad-state/`. Agent cycle starts normally and writes state to the worktree.
- **Verification**: `git branch -a | grep squid-squad` shows the branch. `ls .squidsquad-state/.squidsquad/` shows role directories. Agent's first iteration log appears in `.squidsquad-state/.squidsquad/{role}/iterations/`.

### TC-6: Worktree missing — boot self-heals (edge case)
- **Precondition**: State branch `squid-squad` exists on remote. `.squidsquad-state/` directory has been deleted (e.g., user ran `rm -rf .squidsquad-state/`). `git worktree list` does NOT show the state worktree.
- **Steps**: Run a boot script.
- **Expected**: Boot script detects that `squid-squad` branch exists but worktree is missing. Runs `git worktree add .squidsquad-state squid-squad`. Worktree is recreated. Agent cycle proceeds normally.
- **Verification**: `git worktree list` shows `.squidsquad-state` mapped to `squid-squad`. `ls .squidsquad-state/.squidsquad/` returns the expected state directory structure. Agent writes state successfully on next cycle.

### TC-7: Concurrent pushes to state branch (edge case)
- **Precondition**: Two agents (PM and skill) running in separate clones. Both have state worktrees pointing to `squid-squad`. Both are mid-cycle and about to push state.
- **Steps**: Agent A (PM) commits and pushes `.squidsquad/pm/working-state.md` to state branch. While push is in-flight or just completed, Agent B (skill) attempts to push `.squidsquad/skill/iterations/iter-N.md`.
- **Expected**: Agent B's push is rejected (non-fast-forward). Agent B runs `git pull --rebase` in the state worktree, which succeeds without conflicts (different directories). Agent B retries push successfully. Both agents' state files are present on `squid-squad`.
- **Verification**: `git log squid-squad --oneline -5` shows both agents' commits. `cat .squidsquad-state/.squidsquad/pm/working-state.md` and `cat .squidsquad-state/.squidsquad/skill/iterations/iter-N.md` both return valid content. No merge conflict markers in any files.

### TC-8: Network down — graceful degradation (edge case)
- **Precondition**: 3-branch setup complete. Agent is mid-cycle. Network is disconnected (simulate with `git remote set-url origin https://invalid.example.com/repo.git` or firewall rule).
- **Steps**: Agent completes a cycle and attempts to commit and push state.
- **Expected**: Agent commits state locally to the state worktree (commit succeeds — local operation). Push fails with a network error. Agent logs the failure but does NOT crash. Cycle completes. On next cycle with network restored, `git pull --rebase` syncs and push succeeds. No state is lost — local commits are preserved.
- **Verification**: `git -C .squidsquad-state log --oneline -3` shows the local (unpushed) commits. Agent's current-state file shows `idle|` (cycle completed). After network restore, `git -C .squidsquad-state push` succeeds. `git log origin/squid-squad --oneline -3` shows the previously-local commits.

### TC-9: Custom branch names (edge case)
- **Precondition**: Fresh repo. No existing SquidSquad branches.
- **Steps**: Run setup CLI. When prompted, enter custom names: working branch = `dev-working`, state branch = `ss-state`. Complete setup.
- **Expected**: Config.md contains `Working Branch: dev-working` and `State Branch: ss-state`. Branches `dev-working` and `ss-state` are created (not `stag` or `squid-squad`). Worktree is created for `ss-state`. All agent scripts read branch names from config and use them correctly. PRs target `dev-working`. State commits go to `ss-state`.
- **Verification**: `git branch -a | grep dev-working` and `git branch -a | grep ss-state` both match. `grep "Working Branch" .squidsquad/config.md` returns `dev-working`. `grep "State Branch" .squidsquad/config.md` returns `ss-state`. `git worktree list` shows worktree on `ss-state`. After one agent cycle, `git log ss-state --oneline -1` shows a state commit.

### TC-10: Migration — existing install moves state to orphan branch (migration)
- **Precondition**: Existing SquidSquad install with state files on `main` (iterations/, planning/, working-state.md, scan-history.md, vault/, bugs/, features/, qa-log.md, diagnostics/, .backlog-cache, boot-attempts.log all committed to main).
- **Steps**: Run the migration script.
- **Expected**: Orphan branch `squid-squad` (or configured name) is created. All state files are populated on the orphan branch from main's current content. State files are removed from `main` via a cleanup commit. `.gitignore` on main is updated to prevent state files from reappearing. Worktree is created at `.squidsquad-state/`. Config.md is updated with `## Git Branches` section.
- **Verification**: `git show squid-squad:.squidsquad/vault/BRIEFING.md` returns the BRIEFING content. `git show main:.squidsquad/vault/BRIEFING.md` fails (file removed from main). `git log main --oneline -1` shows the cleanup commit. `git log squid-squad --oneline -1` shows the migration commit. `grep "Git Branches" .squidsquad/config.md` matches.

### TC-11: Migration — vault history preserved (migration)
- **Precondition**: Existing install with vault files (BRIEFING.md, galaxy/*.md, areas/*.md, projects/*.md) having multiple commits of history on main.
- **Steps**: Run the migration script. Inspect vault content on the state branch.
- **Expected**: All vault files are present on the state branch with their latest content intact. File contents on `squid-squad` match the pre-migration content byte-for-byte. Historical commits remain accessible on `main` via `git log main -- .squidsquad/vault/`. The state branch starts with a fresh initial commit (no shared history with main — expected per orphan branch design).
- **Verification**: For each vault file: `diff <(git show main~1:.squidsquad/vault/BRIEFING.md) <(git show squid-squad:.squidsquad/vault/BRIEFING.md)` returns no diff (content matches pre-migration snapshot). `git log main -- .squidsquad/vault/BRIEFING.md` shows the historical commits (audit trail preserved on main).

### TC-12: Migration — in-flight work not lost (migration)
- **Precondition**: Existing install with an agent mid-task. `working-state.md` contains an active task (`Status: in-progress`). Uncommitted local changes exist in `.squidsquad/{role}/iterations/`.
- **Steps**: Stop agents with `.stop` sentinels. Run the migration script. Remove `.stop` sentinels. Restart agents.
- **Expected**: `working-state.md` is migrated to state branch with the in-progress task intact. On restart, agent reads working-state from the state worktree and resumes the in-progress task. No iteration logs are lost — uncommitted logs are included in the migration. Planning artifacts in progress are migrated to state branch.
- **Verification**: `cat .squidsquad-state/.squidsquad/{role}/working-state.md` shows the in-progress task. Agent's first post-migration cycle prints "Resuming [task]" in Step 1c. `ls .squidsquad-state/.squidsquad/{role}/iterations/` shows all iteration files (count matches pre-migration count).

### TC-13: Side effect — health check still works (regression)
- **Precondition**: 3-branch setup complete. Agent is running. `.squidsquad/{role}/.health`, `.squidsquad/{role}/.pid`, `.squidsquad/{role}/current-state` exist as local `.gitignore`d files.
- **Steps**: Run `python references/scripts/health_check.py`.
- **Expected**: Health check reads from local `.gitignore`d files in `.squidsquad/{role}/`, NOT from the state worktree. Reports agent health correctly (healthy/stalled/unknown). No errors about missing files or wrong paths. Output format unchanged from pre-migration behavior.
- **Verification**: `python references/scripts/health_check.py` exits 0 with per-agent status. `python references/scripts/health_check.py --json` returns valid JSON with agent statuses. No stderr warnings about state branch or worktree paths.

### TC-14: Side effect — watchdog still works (regression)
- **Precondition**: 3-branch setup complete. Agent is running. Watchdog is configured.
- **Steps**: Run `python references/scripts/watchdog.py` (or let it run its 30-second check interval).
- **Expected**: Watchdog reads `.health`, `.pid`, `context-pressure` from local `.gitignore`d paths. Does NOT attempt to read from the state worktree. Correctly detects agent liveness. No changes needed to watchdog.py.
- **Verification**: Watchdog output shows agent status without errors. `grep -c "squidsquad-state" references/scripts/watchdog.py` returns 0 (watchdog has no references to state worktree).

### TC-15: Side effect — tracker.py unaffected (regression)
- **Precondition**: 3-branch setup complete. `gh` CLI authenticated.
- **Steps**: Run `python references/scripts/tracker.py list-tasks skill --status approved` and `python references/scripts/tracker.py check-gh`.
- **Expected**: tracker.py uses GitHub Issues API exclusively. No git branch operations. Output identical to pre-migration behavior. All tracker commands work without modification.
- **Verification**: `python references/scripts/tracker.py check-gh` exits 0. `python references/scripts/tracker.py list-tasks skill --status approved` returns valid JSON. `grep -c "squid-squad\|squidsquad-state\|stag" references/scripts/tracker.py` returns 0 (no branch references in tracker).

### TC-16: Performance — state worktree read speed (performance)
- **Precondition**: 3-branch setup complete. State worktree populated with typical state files (20+ iteration logs, working-state, vault with 20+ notes).
- **Steps**: Time reading 5 state files from the worktree path (`cat .squidsquad-state/.squidsquad/{role}/working-state.md` etc.). Compare to baseline of reading 5 files from main checkout.
- **Expected**: Worktree reads are at filesystem speed (~70ms for 5 files, per research benchmarks). No meaningful difference from reading files in the main checkout directory. Certainly under 200ms for 5 files.
- **Verification**: `time for f in working-state.md iterations/iter-1.md iterations/iter-2.md scan-history.md ../vault/BRIEFING.md; do cat ".squidsquad-state/.squidsquad/{role}/$f" > /dev/null; done` reports real time under 200ms. Compare with equivalent read from main checkout path — delta < 50ms.

### TC-17: Squash — state branch history management (performance)
- **Precondition**: State branch has accumulated 500+ commits (simulated or real).
- **Steps**: Trigger the periodic squash mechanism (however implemented — commit count threshold, manual script, etc.).
- **Expected**: State branch is squashed to a single commit (or small number of commits). All current state files are preserved with correct content. Remote is force-pushed (state branch only — main and working branch untouched). Worktrees in all clones can recover via `git pull --rebase` or worktree re-creation.
- **Verification**: `git rev-list --count squid-squad` returns a small number (1 or close to it). `cat .squidsquad-state/.squidsquad/{role}/working-state.md` returns valid content (not empty or corrupted). `git log main --oneline -1` SHA unchanged (main not affected). `git log stag --oneline -1` SHA unchanged (working branch not affected).

### TC-18: Comprehension — fresh agent reads state from correct path (comprehension)
- **Precondition**: 3-branch setup complete. Agent templates updated with new state worktree paths.
- **Steps**: Spawn a fresh agent (new context, no prior state) with the updated CLAUDE.md template. Ask: "Where do you read working-state.md from?" and "Where do you write iteration logs?"
- **Expected**: Agent answers with the state worktree path (`.squidsquad-state/.squidsquad/{role}/working-state.md` or equivalent). Agent does NOT reference the old path on main (`.squidsquad/{role}/working-state.md`). Agent correctly distinguishes between state files (worktree) and runtime files (local `.gitignore`d).
- **Verification**: Fresh agent's responses reference the state worktree path. Agent can successfully read its working state and write an iteration log on the first cycle without errors.

### TC-19: Comprehension — fresh agent creates PR to working branch (comprehension)
- **Precondition**: 3-branch setup complete. Agent templates updated with working branch config.
- **Steps**: Spawn a fresh agent. Ask: "What branch do you target PRs to?" and "What branch do you commit code changes to?"
- **Expected**: Agent answers `stag` (or the configured working branch name). Agent does NOT say `main`. Agent understands that main is untouched by SquidSquad.
- **Verification**: Agent's responses reference the working branch from config.md. If agent creates a PR, `gh pr view --json baseRefName` confirms the working branch.

### TC-20: Comprehension — fresh agent understands branch separation (comprehension)
- **Precondition**: 3-branch setup complete. Agent templates updated.
- **Steps**: Spawn a fresh agent. Ask: "What are the 3 branches and what is each used for?" and "What happens if the state worktree is missing when you boot?"
- **Expected**: Agent correctly describes: main (project code, never touched), working branch (code changes, PR target), state branch (orphan, state bus for iterations/planning/vault/working-state). Agent describes self-healing behavior: detect missing worktree, run `git worktree add`, continue normally.
- **Verification**: Agent's description matches the architecture. No confusion about which files go where.

### TC-21: Config.md — Git Branches section present (happy path)
- **Precondition**: Setup CLI has been run (fresh or migration).
- **Steps**: Read `.squidsquad/config.md`.
- **Expected**: File contains a `## Git Branches` section with `Working Branch: stag` (or custom name) and `State Branch: squid-squad` (or custom name). Section is well-formed and parseable by `config.py`.
- **Verification**: `python references/scripts/config.py get working-branch` returns the configured branch name. `python references/scripts/config.py get state-branch` returns the configured state branch name.

### TC-22: git_ops.py — branch-aware pull/push (happy path)
- **Precondition**: 3-branch setup complete. Agent on a feature branch based on the working branch.
- **Steps**: Run `python references/scripts/git_ops.py pull`. Run `python references/scripts/git_ops.py commit-push {role} "test commit"`.
- **Expected**: `pull` fetches from the working branch (not main). `commit-push` pushes code changes to the feature branch. State commits (via a separate state-commit command) go to the state worktree and push to the state branch. No operations target main.
- **Verification**: `git log --oneline -1` shows the commit on the feature branch. `git log main --oneline -1` is unchanged. If state was committed, `git -C .squidsquad-state log --oneline -1` shows the state commit.

### TC-23: compose.py reads vault from state worktree (happy path)
- **Precondition**: 3-branch setup complete. Vault content exists on state branch (BRIEFING.md, galaxy notes). State worktree is present.
- **Steps**: Run `python references/scripts/compose.py deploy-all` (or equivalent compose command that reads BRIEFING.md).
- **Expected**: compose.py reads BRIEFING.md from `.squidsquad-state/.squidsquad/vault/BRIEFING.md` (state worktree path). Template composition succeeds. No errors about missing vault files.
- **Verification**: compose.py exits 0. Composed templates reference vault content correctly. `grep -c "BRIEFING" .squidsquad/{role}/CLAUDE.md` confirms vault content was injected (if applicable).

### TC-24: Boot script creates worktree on first run (happy path)
- **Precondition**: State branch exists on remote but no local worktree. Fresh clone with no `.squidsquad-state/` directory.
- **Steps**: Run boot script (`start-{role}.sh`).
- **Expected**: Boot script checks for `.squidsquad-state/`. Detects it is missing. Runs `git worktree add .squidsquad-state squid-squad` (or configured branch name). Worktree is created. Agent boots normally.
- **Verification**: `git worktree list` shows the state worktree. `.squidsquad-state/.squidsquad/` directory exists with expected structure. Agent's first cycle completes without state-related errors.

### TC-25: Setup CLI prompts for branch names (happy path)
- **Precondition**: Fresh repo. Setup CLI ready to run.
- **Steps**: Run setup CLI. Observe prompts. Press Enter for defaults on both branch name prompts.
- **Expected**: CLI prompts "Working branch name? (default: stag):" and "State branch name? (default: squid-squad):". Accepting defaults produces `stag` and `squid-squad`. Values are written to config.md.
- **Verification**: Config.md contains `Working Branch: stag` and `State Branch: squid-squad`. Branches exist with those names.

### TC-26: Vault writes go to state branch (happy path)
- **Precondition**: 3-branch setup complete. Agent runs vault-remember or vault-create during a cycle.
- **Steps**: Agent creates a new galaxy note (e.g., `galaxy/decision-test-branch.md`) via vault-create.
- **Expected**: The note is written to `.squidsquad-state/.squidsquad/vault/galaxy/decision-test-branch.md`. Committed and pushed to the state branch. NOT present on main or working branch.
- **Verification**: `git show squid-squad:.squidsquad/vault/galaxy/decision-test-branch.md` returns the note content. `git show stag:.squidsquad/vault/galaxy/decision-test-branch.md` fails (not on working branch). `git show main:.squidsquad/vault/galaxy/decision-test-branch.md` fails (not on main).

## Smoke Tests

- [ ] `git branch -a` shows all 3 branches after setup
- [ ] `git worktree list` shows the state worktree
- [ ] `.squidsquad-state/` directory exists and contains `.squidsquad/`
- [ ] `config.md` has `## Git Branches` section with both branch names
- [ ] Agent cycle completes without errors on the 3-branch setup
- [ ] `git log main --oneline -1` SHA does not change after agent cycles
- [ ] `health_check.py` runs without errors
- [ ] `watchdog.py` runs without errors
- [ ] `tracker.py check-gh` runs without errors
- [ ] PR created by agent targets the working branch
- [ ] State files are absent from main after migration
- [ ] Vault content is readable from the state worktree

## Regression Risks

- **Path hardcoding**: Any script or template that hardcodes `.squidsquad/{role}/iterations/` without accounting for the state worktree will break. Grep all references to state file paths in templates and scripts.
- **git_ops.py pull targeting wrong branch**: If pull still defaults to main instead of the working branch, agents will miss code changes on the working branch.
- **compose.py vault path**: If compose.py still reads vault from the main checkout instead of the state worktree, template composition will fail when vault files are removed from main.
- **Migration leaves orphan files**: If the cleanup commit on main misses some state files, they will accumulate again on main.
- **Worktree path in .gitignore**: If `.squidsquad-state/` is not in `.gitignore` on the working branch, it could accidentally be committed.
- **Force push during squash**: The periodic squash force-pushes the state branch. If other agents have unpushed local state commits, they will need to `git pull --rebase` which could fail if the rebase base has been rewritten. Agents must handle this gracefully (re-create worktree if rebase fails).
- **Windows path handling**: `git worktree add` on Windows uses native paths. Ensure all scripts use forward slashes or `pathlib` for cross-platform compatibility.
- **Shallow clone interaction**: If an agent clone uses `--depth 1`, worktree creation for the state branch may fail. Boot scripts should fetch the state branch before creating the worktree.
