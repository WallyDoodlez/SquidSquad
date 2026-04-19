# FEAT-SKILL-1389 Context — Self-Hosted Forge Backend (Forgejo)

## Scope

Add Forgejo as an alternative forge backend so non-technical teams can run SquidSquad without GitHub. Implement a `forge_adapter.py` abstraction layer, refactor `tracker.py` and `git_ops.py` to use it, add Forgejo deployment automation to the setup wizard, and add `Forge Backend` config section.

## Locked Decisions (human decided)

- **Forgejo only**: No Gitea support. Follow-up if needed later.
- **Fully automated deployment**: Setup deploys Forgejo via Docker automatically. No guided/manual fallback in v1.
- **Config naming**: `Forge Backend` section in config.md (not `Tracker`, not `Bus`).
- **HTTP for local**: localhost Forgejo uses plain HTTP. Remote instances use HTTPS.
- **urllib for HTTP client**: Zero dependencies. No `requests` package.
- **Token storage**: `~/.squidsquad/secrets` (#1426 dependency). No environment variable contamination.
- **Single provider in setup**: User picks one forge backend. Power users edit config.md for advanced config.
- **Presets are orthogonal**: Team presets define team shape (roles). Forge backend is configured independently during setup.
- **Forgejo provider discovery**: Setup lists available forge backends (like model provider discovery). Adding new backends = adding adapter code.

## Dev Discretion (dev agent can choose)

- Internal structure of `forge_adapter.py` (class hierarchy, method signatures)
- Docker Compose template details (ports, volumes, image version)
- Error handling strategy for Forgejo API failures
- How to detect Docker availability during setup
- Port conflict detection approach

## Side Effect Mitigations (required)

- Existing GitHub users MUST be unaffected. Default `Provider: github` preserves current behavior.
- `tracker.py` public interface (function signatures) MUST NOT change — only internal implementation routes through adapter.
- If `forge_adapter.py` is missing (user hasn't upgraded), `tracker.py` MUST fall back to direct `gh` calls. Backward compatibility guaranteed.
- Agent CLAUDE.md templates reference `tracker.py` by name — no template changes needed since public interface is unchanged.
- `~/.squidsquad/secrets` MUST have restricted permissions: Unix `chmod 600`, Windows `icacls` user-only ACL (remove inheritance, grant current user only).
- Setup MUST verify `~/.squidsquad/` is not inside any git repo before writing secrets.

## Upgrade Path (required)

- `/squidsquad-upgrade` adds `Forge Backend` section to config.md with defaults: `Provider: github`, `Endpoint: https://api.github.com`.
- No breaking changes. Existing `Tracker: github-issues` field remains valid and maps to `Provider: github`.
- New files (`forge_adapter.py`, `forgejo_setup.py`, docker-compose template) are additive.

## Out of Scope

- Gitea support (follow-up)
- Cross-backend migration tooling (GitHub ↔ Forgejo issue migration)
- Forgejo webhook support (SquidSquad uses polling, not webhooks)
- Multi-forge support (one forge per project)
- HTTPS for local Forgejo
- Binary download fallback (Docker only in v1)
- Encrypted secrets
