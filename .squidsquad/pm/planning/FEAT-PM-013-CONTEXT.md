# FEAT-PM-013 Context — Setup Flow Improvements

## Scope

Restructure the SquidSquad setup flow so scripts handle all mechanical work and Claude only handles interactive decisions. The CLI auto-detects project context, pre-fills smart defaults, and Claude asks a minimal set of questions. Scaffolding happens via a single script call inside Claude's session. Install spec is committed for reproducibility and upgrade re-use.

## Locked Decisions (human decided)

- **Scaffold inside Claude**: After interactive questions, Claude calls a single scaffold script (`python references/scripts/scaffold.py --spec .install-spec.json`). Claude can see errors and help debug. No post-Claude external scaffolding.
- **Tarball download**: `npx squidsquad` downloads a single archive instead of 119 individual HTTP requests. 10-30x faster. DM release process produces the tarball via project-specific delivery hook in SOUL.md (not baked into DM template).
- **Commit `.install-spec.json`**: Install spec saved to `.squidsquad/.install-spec.json` and committed. Reproducible — upgrades re-read it to know what was configured. Other devs can see what was chosen.
- **Structured scan summary**: CLI auto-detects project (language, framework, test commands, git remote, CI). Shows grouped findings before questions so user can confirm or correct. Empty repos handled gracefully — all defaults, no errors.
- **CLI handles model routing**: CLI detects available API keys/providers, prompts user interactively in CLI (not Claude). Writes results to config. No Claude involvement for model selection.
- **Build `--yes` mode**: `npx squidsquad --yes` accepts all defaults, skips questions. Good for CI/testing and dogfooding.
- **Always interactive by default**: `--yes` is opt-in, normal flow is always interactive.
- **DM delivery hook is project-specific**: Tarball generation and npm publish are configured per-project in SOUL.md as role customization, not in the generic DM template. DM template handles universal delivery (CHANGELOG, versions, tags). Project-specific steps are role customization.

## Dev Discretion (dev agent can choose)

- CLI framework for interactive prompts (inquirer, readline, etc.)
- Tarball format (tar.gz vs zip — consider Windows)
- Exact scan heuristics (which files to check for language/framework detection)
- scaffold.py internal organization
- Grouping and ordering of scan summary output

## Side Effect Mitigations (required)

- **Empty repo handling**: Scan must not error on empty repos. All fields default gracefully.
- **Partial failure rollback**: If scaffold script fails mid-way, leave partial state and print clear error. Don't delete what was already created — idempotent re-run should fix it.
- **Existing repo detection**: If `.squidsquad/` already exists, scaffold reads `.install-spec.json` and only regenerates what's needed. Never overwrites user customizations (SOUL.md edits, config tweaks) unless explicitly requested.
- **Tarball versioning**: Tarball must match the npm package version. DM delivery hook produces it alongside npm publish.
- **Windows compatibility**: All scripts must work on Windows (paths, line endings, archive extraction).

## Upgrade Path (required)

- **Upgrade = re-scaffold from spec**: `/squidsquad-upgrade` reads `.install-spec.json`, re-runs scaffold with latest templates. User customizations preserved via merge logic (same as today's compose.py).
- **New config values**: `--yes` flag support in CLI. No new config.md fields — install spec is separate.
- **Graceful degradation**: If `.install-spec.json` is missing (old install), upgrade falls back to current behavior. New installs always produce the spec.

## Out of Scope

- Changing the DM template for delivery hooks (that's role customization via SOUL.md)
- Agent selection presets (e.g., "solo dev" vs "full team") — future enhancement
- #361 (project-adaptive souls) — separate task, planned after this

## Integration with Other Tasks

- **#2006**: PR Flow question and post-setup instructions are part of this flow. #2006 can be absorbed or referenced.
- **#2070**: Transport vs behavior principle applies here too — setup scripts are transport, Claude handles behavior (interactive decisions).
- **#361**: Soul seeding at setup time is a natural extension. Design spec format to accommodate it later.
