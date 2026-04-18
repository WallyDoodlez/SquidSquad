# FEAT-SKILL-1389 Research — Self-Hosted Forge Backend (Forgejo)

## Summary

SquidSquad currently has a hard dependency on GitHub for its tracker (issue tracking, labels, comments, PR workflow) and uses the `gh` CLI as the sole interface. This task proposes adding Forgejo as an alternative forge backend so non-technical teams who cannot or do not want to use GitHub can still run SquidSquad. The human has locked the choice to Forgejo (not Gitea, not a custom backend) and wants a single provider selection at setup time.

The codebase impact is moderate but well-contained. The tracker layer (`tracker.py`) is the primary integration point — it makes 20+ distinct `gh` CLI calls and is 100% GitHub-coupled. `git_ops.py` has 2 `gh`-dependent functions (PR create/merge). `health_check.py` and `boot_remote.py` have zero GitHub API dependencies (they operate on local files). The setup wizard (`WIZARD.md`) has GitHub hardcoded into its prerequisite check and label provisioning. The key architectural insight: Forgejo provides a GitHub-compatible REST API, but the `gh` CLI does NOT natively support Forgejo. This means SquidSquad cannot simply point `gh` at a Forgejo instance — it needs an alternative CLI adapter or direct HTTP calls.

Recommendation: **Feasible with caveats.** The tracker abstraction layer (`tracker.py`) is already the single chokepoint for all GitHub operations, which is good. The main risk is the `gh` CLI gap — Forgejo has its own CLI (`forgejo-cli` or the `tea` CLI) but neither is a drop-in replacement for `gh`. The cleanest path is to add a `forge_adapter.py` that provides a unified interface, with a `github` backend (wrapping `gh`) and a `forgejo` backend (wrapping Forgejo's REST API via `curl`/`requests`). This keeps `tracker.py`'s public interface unchanged.

## Vault Context

- **BRIEFING.md priorities**: Going public focus, v1.0.0 launch
- **Related decisions**: [[decision-general-purpose-vision]] — Human confirmed SquidSquad is for all teams, not just developers. Self-hosted forge backend is part of this vision. tracker.py abstracts the difference.
- **Related patterns**: None directly applicable
- **Human preferences**: Sub-skills live in separate repos; marketplace is the monetization vehicle; agents are manually triggered (not auto-started)
- **Related learnings**: Tracker backend abstraction is already a known future direction (per project memory `project_tracker_abstraction.md`)

## Impact Analysis

### Files Touched

| File | Change Type | Scope |
|------|-------------|-------|
| `references/scripts/tracker.py` | **Major refactor** | Replace all 20+ `gh` CLI calls with calls to a forge adapter |
| `references/scripts/git_ops.py` | **Moderate** | Replace `gh pr create`, `gh pr merge`, `gh pr view` calls (3 functions) |
| `references/scripts/forge_adapter.py` | **New file** | Unified forge interface with `github` and `forgejo` backends |
| `references/scripts/wizard.py` | **Moderate** | Add forge provider selection, Forgejo deployment step, replace `check-gh` |
| `references/wizard/WIZARD.md` | **Moderate** | Add Step 0c (forge provider selection), modify Step 0 (prerequisite check per provider) |
| `.squidsquad/config.md` | **Minor** | Add `Tracker` value options, add `Forge Endpoint` field |
| `SKILL.md` | **Minor** | Update setup flow description, tracker docs |
| `references/presets/software-dev/manifest.yaml` | **Minor** | No change needed (presets are role-focused, not backend-focused) |
| `references/scripts/health_check.py` | **No change** | Reads only local files (.health, current-state, .local-config) |
| `references/scripts/boot_remote.py` | **No change** | Reads only local files and config.md, spawns terminals |
| `references/scripts/diagnostics.py` | **No change** | Local-only operations |

### Behavior Changes

- **Setup wizard** gains a new step asking which forge backend to use (github vs forgejo-local)
- **Forgejo backend**: setup wizard can optionally deploy a Forgejo instance via Docker or binary
- **tracker.py** calls route through `forge_adapter.py` instead of directly invoking `gh`
- **git_ops.py** PR functions route through `forge_adapter.py` for PR operations
- **config.md** gains a `Tracker` field with values like `github-issues` (default, current) or `forgejo-local`

### Dependencies

- **Forgejo backend**: Docker (preferred) or a Forgejo binary download
- **Forgejo REST API**: HTTP client (Python `urllib` or `requests`) for direct API calls
- **No new Python package dependencies** if using `urllib.request` (stdlib)
- **`gh` CLI**: Still required for GitHub backend, NOT required for Forgejo backend
- **`tea` CLI** (Forgejo/Gitea CLI): Optional, not required — direct REST API is more reliable
- **Git**: Always required regardless of backend (git operations are backend-agnostic)

## Side Effects

- **Risk 1**: Existing GitHub users see behavioral changes in tracker.py — Severity: **M** — Mitigation: The `github` backend in `forge_adapter.py` wraps `gh` identically to current behavior. Existing users set `Tracker: github-issues` (the default) and nothing changes. Comprehensive regression testing with the GitHub backend before release.

- **Risk 2**: Forgejo API compatibility gaps — Severity: **M** — Mitigation: Forgejo's API is documented as GitHub-compatible but has known gaps (see Forgejo API Compatibility section below). Build the adapter with explicit compatibility tests. Key areas: label management, issue comments, PR workflow. Forgejo v7+ covers all needed endpoints.

- **Risk 3**: Docker dependency for Forgejo deployment — Severity: **L** — Mitigation: Provide binary download fallback. The wizard detects Docker availability and offers the appropriate option.

- **Risk 4**: `gh` CLI no longer universally required — Severity: **L** — Mitigation: The prerequisite check in wizard.py becomes provider-aware. GitHub backend still requires `gh`. Forgejo backend skips the `gh` check and instead verifies Forgejo endpoint connectivity.

- **Risk 5**: Forgejo auth tokens vs `gh auth` — Severity: **M** — Mitigation: Forgejo uses API tokens (generated in Forgejo UI). The adapter stores the token in `.squidsquad/.local-config` or an environment variable. This is simpler than `gh auth` but different — docs must be clear.

## Forgejo API Compatibility Analysis

Forgejo implements a large subset of the GitHub REST API (v1 compatible). Key findings:

### What Works (GitHub-compatible)

| Operation | GitHub (`gh` CLI) | Forgejo REST API | Compatible? |
|-----------|-------------------|-------------------|-------------|
| List issues | `gh issue list --label X --state open --json ...` | `GET /api/v1/repos/{owner}/{repo}/issues?labels=X&state=open` | Yes |
| Create issue | `gh issue create --title X --body Y --label Z` | `POST /api/v1/repos/{owner}/{repo}/issues` | Yes |
| Edit issue labels | `gh issue edit N --add-label X --remove-label Y` | `POST/DELETE /api/v1/repos/{owner}/{repo}/issues/{id}/labels` | Yes (different endpoint shape) |
| View issue | `gh issue view N --json labels,comments` | `GET /api/v1/repos/{owner}/{repo}/issues/{id}` + `/comments` | Yes (two calls) |
| Close issue | `gh issue close N` | `PATCH /api/v1/repos/{owner}/{repo}/issues/{id}` with `state: closed` | Yes |
| Add comment | `gh issue comment N --body X` | `POST /api/v1/repos/{owner}/{repo}/issues/{id}/comments` | Yes |
| Create PR | `gh pr create --draft --title X --body Y` | `POST /api/v1/repos/{owner}/{repo}/pulls` | Yes |
| Merge PR | `gh pr merge N --squash` | `POST /api/v1/repos/{owner}/{repo}/pulls/{id}/merge` | Yes |
| View PR state | `gh pr view N --json state` | `GET /api/v1/repos/{owner}/{repo}/pulls/{id}` | Yes |
| Create labels | `gh label create X --color Y` | `POST /api/v1/repos/{owner}/{repo}/labels` | Yes |

### Known Incompatibilities

1. **`gh` CLI does not support Forgejo**: The `gh` CLI is GitHub-only. Setting `GH_HOST` or `GH_ENTERPRISE_TOKEN` does not work with Forgejo because `gh` performs GitHub-specific OAuth flows and API negotiation. There is no `GH_HOST` hack that makes `gh` work against Forgejo.

2. **Label API differences**: GitHub's `gh issue edit --add-label X --remove-label Y` is a single atomic operation. Forgejo's label API uses separate endpoints for add (`POST .../labels`) and remove (`DELETE .../labels/{id}`). The adapter must handle this as two sequential calls.

3. **JSON field naming**: Minor differences in JSON response shapes. Forgejo returns `id` as integer; GitHub returns `node_id` as string in some contexts. The adapter must normalize field access.

4. **Draft PRs**: Forgejo supports draft PRs (via `"draft": true` in the create payload) but the field is not always present in older Forgejo versions. The adapter should handle missing draft support gracefully.

5. **Search/filter syntax**: `gh issue list --search` uses GitHub's search syntax. Forgejo's issue list endpoint uses query parameters (`labels`, `state`, `type`) rather than a search string. The adapter translates SquidSquad's label-based queries to the appropriate parameter format.

### `gh` CLI and Forgejo — Not Compatible

The `gh` CLI (github.com/cli/cli) is tightly coupled to GitHub:
- Authentication uses GitHub OAuth device flow
- API calls target `api.github.com` or GitHub Enterprise Server
- `GH_HOST` only works with GitHub Enterprise Server instances, not Forgejo
- There is no environment variable or config to point `gh` at a Forgejo instance

Alternative CLIs:
- **`tea`** (Gitea/Forgejo CLI): Supports Forgejo but has a different command syntax. Not a drop-in replacement for `gh`.
- **Direct REST API** via `curl` or Python `urllib`: Most reliable approach. Forgejo's Swagger docs are comprehensive. No external CLI dependency.

**Recommendation**: Use direct HTTP calls (Python `urllib.request`) for the Forgejo backend. This avoids adding CLI dependencies and gives full control over request/response handling.

## Deployment Options

### Option A: Docker Compose (Recommended)

Forgejo provides official Docker images. Minimal setup:

```yaml
# docker-compose.forgejo.yml
version: "3"
services:
  forgejo:
    image: codeberg.org/forgejo/forgejo:9
    ports:
      - "3000:3000"    # Web UI
      - "2222:22"      # SSH (optional)
    volumes:
      - ./forgejo-data:/data
    environment:
      - FORGEJO__server__ROOT_URL=http://localhost:3000
      - FORGEJO__server__DISABLE_SSH=true
      - FORGEJO__service__DISABLE_REGISTRATION=true
```

**Pros**: Single command (`docker compose up -d`), isolated, portable, reproducible.
**Cons**: Requires Docker. ~200MB image.

Minimum Forgejo setup for SquidSquad:
- Issues enabled (default)
- Labels API (default)
- Pull requests (default, can be disabled if PR flow is not used)
- API token auth (default)
- No SSH needed (HTTPS git push suffices)
- No CI/CD needed
- No package registry needed

### Option B: Binary Download

Forgejo provides standalone binaries for Linux, macOS, and Windows:
- Download from `codeberg.org/forgejo/forgejo/releases`
- Run: `./forgejo web --port 3000`
- Data stored in a local SQLite DB (no external database needed)

**Pros**: No Docker dependency. Single binary.
**Cons**: More manual setup. User must configure admin account, create repo, generate API token. Less portable.

### Option C: Existing Forgejo Instance

User already has a Forgejo (or Gitea) instance running elsewhere. Setup wizard asks for:
- Endpoint URL (e.g., `https://forge.mycompany.com`)
- Repository path (e.g., `myteam/myproject`)
- API token

**Pros**: No deployment needed.
**Cons**: Requires user to have an existing instance.

### Wizard Deployment Flow (Recommended)

```
Step 0c — Forge Backend Selection

Which forge backend should SquidSquad use?

  1. GitHub (default) — uses your existing GitHub repo
  2. Local Forgejo — we'll set up a local Forgejo instance
  3. External Forgejo — connect to an existing Forgejo server

[User picks 2]

Do you have Docker installed? (checking...)

  Docker found. I'll set up Forgejo via Docker Compose.
  → Creates docker-compose.forgejo.yml
  → Runs docker compose up -d
  → Creates admin account
  → Creates repo
  → Generates API token
  → Initializes git remote
```

## Team Presets Architecture

### Where Presets Live

Presets already exist at `references/presets/<preset>/manifest.yaml`. The forge backend is orthogonal to presets — a `software-dev` preset can use either GitHub or Forgejo. The backend choice belongs in **config.md**, not in preset manifests.

### Config.md Changes

```markdown
## Forge Backend

- **Provider**: github | forgejo-local | forgejo-remote
- **Endpoint**: https://api.github.com | http://localhost:3000 | https://forge.example.com
- **Repository**: owner/repo
- **Auth Method**: gh-cli | api-token
- **Auth Token Env Var**: FORGEJO_TOKEN (for forgejo backends)
```

The existing `Tracker: github-issues` field in config.md already hints at this abstraction. It would be renamed/extended to reference the forge backend.

### Preset Interaction

Presets define the team shape (which roles to install). The forge backend is a separate axis:
- `software-dev` + `github` = current behavior
- `software-dev` + `forgejo-local` = same team, self-hosted forge
- `design` + `forgejo-local` = design team, self-hosted forge
- Future: `ops` + `forgejo-local` = non-technical ops team

No changes to preset manifests are needed. The forge backend is configured independently during setup.

## Edge Cases

- **Docker not available**: Wizard falls back to binary download option. If neither Docker nor a writable directory for the binary is available, wizard offers "External Forgejo" (user provides their own instance) or falls back to GitHub.

- **Forgejo down mid-cycle**: Same handling as current "GitHub unreachable" path. Agents skip tracker operations for the cycle and print: `[... HH:MM:SS] Forge unreachable — skipping tracker operations. Will retry next cycle.` The health check and boot scripts are unaffected (they read local files only).

- **Data migration between backends**: Not supported in v1. Users must choose a backend at setup time. Migration tooling (export GitHub issues -> import to Forgejo, or vice versa) is a follow-up feature. Both Forgejo and GitHub support issue import/export via API, so migration is technically feasible but out of scope.

- **Multi-user access to local Forgejo**: For a locally deployed Forgejo instance, the default setup creates a single admin user. Multi-user access requires the admin to create additional accounts in the Forgejo UI. The wizard should document this but not automate it — user management is Forgejo's responsibility.

- **git remote URL changes**: Switching from GitHub to Forgejo means the git remote URL changes. The wizard must update `.git/config` to point to the new Forgejo repo. If the user later switches back, the remote must be updated again. This is a destructive operation that should require confirmation.

- **Port conflicts**: Docker maps Forgejo to port 3000 by default. If port 3000 is in use (e.g., by a dev server), the wizard should detect this and offer an alternative port. Check with `netstat` or `ss` before starting Docker.

- **Windows path issues**: Forgejo Docker volumes on Windows require path translation. Docker Desktop handles this for WSL2 but not for older Docker Toolbox. The wizard should detect the Docker backend and adjust volume paths accordingly.

- **Forgejo version compatibility**: The adapter should target Forgejo v7+ (current stable). Older versions may lack some API endpoints (draft PRs, label batch operations). The adapter should check the Forgejo version at setup time and warn about missing features.

## Integration Risks

- **PR Flow interaction**: PR-based workflows (`PR Flow: yes`, `Auto Merge: yes`) use `gh pr` commands in `git_ops.py`. These must be routed through the forge adapter. If Forgejo is the backend, PRs are created/merged via Forgejo's API. The PR URL format differs (`/pulls/N` vs `/pull/N`) — the adapter normalizes this.

- **Improvement scanning**: Improvement scanning files issues via `tracker.py`. No special handling needed — the adapter abstracts the backend.

- **Vault operations**: Vault is entirely local file-based. Zero interaction with the forge backend.

- **Diagnostics / issue reporting**: The `/squidsquad-issue` command files issues to the upstream SquidSquad repo on GitHub. This should always use GitHub regardless of the user's forge backend — it's reporting to SquidSquad's repo, not the user's project.

- **External issue ingestion** (Step 7b in PM loop): `tracker.py list-all-open` queries all open issues. The Forgejo adapter must support the same query. Forgejo's API supports listing all issues — this is straightforward.

- **Label creation** (wizard.py `ensure-labels`): Currently uses `gh label create`. The adapter must support label creation on Forgejo via `POST /api/v1/repos/{owner}/{repo}/labels`.

## Upgrade & Migration

- **New config values**:
  - `Forge Backend > Provider`: default `github` (backward compatible)
  - `Forge Backend > Endpoint`: default `https://api.github.com`
  - `Forge Backend > Repository`: default read from existing `Project > Repo`
  - `Forge Backend > Auth Method`: default `gh-cli`
  - `Forge Backend > Auth Token Env Var`: default empty (not needed for GitHub)

- **New files**:
  - `references/scripts/forge_adapter.py` — unified forge interface (~400-500 lines)
  - `references/docker/docker-compose.forgejo.yml` — Forgejo Docker Compose template
  - `references/scripts/forgejo_setup.py` — Forgejo deployment automation (~200 lines)

- **Template changes**: Agent CLAUDE.md files reference `tracker.py` and `git_ops.py` by name. Since those files' public interfaces don't change (only their internal implementation), no template changes are needed.

- **Upgrade steps**: Existing GitHub users upgrading to the version with Forgejo support get the new config fields with GitHub defaults. No action required. The `/squidsquad-upgrade` command adds the `Forge Backend` section to config.md with `Provider: github`.

- **Graceful degradation**: If `forge_adapter.py` is missing (user hasn't upgraded), `tracker.py` continues to call `gh` directly as it does today. The adapter is additive — its absence doesn't break anything. This is the key backward-compatibility guarantee.

- **Breaking changes**: None for existing GitHub users. The `Tracker: github-issues` field in config.md remains valid and maps to `Provider: github`.

## Capability Gaps

- **No `gh` equivalent for Forgejo**: The `gh` CLI is GitHub-only. The forge adapter must implement all needed operations via HTTP. This is the largest piece of new code.

- **No automated Forgejo provisioning**: Setting up a Forgejo instance (create admin, create repo, configure settings) requires scripting against Forgejo's API or its `forgejo admin` CLI. The `forgejo_setup.py` script handles this.

- **No cross-backend migration tooling**: Moving issues from GitHub to Forgejo (or vice versa) is not supported. Users must choose at setup time.

- **No Forgejo webhook support**: SquidSquad's polling-based architecture (agents query the tracker each cycle) means webhooks are not needed. This is actually an advantage — no webhook configuration required on Forgejo.

## Open Questions

- **Q1**: Should the forge adapter use Python `urllib` (stdlib, no dependencies) or `requests` (better ergonomics, requires pip install)? — **Why**: Adding `requests` as a dependency changes SquidSquad's install requirements. Using `urllib` keeps it zero-dependency but makes the adapter code more verbose.

- **Q2**: Should Forgejo deployment be fully automated (wizard runs Docker, creates admin, creates repo, generates token) or guided (wizard tells user what to do step by step)? — **Why**: Full automation is more user-friendly but more fragile (Docker quirks, port conflicts, platform differences). Guided setup is simpler to implement but less "non-technical user friendly."

- **Q3**: Should the config field be `Tracker` (current) or `Forge Backend` (new)? Or both (Forge Backend is the provider, Tracker is the feature set)? — **Why**: Naming affects how users and agents think about the system. `Tracker` implies issue tracking only. `Forge Backend` implies the full git forge (issues + PRs + git hosting). SquidSquad uses all three.

- **Q4**: Should the adapter support Gitea instances in addition to Forgejo? Forgejo is a fork of Gitea and their APIs are 99% identical. — **Why**: Supporting Gitea nearly for free would expand the user base. But the human locked the decision to Forgejo. Gitea support could be a follow-up with minimal effort.

- **Q5**: How should the API token be stored? Options: environment variable (`FORGEJO_TOKEN`), `.squidsquad/.local-config` (gitignored), OS keyring. — **Why**: Security matters. Tokens in config files risk accidental commits. Environment variables are the standard approach but require user setup. `.local-config` is already gitignored and used for clone paths.

- **Q6**: Should the wizard offer to set up Forgejo with a self-signed TLS cert (HTTPS) or plain HTTP? — **Why**: For local-only instances, HTTP is simpler. For network-accessible instances, HTTPS is required. The wizard should probably default to HTTP for local and HTTPS for remote, but this needs confirmation.

## Architecture Diagram

```
Before (current):
  tracker.py  ──→  gh CLI  ──→  GitHub API
  git_ops.py  ──→  gh CLI  ──→  GitHub API (PR ops only)

After (proposed):
  tracker.py  ──→  forge_adapter.py  ──→  gh CLI        ──→  GitHub API
                                     ──→  urllib/HTTP    ──→  Forgejo API
  git_ops.py  ──→  forge_adapter.py  ──→  (same routing)
```

The `forge_adapter.py` reads `Provider` from config.md once at import time and routes all calls to the appropriate backend. Each backend implements the same interface:

```python
class ForgeBackend:
    def list_issues(labels, state, limit) -> list[dict]
    def create_issue(title, body, labels) -> dict
    def edit_labels(number, add=[], remove=[]) -> None
    def view_issue(number, fields) -> dict
    def close_issue(number) -> None
    def add_comment(number, body) -> None
    def create_pr(title, body, head, base, draft) -> dict
    def merge_pr(number, strategy) -> tuple[bool, str]
    def view_pr(number, fields) -> dict
    def create_label(name, color, description) -> None
    def list_labels() -> list[dict]
```

## Recommendation

**Feasible with caveats.**

The architecture is sound. The tracker abstraction via `forge_adapter.py` is clean, backward-compatible, and extends naturally. The main caveats:

1. **The `gh` CLI gap is real work**: Forgejo cannot use `gh`. The adapter must implement ~15 HTTP endpoints directly. This is the bulk of the new code (~400-500 lines).

2. **Forgejo deployment automation is platform-sensitive**: Docker is the cleanest path but not universally available. Binary download works but requires more manual steps. The wizard must handle both gracefully.

3. **Non-technical users are the target audience**: If the goal is non-technical teams, the setup experience must be polished. A half-automated Forgejo setup that requires manual API token generation is worse than no Forgejo support. The wizard should fully automate the happy path (Docker available, port 3000 free, single-user setup).

4. **Testing burden**: Every `tracker.py` function must be tested against both backends. Integration tests against a real Forgejo instance (via Docker in CI) are essential.

**Estimated effort**: 5-7 dev cycles.
- Cycle 1: `forge_adapter.py` core — GitHub backend (wraps existing `gh` calls)
- Cycle 2: `forge_adapter.py` — Forgejo backend (HTTP implementation)
- Cycle 3: Refactor `tracker.py` and `git_ops.py` to use `forge_adapter.py`
- Cycle 4: `forgejo_setup.py` — Docker deployment automation
- Cycle 5: Wizard changes — Step 0c (provider selection), prerequisite check per provider
- Cycle 6: Config.md schema, upgrade path, regression testing
- Cycle 7: End-to-end testing with both backends, documentation
