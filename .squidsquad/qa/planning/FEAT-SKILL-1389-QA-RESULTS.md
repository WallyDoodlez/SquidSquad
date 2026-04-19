# FEAT-SKILL-1389 QA Results -- Self-Hosted Forge Backend (Forgejo)

**Executed**: 2026-04-18
**Executor**: QA subagent (structural verification)

## Summary Table

| TC | Title | Result |
|----|-------|--------|
| TC-1 | GitHub adapter wraps gh identically | FAIL |
| TC-2 | Forgejo backend creates issue via HTTP | HUMAN-REQUIRED |
| TC-3 | Forgejo backend list issues with filters | HUMAN-REQUIRED |
| TC-4 | Forgejo backend edit labels | HUMAN-REQUIRED |
| TC-5 | Forgejo backend PR create/view/merge | HUMAN-REQUIRED |
| TC-6 | tracker.py operations through adapter | FAIL |
| TC-7 | git_ops.py PR operations through adapter | FAIL |
| TC-8 | Setup wizard forge backend selection | HUMAN-REQUIRED |
| TC-9 | GitHub selection defaults in config | PASS |
| TC-10 | Setup wizard external Forgejo | HUMAN-REQUIRED |
| TC-14 | Config.md Forge Backend section exists | FAIL |
| TC-15 | Backward compat -- missing forge_adapter.py fallback | PASS |
| TC-16 | Backward compat -- existing GitHub users | PASS |
| TC-17 | Forgejo API label creation | HUMAN-REQUIRED |
| TC-18 | Forgejo down mid-cycle | HUMAN-REQUIRED |
| TC-19 | Docker port conflict during setup | HUMAN-REQUIRED |
| TC-20 | Windows path handling in Docker volumes | HUMAN-REQUIRED |
| TC-23 | Diagnostics always uses GitHub | PASS |
| TC-24 | tracker.py check-gh for Forgejo | HUMAN-REQUIRED |
| TC-25 | Forgejo draft PR fallback | HUMAN-REQUIRED |
| TC-26 | Token read from ~/.squidsquad/secrets | PASS |
| TC-28 | Upgrade path | FAIL |
| TC-29 | Non-upgraded installs gracefully degrade | PASS |
| TC-30 | Forgejo concurrent label add/remove | HUMAN-REQUIRED |
| TC-31 | urllib usage, no requests dependency | PASS |
| TC-32 | Forgejo issue close via PATCH | HUMAN-REQUIRED |
| TC-33 | Forgejo add comment | HUMAN-REQUIRED |
| TC-34 | tracker.py function signatures unchanged | PASS |
| TC-35 | git_ops.py function signatures unchanged | PASS |

**Structurally verifiable: 15 TCs executed**
- PASS: 9
- FAIL: 4
- HUMAN-REQUIRED: 12

---

## Detailed Per-TC Findings

### TC-1: GitHub adapter wraps gh identically
- **Result**: FAIL
- **Evidence**: The `GitHubAdapter` class in `forge_adapter.py` (lines 160-268) implements all required methods (`list_issues`, `create_issue`, `view_issue`, `close_issue`, `add_comment`, `add_labels`, `remove_labels`, `edit_labels`, `create_pr`, `merge_pr`, `view_pr`, `list_prs`, `pr_ready`, `check_connection`). However, the adapter is NOT used by `tracker.py` or `git_ops.py`. Both files still make direct `gh` CLI calls via their own `_run_list()` helpers. There is no integration -- `forge_adapter.py` exists as a standalone module that neither `tracker.py` nor `git_ops.py` imports. The gh command construction in `GitHubAdapter` also differs from `tracker.py` in several ways:
  - `tracker.py` `list_issues()` uses `--label` with a comma-joined string; `GitHubAdapter.list_issues()` uses separate `--label` flags per label
  - `tracker.py` `check_gh()` runs `gh issue list --limit 1`; `GitHubAdapter.check_connection()` runs `gh auth status`
  - `tracker.py` `add_labels()` uses `--add-label` with a comma-joined string; `GitHubAdapter.add_labels()` uses separate `--add-label` per label
  - `tracker.py` `create_issue()` adds role, severity, type labels in a single `--label` flag; `GitHubAdapter.create_issue()` uses separate `--label` per label
- **Conclusion**: The adapter wraps gh in a structurally similar way but is NOT identical to the hardcoded calls in `tracker.py`. The adapter is also not wired into `tracker.py` or `git_ops.py`.

### TC-6: tracker.py operations through adapter
- **Result**: FAIL
- **Evidence**: `grep "forge_adapter" references/scripts/tracker.py` returns zero matches. `tracker.py` does not import `forge_adapter` anywhere. All operations use direct `gh` CLI calls via `_run_list(["gh", ...])`. The refactor to route through the adapter has NOT been performed.

### TC-7: git_ops.py PR operations through adapter
- **Result**: FAIL
- **Evidence**: `grep "forge_adapter" references/scripts/git_ops.py` returns zero matches. `git_ops.py` does not import `forge_adapter`. `pr_create()` and `pr_merge()` both call `_run_list(["gh", ...])` directly. The refactor has NOT been performed.

### TC-9: GitHub selection defaults in config
- **Result**: PASS
- **Evidence**: `config.py` FIELD_MAP (lines 80-83) includes `forge-provider`, `forge-endpoint`, `forge-owner`, `forge-repo` mapped to the `Forge Backend` section. `forge_adapter.py` `_read_forge_config()` defaults to `{"provider": "github", "endpoint": "https://api.github.com"}` when no `Forge Backend` section exists. The wizard (WIZARD.md Step 5c) defaults to GitHub and records `"provider": "github"`. The default path correctly results in GitHub being used.

### TC-14: Config.md Forge Backend section exists
- **Result**: FAIL
- **Evidence**: `grep "Forge Backend" .squidsquad/config.md` returns no matches. Running `python references/scripts/config.py get forge-provider` exits with error "Field 'forge-provider' not found in config.md". The `## Forge Backend` section has NOT been added to the current config.md. Note: this is expected for an existing GitHub install that has not run `/squidsquad-upgrade` with the new Forgejo support -- the section would only appear after setup or upgrade. However, the test plan expects it to exist "after upgrade or fresh setup", and the upgrade path has not been implemented yet (see TC-28).

### TC-15: Backward compat -- missing forge_adapter.py fallback
- **Result**: PASS
- **Evidence**: Since `tracker.py` and `git_ops.py` do NOT import `forge_adapter.py` at all, removing `forge_adapter.py` has zero effect on their behavior. They make direct `gh` CLI calls unconditionally. This means backward compatibility is trivially maintained -- there is no forge_adapter dependency to break. While this passes the letter of the test case (no crash, behavior identical), it passes for the wrong reason: the refactor simply hasn't happened.

### TC-16: Backward compat -- existing GitHub users unaffected
- **Result**: PASS
- **Evidence**: The current `config.md` has NO `Forge Backend` section. `tracker.py` and `git_ops.py` work without it because they don't read forge config -- they call `gh` directly. `forge_adapter.py` `_read_forge_config()` defaults to `provider: github` when the section is missing (verified in test `test_defaults_to_github`). Existing GitHub users are completely unaffected.

### TC-23: Diagnostics always uses GitHub
- **Result**: PASS
- **Evidence**: `diagnostics.py` does not import `forge_adapter` (verified via grep). The `/squidsquad-issue` report generation (line 181) produces a template for filing on GitHub. The script imports only `config`, `json`, `subprocess`, `sys`, `datetime`, and `Path`. It has zero forge backend dependency. Upstream reporting always targets GitHub.

### TC-26: Token read from ~/.squidsquad/secrets
- **Result**: PASS
- **Evidence**: `ForgejoAdapter._load_token()` (forge_adapter.py lines 278-284) calls `shared_fs.read_secret_or_env("FORGEJO_TOKEN")`. `shared_fs.py` `read_secret_or_env()` reads from `~/.squidsquad/secrets` first, falling back to environment variables. `shared_fs.py` `read_secret()` reads `~/.squidsquad/secrets` and parses `KEY=VALUE` lines. The secrets file gets `chmod 600` on Unix via `_restrict_permissions()`. Token is used in `Authorization: token {self._token}` header (line 294).

### TC-28: Upgrade path
- **Result**: FAIL
- **Evidence**: There is no implementation of `/squidsquad-upgrade` that adds a `Forge Backend` section to config.md. The `config.py` FIELD_MAP includes `forge-provider` -> `("Forge Backend", "Provider")` mapping, but there is no upgrade script that writes the section. The wizard (WIZARD.md Step 5c) writes it for fresh installs, but the upgrade path for existing installs is not implemented. An existing GitHub user running the current code would have no `Forge Backend` section in config.md and `config.py get forge-provider` would fail.

### TC-29: Non-upgraded installs gracefully degrade
- **Result**: PASS
- **Evidence**: `tracker.py` and `git_ops.py` do not import `forge_adapter.py`, so there is no import to fail. `forge_adapter.py` `_read_forge_config()` returns `provider: github` defaults when the config section is missing. All operations continue to use direct `gh` CLI calls. No crash, no warning noise.

### TC-31: urllib usage, no requests dependency
- **Result**: PASS
- **Evidence**: `grep "import requests" references/scripts/` returns zero matches across all script files. `forge_adapter.py` imports `urllib.request`, `urllib.error`, `urllib.parse` (lines 18-20). `forgejo_setup.py` imports `urllib.request`, `urllib.error` (lines 21-22). The `ForgejoAdapter._api()` method uses `urllib.request.Request` and `urllib.request.urlopen`. No external HTTP dependencies exist. All 15 forge_adapter tests pass with only stdlib.

### TC-34: tracker.py function signatures unchanged
- **Result**: PASS
- **Evidence**: All public functions are present with expected signatures:
  - `check_gh()` -- no params
  - `list_issues(role, issue_type="bug", status=None)`
  - `list_by_labels(labels_str)`
  - `list_all_open()`
  - `work_queue(role)`
  - `add_labels(number, labels_str)`
  - `create_issue(title, body, role, severity, reporter=None)`
  - `create_task(title, body, role, priority, reporter=None)`
  - `transition(number, from_status, to_status, role=None, force=False)`
  - `comment(number, role, message)`
  - `get_labels(number)`
  - `get_state(number)`
  - `close_issue(number)`
  - Since no refactor occurred, signatures are trivially unchanged.

### TC-35: git_ops.py function signatures unchanged
- **Result**: PASS
- **Evidence**: All public functions present with expected signatures:
  - `pull()`, `add_all()`, `commit(role, message)`, `push()`
  - `commit_push(role, message)`, `branch_create(name)`, `branch_switch(name)`
  - `branch_exists(name)`, `branch_delete(name)`, `current_branch()`
  - `pr_create(title, body)`, `pr_merge(pr_number, strategy="squash")`
  - `commit_code(role, branch, message)`, `commit_state(role, message)`
  - `has_changes()`, `last_hash()`
  - Since no refactor occurred, signatures are trivially unchanged.

---

## Comprehension Test Results

### CQ-1: How does tracker.py decide whether to use gh CLI or Forgejo HTTP calls?
- **Expected**: tracker.py imports forge_adapter and calls its unified interface based on Provider config.
- **Actual**: tracker.py does NOT import forge_adapter at all. It always uses direct `gh` CLI calls via `_run_list(["gh", ...])`. The `forge_adapter.py` module exists as a standalone abstraction layer but is not wired into tracker.py. The integration step (refactoring tracker.py to use the adapter) has not been performed.
- **Result**: FAIL -- The expected architecture is not implemented.

### CQ-2: Where are Forgejo API tokens stored and what protections are applied?
- **Expected**: Tokens in `~/.squidsquad/secrets` with chmod 600.
- **Actual**: Correct. `shared_fs.py` creates `~/.squidsquad/secrets` with `_restrict_permissions()` (chmod 600 on Unix, platform-aware). `ForgejoAdapter._load_token()` reads via `shared_fs.read_secret_or_env("FORGEJO_TOKEN")`. The wizard (WIZARD.md Step 5c) writes the token via `shared_fs.py write-secret`.
- **Result**: PASS

### CQ-3: What happens if a user upgrades to the Forgejo-capable version but does not run /squidsquad-upgrade?
- **Expected**: Everything continues to work via fallback.
- **Actual**: Correct. tracker.py and git_ops.py don't import forge_adapter, so they can't break. forge_adapter.py defaults to GitHub when config section is missing. No crash, no warning.
- **Result**: PASS (but for trivial reasons -- no refactor means no breakage risk)

### CQ-4: How does the Forgejo adapter handle the label API difference?
- **Expected**: GitHub uses single `gh issue edit --add-label X --remove-label Y`. Forgejo uses two sequential HTTP calls (DELETE then POST).
- **Actual**: Correct. `ForgeAdapter.edit_labels()` (base class, line 128-133) calls `remove_labels()` first, then `add_labels()`. `ForgejoAdapter.remove_labels()` resolves label names to IDs via `_resolve_label_ids()` then issues `DELETE` per label. `ForgejoAdapter.add_labels()` resolves to IDs and issues a single `POST`. `GitHubAdapter.edit_labels()` inherits the base class behavior (separate add/remove calls), but each uses `gh issue edit` with multiple `--add-label`/`--remove-label` flags. Note: the GitHubAdapter does NOT use a single atomic `gh issue edit --add-label X --remove-label Y` call -- it makes two separate `gh issue edit` calls (one for removes, one for adds), which differs slightly from the current tracker.py behavior.
- **Result**: PASS (structurally correct in forge_adapter.py)

### CQ-5: Which files have zero forge backend dependency and must remain that way?
- **Expected**: health_check.py, boot_remote.py, diagnostics.py.
- **Actual**: Confirmed. All three files were grep'd for "forge" and "forge_adapter" -- zero matches. Their imports are limited to standard library modules (json, os, subprocess, sys, etc.) and local config. They operate on local files only.
- **Result**: PASS

### CQ-6: How does the setup wizard determine which prerequisite checks to run?
- **Expected**: Wizard asks user to select forge backend, then runs provider-specific checks.
- **Actual**: Correct. WIZARD.md Step 5c asks the user "GitHub/Forgejo". If GitHub: skip (no Docker needed). If Forgejo: runs `forgejo_setup.py check-docker` (checks Docker + Docker Compose + daemon + port availability), then deploys, guides user through account/repo creation, creates token. The `gh` CLI check (Step 0) runs regardless of forge selection -- this is correct because gh is still needed for some operations even with Forgejo.
- **Result**: PARTIAL PASS -- The wizard does not skip the gh CLI check for Forgejo users. Step 0 always requires gh authentication. The test plan expected gh check to be skipped for Forgejo backends, but the implementation requires it unconditionally.

### CQ-7: What is the adapter's behavior when the Forgejo instance is unreachable during an agent cycle?
- **Expected**: Adapter raises connection error, tracker.py catches it and prints "Forge unreachable" message.
- **Actual**: `ForgejoAdapter._api()` (line 302-308) catches `urllib.error.HTTPError` and generic `Exception`, prints to stderr, and returns `None`. The caller methods return empty lists or `None` on failure. However, tracker.py does not use the adapter at all, so the expected "Forge unreachable" message in the cycle flow is not implemented. The adapter itself handles errors gracefully (no crash, returns None), but the agent-level retry logic described in the test plan is not wired up.
- **Result**: PARTIAL PASS -- Adapter handles errors gracefully but integration with agent cycle logic is missing.

### CQ-8: Does the /squidsquad-issue command use the user's forge backend or always GitHub?
- **Expected**: Always uses GitHub regardless of forge backend.
- **Actual**: Correct. `diagnostics.py` does not import `forge_adapter`. The `report()` function (line 181) generates a template with `*Filed via /squidsquad-issue*` targeting the upstream SquidSquad repo. It uses `gh` directly (via subprocess) for any GitHub operations. The forge adapter is completely bypassed.
- **Result**: PASS

---

## Smoke Test Results

| # | Smoke Test | Result | Notes |
|---|-----------|--------|-------|
| 1 | `tracker.py check-gh` returns exit 0 with GitHub backend | NOT RUN | Would require live gh auth verification |
| 2 | `tracker.py check-gh` returns exit 0 with Forgejo backend | HUMAN-REQUIRED | Needs live Forgejo instance |
| 3 | `from references.scripts.forge_adapter import ForgeBackend` imports without error | FAIL | Class is named `ForgeAdapter`, not `ForgeBackend`. `from references.scripts.forge_adapter import ForgeAdapter` works. |
| 4 | `config.py get forge-provider` returns valid value | FAIL | `Forge Backend` section not in config.md. Returns error. |
| 5 | `~/.squidsquad/secrets` readable by current user | PASS (structural) | `shared_fs.py` creates it with restricted permissions |
| 6 | `docker ps | grep forgejo` shows running container | HUMAN-REQUIRED | Docker not running |
| 7 | `curl localhost:3000/api/v1/version` returns JSON | HUMAN-REQUIRED | Docker not running |
| 8 | `tracker.py list-issues skill` works with both backends | NOT RUN / HUMAN-REQUIRED | Adapter not integrated into tracker.py |
| 9 | `git_ops.py pull` works regardless of backend | PASS (structural) | git_ops.py pull uses git directly, no forge dependency |
| 10 | Config.md contains `## Forge Backend` section | FAIL | Section not present |
| 11 | Removing forge_adapter.py does not crash tracker.py | PASS | tracker.py does not import it |
| 12 | No `import requests` in any modified file | PASS | Verified via grep -- zero matches |

---

## Existing Test Suite Results

All 15 existing tests in `tests/test_forge_adapter.py` **PASS** (pytest, 0.06s):

- TestReadForgeConfig: 3/3 PASS (defaults, forgejo config, missing section)
- TestGetAdapter: 6/6 PASS (github, forgejo, forgejo-local, unknown fallback, cache, reset)
- TestGitHubAdapter: 3/3 PASS (list_issues, add_comment, check_connection)
- TestForgejoAdapter: 2/2 PASS (repo_path, provider)
- TestBaseAdapter: 1/1 PASS (edit_labels calls both add and remove)

---

## Critical Findings

### Finding 1: forge_adapter.py is NOT integrated into tracker.py or git_ops.py (BLOCKING)

The core architectural promise of #1389 -- routing all forge operations through a unified adapter -- has NOT been implemented. `forge_adapter.py` exists as a well-structured standalone module with `GitHubAdapter` and `ForgejoAdapter` classes, but:

- `tracker.py` makes all 20+ `gh` CLI calls directly
- `git_ops.py` makes all PR-related `gh` calls directly
- Neither file imports `forge_adapter`

This means the Forgejo backend cannot actually be used for any agent operations. The adapter is tested in isolation (15 tests pass) but is dead code from the perspective of the running system.

### Finding 2: Config.md Forge Backend section not written (BLOCKING)

The `## Forge Backend` section does not exist in the current `config.md`. While `config.py` has the FIELD_MAP entries for it, and `forge_adapter.py` defaults to GitHub when the section is missing, the upgrade path that would add this section is not implemented.

### Finding 3: Smoke test class name mismatch

The test plan references `ForgeBackend` but the actual class is `ForgeAdapter`. This is a test plan naming inconsistency, not an implementation bug.

### Finding 4: forgejo-remote provider not handled

`forge_adapter.py` `get_adapter()` handles `"github"`, `"forgejo"`, and `"forgejo-local"` but does NOT handle `"forgejo-remote"`. Any config with `provider: forgejo-remote` would fall through to the GitHub fallback with a warning. The test plan and WIZARD.md both reference `forgejo-remote` as a valid provider value.

---

## Overall Assessment

**Status: FAIL -- Back to dev**

The `forge_adapter.py` module itself is well-implemented with correct structure, proper error handling, urllib-only dependencies, and passing unit tests. However, the critical integration work -- refactoring `tracker.py` and `git_ops.py` to route through the adapter -- has not been done. The adapter is currently dead code from the system's perspective.

Items that must be completed before re-test:
1. Refactor `tracker.py` to import and use `forge_adapter.get_adapter()` for all gh operations
2. Refactor `git_ops.py` to use the adapter for PR operations
3. Add `## Forge Backend` section to config.md (or implement the upgrade path)
4. Add `forgejo-remote` to the provider handling in `get_adapter()`
5. Fix class name in smoke test (ForgeBackend -> ForgeAdapter)
