# FEAT-SKILL-1389 Test Plan — Self-Hosted Forge Backend (Forgejo)

## Test Cases

### TC-1: GitHub backend wraps gh identically (happy path)
- **Precondition**: `forge_adapter.py` exists. `config.md` has `Provider: github`. `gh` CLI is authenticated.
- **Steps**: Call every `ForgeBackend` method via the GitHub adapter: `list_issues`, `create_issue`, `edit_labels`, `view_issue`, `close_issue`, `add_comment`, `create_pr`, `merge_pr`, `view_pr`, `create_label`, `list_labels`.
- **Expected**: Each method produces the same `gh` CLI invocation (same flags, same argument order) as the current direct calls in `tracker.py` and `git_ops.py`. Return values match the current JSON shapes.
- **Verification**: Add `--dry-run` or logging mode to the adapter. Diff the generated `gh` commands against the 20+ calls currently hardcoded in `tracker.py` (lines with `gh issue`, `gh pr`, `gh label`). Zero differences.

### TC-2: Forgejo backend creates an issue via HTTP (happy path)
- **Precondition**: Forgejo instance running at `http://localhost:3000`. API token valid. Repo exists with issues enabled.
- **Steps**: Call `create_issue(title="Test Issue", body="Body text", labels=["bug"])` through the Forgejo backend.
- **Expected**: `POST /api/v1/repos/{owner}/{repo}/issues` is sent with correct JSON payload. Response returns `id` (integer) and `number`. Issue appears in Forgejo web UI.
- **Verification**: `curl -s -H "Authorization: token $TOKEN" http://localhost:3000/api/v1/repos/{owner}/{repo}/issues | python -m json.tool` shows the created issue.

### TC-3: Forgejo backend list issues with label and state filters (happy path)
- **Precondition**: Forgejo instance with 3+ issues: some open, some closed, some with `squidsquad` label.
- **Steps**: Call `list_issues(labels=["squidsquad"], state="open", limit=10)` through the Forgejo backend.
- **Expected**: Only open issues with the `squidsquad` label are returned. Closed issues and unlabeled issues are excluded. Response shape matches the GitHub adapter's return format (normalized fields).
- **Verification**: Compare result count against Forgejo web UI filtered view. Verify JSON keys match the GitHub backend's output keys (no `node_id` vs `id` leaks).

### TC-4: Forgejo backend edit labels (two-step atomic) (happy path)
- **Precondition**: Forgejo issue exists with label `status:open`.
- **Steps**: Call `edit_labels(number=N, add=["status:in-progress"], remove=["status:open"])`.
- **Expected**: Two sequential API calls: `DELETE /api/v1/repos/.../issues/N/labels/{label_id}` then `POST /api/v1/repos/.../issues/N/labels`. Both succeed. Issue ends with only `status:in-progress`.
- **Verification**: `python references/scripts/tracker.py get-labels N` returns only the expected labels.

### TC-5: Forgejo backend PR create, view, merge (happy path)
- **Precondition**: Forgejo repo with a feature branch containing at least one commit ahead of `main`.
- **Steps**: Call `create_pr(title="Test PR", body="Body", head="feature", base="main", draft=True)`, then `view_pr(number=N, fields=["state"])`, then `merge_pr(number=N, strategy="squash")`.
- **Expected**: PR created with draft=true. View returns `state: "open"`. Merge succeeds. After merge, view returns `state: "closed"` (Forgejo uses `closed` for merged PRs in some versions).
- **Verification**: `curl http://localhost:3000/api/v1/repos/{owner}/{repo}/pulls/N` shows merged state.

### TC-6: tracker.py refactor — all existing operations work through adapter
- **Precondition**: `forge_adapter.py` present. `config.md` set to `Provider: github`.
- **Steps**: Run the full tracker.py test suite: `check-gh`, `list-tasks skill --status approved`, `create-issue`, `create-task`, `transition N open in-progress --role skill-lead`, `comment N --role pm-lead --message "test"`, `get-labels N`, `get-state N`, `close-issue N`, `list-all-open`, `work-queue skill`, `add-labels N "squidsquad,type:task"`.
- **Expected**: Every command produces identical output and side effects as before the refactor. Exit codes unchanged.
- **Verification**: Capture `tracker.py` output for each command before and after the refactor (on same test data). `diff` the outputs. Zero meaningful differences (timestamps excluded).

### TC-7: git_ops.py refactor — PR operations work through adapter
- **Precondition**: `forge_adapter.py` present. `config.md` set to `Provider: github`. A feature branch exists.
- **Steps**: Run `python references/scripts/git_ops.py pr-create "Test" "Body"`, `python references/scripts/git_ops.py pr-merge N`.
- **Expected**: PR created and merged identically to current behavior. `pr_create()` and `pr_merge()` function signatures unchanged.
- **Verification**: Check GitHub web UI for the created/merged PR. Confirm `git_ops.py` public function signatures match pre-refactor (inspect with `grep "^def " references/scripts/git_ops.py`).

### TC-8: Setup wizard — forge backend selection
- **Precondition**: Clean project, no `config.md` Forge Backend section. Docker available.
- **Steps**: Run the setup wizard. Select option 2 (Local Forgejo). Wizard deploys Forgejo via Docker, creates admin account, creates repo, generates API token, initializes git remote.
- **Expected**: Forgejo container running on port 3000. Admin account created. Repo accessible. API token stored in `~/.squidsquad/secrets`. `config.md` updated with `Provider: forgejo-local`, `Endpoint: http://localhost:3000`, correct `Repository` value, `Auth Method: api-token`.
- **Verification**: `docker ps | grep forgejo` shows running container. `curl http://localhost:3000/api/v1/version` returns Forgejo version JSON. `cat ~/.squidsquad/secrets` contains the token. `python references/scripts/config.py get forge-provider` returns `forgejo-local`.

### TC-9: Setup wizard — GitHub selection (default)
- **Precondition**: Clean project, `gh` CLI authenticated.
- **Steps**: Run the setup wizard. Select option 1 (GitHub, default).
- **Expected**: No Docker operations. `config.md` updated with `Provider: github`, `Endpoint: https://api.github.com`, `Auth Method: gh-cli`. No token stored in `~/.squidsquad/secrets`.
- **Verification**: `python references/scripts/config.py get forge-provider` returns `github`. No `~/.squidsquad/secrets` file created (or file exists but has no Forgejo token).

### TC-10: Setup wizard — external Forgejo
- **Precondition**: Existing Forgejo instance at `https://forge.example.com` with a repo and API token.
- **Steps**: Run the setup wizard. Select option 3 (External Forgejo). Enter endpoint URL, repo path, API token.
- **Expected**: `config.md` updated with `Provider: forgejo-remote`, `Endpoint: https://forge.example.com`, `Repository: myteam/myproject`, `Auth Method: api-token`. Token stored in `~/.squidsquad/secrets`.
- **Verification**: `python references/scripts/tracker.py check-gh` succeeds (adapter routes to Forgejo connectivity check). `curl -H "Authorization: token $TOKEN" https://forge.example.com/api/v1/repos/myteam/myproject` returns repo info.

### TC-11: Secrets file permissions — Unix
- **Precondition**: Unix/macOS system. `~/.squidsquad/secrets` written by setup wizard.
- **Steps**: Check file permissions after wizard writes the token.
- **Expected**: File permissions are `600` (owner read/write only). No group or other access.
- **Verification**: `stat -c '%a' ~/.squidsquad/secrets` returns `600`. `ls -la ~/.squidsquad/secrets` shows `-rw-------`.

### TC-12: Secrets file permissions — Windows
- **Precondition**: Windows system. `~/.squidsquad/secrets` written by setup wizard.
- **Steps**: Check file ACLs after wizard writes the token.
- **Expected**: Inheritance removed. Only the current user has access (Full Control). No other users or groups have permissions.
- **Verification**: `icacls "$HOME/.squidsquad/secrets"` shows only the current user with `(F)` (Full Control). No `BUILTIN\Users`, no `Everyone`.

### TC-13: Secrets directory not inside a git repo
- **Precondition**: Setup wizard about to write to `~/.squidsquad/secrets`.
- **Steps**: Wizard runs a check for git repo presence in `~/.squidsquad/`.
- **Expected**: If `~/.squidsquad/` is inside a git repo (e.g., user's home directory is a git repo), wizard warns and refuses to write secrets there. Prompts for alternative location or asks user to fix.
- **Verification**: Create a test scenario: `cd ~ && git init` (temporary), run wizard, observe the warning. Clean up: `rm -rf ~/.git`.

### TC-14: Config.md Forge Backend section
- **Precondition**: `config.md` exists with current fields.
- **Steps**: After setup with Forgejo, read config.md.
- **Expected**: New section present: `## Forge Backend` with fields: `Provider` (github | forgejo-local | forgejo-remote), `Endpoint` (URL), `Repository` (owner/repo), `Auth Method` (gh-cli | api-token), `Auth Token Env Var` (if applicable). Existing sections unchanged.
- **Verification**: `python references/scripts/config.py get forge-provider` returns the correct value. Manual read of `config.md` confirms section structure.

### TC-15: Backward compatibility — missing forge_adapter.py fallback
- **Precondition**: `forge_adapter.py` does NOT exist (simulating pre-upgrade state). `tracker.py` and `git_ops.py` are the refactored versions.
- **Steps**: Run `python references/scripts/tracker.py check-gh`, `python references/scripts/tracker.py list-issues skill`, `python references/scripts/git_ops.py pr-create "Test" "Body"`.
- **Expected**: All commands succeed by falling back to direct `gh` CLI calls. No `ImportError` or crash. Behavior identical to pre-refactor.
- **Verification**: Rename `forge_adapter.py` to `forge_adapter.py.bak`. Run all tracker.py subcommands. Confirm zero errors. Restore the file.

### TC-16: Backward compatibility — existing GitHub users unaffected
- **Precondition**: Existing project with `config.md` that has NO `Forge Backend` section (pre-upgrade config).
- **Steps**: Run `python references/scripts/tracker.py list-issues skill`, `python references/scripts/tracker.py create-issue --title "Test" --body "Test" --role skill --severity low --reporter pm-lead`.
- **Expected**: All operations work. Missing `Forge Backend` section defaults to `Provider: github`, `Auth Method: gh-cli`. No errors about missing config fields.
- **Verification**: Confirm exit code 0 for all commands. Confirm the created issue appears on GitHub.

### TC-17: Forgejo API — label creation
- **Precondition**: Forgejo instance running. No labels exist in the repo.
- **Steps**: Call `create_label(name="squidsquad", color="#0075ca", description="SquidSquad managed")` and all standard SquidSquad labels (status:*, type:*, role:*, priority:*).
- **Expected**: All labels created successfully via `POST /api/v1/repos/{owner}/{repo}/labels`. Labels visible in Forgejo UI with correct colors.
- **Verification**: `curl http://localhost:3000/api/v1/repos/{owner}/{repo}/labels` returns all created labels.

### TC-18: Forgejo down mid-cycle
- **Precondition**: Forgejo instance configured. Agent running a cycle. Forgejo stopped mid-cycle.
- **Steps**: Start an agent cycle. Stop Forgejo container (`docker stop forgejo`) before the agent's tracker operations.
- **Expected**: Agent prints `[... HH:MM:SS] Forge unreachable — skipping tracker operations. Will retry next cycle.` Agent completes the cycle (health check, local file ops succeed). No crash, no traceback.
- **Verification**: Check agent's iteration log for the "Forge unreachable" message. Confirm next cycle retries and succeeds after `docker start forgejo`.

### TC-19: Docker port conflict during setup
- **Precondition**: Port 3000 already in use (e.g., `python -m http.server 3000 &`).
- **Steps**: Run setup wizard, select Local Forgejo.
- **Expected**: Wizard detects port 3000 is occupied. Offers an alternative port (e.g., 3001). User confirms. Forgejo starts on the alternative port. `config.md` Endpoint reflects the chosen port.
- **Verification**: `docker ps` shows Forgejo on the alternative port. `curl http://localhost:3001/api/v1/version` succeeds.

### TC-20: Windows path handling in Docker volumes
- **Precondition**: Windows system with Docker Desktop (WSL2 backend).
- **Steps**: Run setup wizard, select Local Forgejo. Wizard creates docker-compose file with volume mounts.
- **Expected**: Volume paths use forward slashes or Docker-compatible format. `docker compose up -d` succeeds without path translation errors.
- **Verification**: `docker compose -f references/docker/docker-compose.forgejo.yml config` shows valid volume paths. Forgejo starts and data persists across restarts.

### TC-21: Forgejo version compatibility check
- **Precondition**: Forgejo instance running an older version (< v7).
- **Steps**: Adapter initializes and queries Forgejo version.
- **Expected**: Adapter detects version < 7 and warns about potential missing features (draft PRs, label batch operations). Does not crash. Proceeds with available functionality.
- **Verification**: Check adapter logs/output for version warning. Confirm basic operations (list issues, create issue) still work on older Forgejo.

### TC-22: PR URL format normalization
- **Precondition**: Forgejo backend active. A PR exists.
- **Steps**: Call `create_pr()` and inspect the returned URL. Call `view_pr()` and inspect any URL fields.
- **Expected**: URLs use `/pulls/N` format (Forgejo convention) in raw API responses, but the adapter normalizes to a consistent format that agents can display. No broken links in Discussion comments referencing PRs.
- **Verification**: Grep agent Discussion comments for PR URLs. All URLs resolve correctly when opened in a browser.

### TC-23: Diagnostics issue reporting always uses GitHub
- **Precondition**: Project configured with `Provider: forgejo-local`.
- **Steps**: Run `/squidsquad-issue` to report a bug to upstream SquidSquad.
- **Expected**: The issue is filed on the SquidSquad GitHub repo (not on the user's Forgejo instance). The forge adapter is bypassed for upstream reporting.
- **Verification**: Check GitHub (github.com) for the filed issue. Confirm no issue was created on the local Forgejo instance.

### TC-24: tracker.py check-gh equivalent for Forgejo
- **Precondition**: `config.md` set to `Provider: forgejo-local`. Forgejo running.
- **Steps**: Run `python references/scripts/tracker.py check-gh`.
- **Expected**: Instead of checking `gh` CLI auth, the adapter checks Forgejo endpoint connectivity and token validity. Returns exit code 0 on success, exit code 1 on failure with a Forgejo-specific error message.
- **Verification**: Run with valid token (exit 0). Run with invalid token (exit 1, message mentions Forgejo auth). Run with Forgejo down (exit 1, message mentions connectivity).

### TC-25: Forgejo backend — draft PR on Forgejo without draft support
- **Precondition**: Forgejo instance that does not support draft PRs (older version or feature disabled).
- **Steps**: Call `create_pr(title="Test", body="Body", head="feature", base="main", draft=True)`.
- **Expected**: Adapter gracefully degrades — creates a non-draft PR instead. Logs a warning that draft PRs are not supported. No crash.
- **Verification**: PR appears in Forgejo UI as a regular (non-draft) PR. Adapter output includes a warning message.

### TC-26: Token read from ~/.squidsquad/secrets
- **Precondition**: Token file at `~/.squidsquad/secrets` with correct permissions. `config.md` has `Provider: forgejo-local`, `Auth Method: api-token`.
- **Steps**: Run any tracker operation (e.g., `python references/scripts/tracker.py list-issues skill`).
- **Expected**: Adapter reads the token from `~/.squidsquad/secrets`, not from environment variables. Token is used in `Authorization: token <TOKEN>` header for Forgejo API calls.
- **Verification**: Unset any `FORGEJO_TOKEN` env var. Confirm operations succeed using file-based token only. Delete the secrets file, confirm operations fail with auth error.

### TC-27: Cross-clone secrets access
- **Precondition**: Two SquidSquad clones (e.g., PM clone and skill clone) on the same machine. `~/.squidsquad/secrets` exists.
- **Steps**: Run tracker operations from both clones.
- **Expected**: Both clones read the same `~/.squidsquad/secrets` file. Token works for both. No per-clone token duplication needed.
- **Verification**: Run `python references/scripts/tracker.py check-gh` from each clone directory. Both return exit 0.

### TC-28: Upgrade path — /squidsquad-upgrade adds Forge Backend section
- **Precondition**: Existing project with pre-Forgejo `config.md` (no `Forge Backend` section).
- **Steps**: Run `/squidsquad-upgrade`.
- **Expected**: `Forge Backend` section added to `config.md` with defaults: `Provider: github`, `Endpoint: https://api.github.com`. Existing config sections unchanged. No other side effects.
- **Verification**: `diff` config.md before and after upgrade. Only the new `Forge Backend` section should differ. `python references/scripts/config.py get forge-provider` returns `github`.

### TC-29: Upgrade — non-upgraded installs gracefully degrade
- **Precondition**: User has the new `tracker.py` (refactored) but has NOT run `/squidsquad-upgrade` (no `Forge Backend` section in config.md, no `forge_adapter.py`).
- **Steps**: Run normal agent cycle.
- **Expected**: tracker.py falls back to direct `gh` calls. No crash. No warning noise. Agent operates as before.
- **Verification**: Agent iteration log shows normal cycle completion. No `forge_adapter` import errors in logs.

### TC-30: Forgejo backend — concurrent label add and remove
- **Precondition**: Forgejo issue with labels `status:in-progress` and `role:skill`.
- **Steps**: Call `edit_labels(number=N, add=["status:pending-test"], remove=["status:in-progress"])`.
- **Expected**: Remove completes before add. Final state has `status:pending-test` and `role:skill`. No race condition where both old and new status labels coexist.
- **Verification**: Immediately query labels after the call: `curl http://localhost:3000/api/v1/repos/{owner}/{repo}/issues/N/labels`. Only `status:pending-test` and `role:skill` present.

### TC-31: urllib usage — no requests dependency
- **Precondition**: Python environment with no `requests` package installed (`pip uninstall requests`).
- **Steps**: Import `forge_adapter.py`. Run Forgejo backend operations.
- **Expected**: All operations succeed using only `urllib.request`. No `ImportError` for `requests`. No external HTTP dependencies.
- **Verification**: `python -c "import forge_adapter"` succeeds. `pip list | grep requests` returns nothing. Forge operations work.

### TC-32: Forgejo backend — issue close via PATCH
- **Precondition**: Forgejo issue exists in open state.
- **Steps**: Call `close_issue(number=N)`.
- **Expected**: `PATCH /api/v1/repos/{owner}/{repo}/issues/N` sent with `{"state": "closed"}`. Issue transitions to closed state.
- **Verification**: `curl http://localhost:3000/api/v1/repos/{owner}/{repo}/issues/N` shows `"state": "closed"`.

### TC-33: Forgejo backend — add comment
- **Precondition**: Forgejo issue exists.
- **Steps**: Call `add_comment(number=N, body="Test comment from adapter")`.
- **Expected**: `POST /api/v1/repos/{owner}/{repo}/issues/N/comments` sent. Comment appears on the issue.
- **Verification**: `curl http://localhost:3000/api/v1/repos/{owner}/{repo}/issues/N/comments` includes the new comment.

### TC-34: tracker.py function signatures unchanged after refactor
- **Precondition**: Pre-refactor `tracker.py` function signature list captured.
- **Steps**: Compare `grep "^def " references/scripts/tracker.py` output before and after the refactor.
- **Expected**: All public function signatures (`check_gh`, `list_issues`, `list_by_labels`, `list_all_open`, `work_queue`, `add_labels`, `create_issue`, `create_task`, `transition`, `comment`, `get_labels`, `get_state`, `close_issue`) are identical. No added, removed, or changed parameters.
- **Verification**: `diff <(git show HEAD~1:references/scripts/tracker.py | grep "^def ") <(grep "^def " references/scripts/tracker.py)` shows zero differences in public function lines.

### TC-35: git_ops.py function signatures unchanged after refactor
- **Precondition**: Pre-refactor `git_ops.py` function signature list captured.
- **Steps**: Compare `grep "^def " references/scripts/git_ops.py` output before and after the refactor.
- **Expected**: All public function signatures unchanged. Only internal implementation of `pr_create`, `pr_merge`, `pr_view` (if added) routes through adapter.
- **Verification**: `diff <(git show HEAD~1:references/scripts/git_ops.py | grep "^def ") <(grep "^def " references/scripts/git_ops.py)` shows zero differences.

## Smoke Tests

- [ ] `python references/scripts/tracker.py check-gh` returns exit 0 with GitHub backend
- [ ] `python references/scripts/tracker.py check-gh` returns exit 0 with Forgejo backend (Forgejo running)
- [ ] `python -c "from references.scripts.forge_adapter import ForgeBackend"` imports without error
- [ ] `python references/scripts/config.py get forge-provider` returns a valid value (github, forgejo-local, or forgejo-remote)
- [ ] `cat ~/.squidsquad/secrets` is readable by current user (exists after Forgejo setup)
- [ ] `docker ps | grep forgejo` shows running container after local Forgejo setup
- [ ] `curl http://localhost:3000/api/v1/version` returns JSON with Forgejo version after local setup
- [ ] `python references/scripts/tracker.py list-issues skill` works with both backends
- [ ] `python references/scripts/git_ops.py pull` works regardless of backend (git is backend-agnostic)
- [ ] Config.md contains `## Forge Backend` section after upgrade or fresh setup
- [ ] Removing `forge_adapter.py` does not crash `tracker.py` (fallback works)
- [ ] No `import requests` in any modified file

## Regression Risks

- **tracker.py behavioral change under GitHub**: Any change to how `gh` CLI arguments are constructed in the GitHub adapter could silently alter query results (wrong labels, missing issues, different JSON fields). Watch for: label quoting differences, `--json` field list changes, `--limit` default changes.
- **git_ops.py PR flow breakage**: `pr_create` and `pr_merge` are used by the PM delivery fallback (Step 6d). If the adapter introduces any latency, error handling change, or return value difference, auto-merge could fail silently. Watch for: exit code interpretation, merge conflict detection, PR number extraction from output.
- **config.md parsing**: Adding the `Forge Backend` section could break `config.py` if the parser is sensitive to section ordering or duplicate field names. Watch for: parser errors on new section, field name collisions with existing fields.
- **health_check.py / boot_remote.py false positives**: These scripts are documented as having zero GitHub API dependencies. If the refactor accidentally introduces a forge dependency, these local-only scripts could fail when the forge is unreachable. Watch for: new imports in these files.
- **Wizard prerequisite check regression**: The current wizard checks for `gh` CLI. If the provider-aware check is buggy, GitHub users could pass without `gh` being verified, or Forgejo users could be falsely blocked on a `gh` check. Watch for: check logic branching on provider value.
- **Label ID vs name mismatch**: Forgejo's label remove endpoint uses label IDs (integers), not label names. If the adapter caches label name-to-ID mappings incorrectly, label operations could target wrong labels. Watch for: stale label cache after label creation/deletion.
- **Windows file permissions**: `icacls` commands are Windows-specific and easy to get wrong. Incorrect ACL removal could lock the user out of their own secrets file, or leave it world-readable. Watch for: icacls syntax errors, inheritance not properly removed.
- **urllib error handling**: `urllib.request` raises different exceptions than `subprocess` (which is used for `gh`). If the adapter's error handling doesn't normalize these, agents could see unhandled `urllib.error.HTTPError` or `URLError` exceptions instead of clean error messages. Watch for: bare `urllib` exceptions in agent output.
- **Existing Tracker field compatibility**: The existing `Tracker: github-issues` field in config.md must remain valid and map to `Provider: github`. If the upgrade path doesn't handle this mapping, existing configs could be misinterpreted. Watch for: tracker.py checking the wrong config field.

## Comprehension Questions

### CQ-1: How does tracker.py decide whether to use gh CLI or Forgejo HTTP calls?
- **Files**: `references/scripts/tracker.py`, `references/scripts/forge_adapter.py`, `.squidsquad/config.md`
- **Expected**: tracker.py imports forge_adapter.py and calls its unified interface. forge_adapter.py reads the `Provider` field from the `Forge Backend` section in config.md at import time. If Provider is `github`, it wraps `gh` CLI calls. If Provider is `forgejo-local` or `forgejo-remote`, it uses `urllib` HTTP calls to the Forgejo REST API. If forge_adapter.py is missing, tracker.py falls back to direct `gh` CLI calls (backward compatibility).

### CQ-2: Where are Forgejo API tokens stored and what protections are applied?
- **Files**: `references/scripts/forge_adapter.py`, `references/scripts/wizard.py` (or `forgejo_setup.py`), `.squidsquad/config.md`
- **Expected**: Tokens are stored in `~/.squidsquad/secrets` (not in environment variables, not in config.md). On Unix, the file has `chmod 600` permissions. On Windows, `icacls` removes inheritance and grants only the current user Full Control. The setup wizard verifies that `~/.squidsquad/` is not inside any git repo before writing secrets to prevent accidental commits.

### CQ-3: What happens if a user upgrades to the Forgejo-capable version but does not run /squidsquad-upgrade?
- **Files**: `references/scripts/tracker.py`, `references/scripts/forge_adapter.py`, `.squidsquad/config.md`
- **Expected**: Everything continues to work. If forge_adapter.py is present but config.md has no `Forge Backend` section, the adapter defaults to `Provider: github` and `Auth Method: gh-cli`. If forge_adapter.py is missing entirely, tracker.py falls back to direct `gh` CLI calls. No crash, no warning noise. The user is unaffected.

### CQ-4: How does the Forgejo adapter handle the label API difference (GitHub atomic vs Forgejo separate endpoints)?
- **Files**: `references/scripts/forge_adapter.py`
- **Expected**: The GitHub backend's `edit_labels` method issues a single `gh issue edit --add-label X --remove-label Y` call (atomic). The Forgejo backend's `edit_labels` method issues two sequential HTTP calls: first `DELETE /api/v1/repos/{owner}/{repo}/issues/{id}/labels/{label_id}` to remove, then `POST /api/v1/repos/{owner}/{repo}/issues/{id}/labels` to add. Remove happens before add to prevent transient states with conflicting labels.

### CQ-5: Which files have zero forge backend dependency and must remain that way?
- **Files**: `references/scripts/health_check.py`, `references/scripts/boot_remote.py`, `references/scripts/diagnostics.py`
- **Expected**: health_check.py, boot_remote.py, and diagnostics.py operate on local files only (`.health`, `current-state`, `.local-config`). They must NOT import forge_adapter.py or make any forge API calls. Their functionality must be completely independent of the forge backend — they work identically whether the user is on GitHub, Forgejo, or has no network access.

### CQ-6: How does the setup wizard determine which prerequisite checks to run?
- **Files**: `references/scripts/wizard.py`, `references/wizard/WIZARD.md`
- **Expected**: The wizard asks the user to select a forge backend (GitHub, Local Forgejo, External Forgejo). Based on the selection: GitHub requires `gh` CLI authentication check. Local Forgejo requires Docker availability check (and port 3000 availability). External Forgejo requires endpoint connectivity and token validity checks. The `gh` CLI check is skipped entirely for Forgejo backends.

### CQ-7: What is the adapter's behavior when the Forgejo instance is unreachable during an agent cycle?
- **Files**: `references/scripts/forge_adapter.py`, `references/scripts/tracker.py`
- **Expected**: The adapter raises a connection error. tracker.py (or the agent's cycle logic) catches this and prints `[... HH:MM:SS] Forge unreachable — skipping tracker operations. Will retry next cycle.` The agent completes the rest of the cycle (health check, local file operations, commit/push). No crash, no traceback visible to the user. Next cycle retries normally.

### CQ-8: Does the /squidsquad-issue command use the user's forge backend or always GitHub?
- **Files**: `references/scripts/tracker.py` (or whichever script handles upstream issue filing)
- **Expected**: `/squidsquad-issue` always uses GitHub regardless of the user's forge backend. It reports to the upstream SquidSquad repository on GitHub, not to the user's project forge. This is hardcoded — the forge adapter is bypassed for upstream issue reporting.
