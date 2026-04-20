# FEAT-SKILL-1778 Research — Project-Specific Role Responsibilities

## Summary

This task redesigns the SquidSquad setup flow to: (1) move all mechanical steps into the CLI so no LLM token spend is needed for prerequisite checks, file fetching, or model routing; (2) add a `repo_scan.py` script that auto-detects the project's tech stack, CI, tests, and deploy targets; (3) add a "Project-Specific Responsibilities" section to each role's SOUL.md, seeded from scan results; (4) add model routing (API key management) to the CLI; (5) merge wizard steps to reduce redundancy.

The codebase is well-structured for this change. The CLI (`packages/cli/index.js`) already handles prerequisites and file fetching. The wizard (`references/wizard/WIZARD.md`) is a 7-step prose runbook. SOUL.md templates all end with a `### Project Context` section containing a placeholder stub. The scaffolder (`wizard.py scaffold`) already seeds `### Project Context` from the install spec's `domain_context` field. The main gap is: there is no automated repo scanning, no per-role responsibility mapping, and the CLI does not handle model routing or loop configuration.

Recommendation: **Feasible with caveats.** The repo scan and responsibility mapping are net-new functionality but well-scoped. The CLI changes are additive. The main risk is the wizard step merge — Steps 1+1b (project identity + scan review) must preserve the adaptive questioning flow while integrating scan results. The SOUL.md seeding path through `scaffold_install` already exists and handles the `### Project Context` placeholder, so adding `### Project-Specific Responsibilities` follows the same pattern.

## Vault Context

- **BRIEFING.md priorities**: Going public focus, v1.0.0 launch
- **Related decisions**: Sub-skill directory for external capabilities, marketplace as test project
- **Human preferences**: Agents are manually triggered, sub-skills live in separate repos
- **Related patterns**: tracker.py abstraction layer, wizard.py mechanical helpers pattern

## Impact Analysis

### Files Touched

| File | Change Type | Scope |
|------|-------------|-------|
| `references/scripts/repo_scan.py` | **New file** | Detect tech stack, CI, tests, deploy targets from repo files |
| `references/wizard/WIZARD.md` | **Major rewrite** | Merge steps, add scan review, add responsibility seeding, remove steps moved to CLI |
| `packages/cli/index.js` | **Major enhancement** | Add steps: shared FS init, re-run detection, repo scan, model routing, loop config, commit |
| `references/scripts/wizard.py` | **Moderate** | Add `seed-responsibilities` command, update `scaffold` to write responsibilities to SOUL.md |
| `references/roles/*/SOUL.md` | **Minor** | Add `### Project-Specific Responsibilities` placeholder section to all 5 templates |
| `references/scripts/compose.py` | **Minor** | `deploy_role` may need to handle new SOUL.md section during scaffold |
| `references/scripts/model_router.py` | **No change** | Already exists with list-providers, setup-provider, validate commands |
| `references/scripts/shared_fs.py` | **No change** | Already exists with init command |

### Behavior Changes

- **CLI gains 4 new steps** (repo scan, model routing, loop config, commit) — all mechanical, no LLM needed
- **Wizard loses 3 steps** moved to CLI (prerequisites, shared FS, loop interval) and gains 1 new merged step (project identity + scan review)
- **SOUL.md gets a new section** (`### Project-Specific Responsibilities`) seeded per-role based on detected tech stack
- **Existing installs** are unaffected until they run `/squidsquad-upgrade`, which would need to add the new section

## Research Area 1 — Current Wizard Flow

The wizard (WIZARD.md) has 7+2 steps:

| Step | What it does | Mechanical or LLM? |
|------|-------------|---------------------|
| 0 — Prerequisites | `wizard.py check-gh` | Mechanical |
| 0a — Shared FS | `shared_fs.py init` | Mechanical |
| 0b — Re-run detection | `wizard.py check-existing` + 3-way prompt | Mechanical check, LLM for prompt |
| 1 — Project details | `wizard.py repo-info` + name validation | Mechanical check, LLM for conversation |
| 1b — Adaptive context | 3-5 questions about project | Pure LLM |
| 2 — Intent + roster | Intent classifier + role selection | Pure LLM |
| 3 — Preset confirm | Pipeline render + confirmation | LLM conversation |
| 4 — Setup requirements | Manifest-driven walker per role | LLM + `manifest.py` calls |
| 5 — Loop interval | Ask interval + threshold | LLM conversation (trivially mechanical) |
| 5b — Model routing | Provider discovery + key setup | Mechanical + LLM conversation |
| 5c — Forge backend | Docker check + deploy | Mechanical + LLM conversation |
| 6 — Review screen | Summary table + [P/V/E/A] actions | LLM rendering |
| 7 — Commit and write | `wizard.py scaffold` + labels + git | Mechanical |

**Steps that can move to CLI (no LLM needed):**
- Step 0 (prerequisites) — CLI already does this
- Step 0a (shared FS) — one shell command
- Step 0b re-run detection — CLI already checks for `.squidsquad/` existence
- Step 5 (loop interval) — simple numeric input, can be CLI prompt
- Step 5b (model routing) — provider discovery + editor open
- Step 7 commit portion — git add/commit/push

**Steps that remain in wizard (need LLM):**
- Step 1 + 1b (project identity + adaptive context) — can be merged with scan review
- Step 2 (intent + roster) — intent classification needs LLM
- Step 3 (preset confirmation) — simple but conversational
- Step 4 (setup requirements) — manifest-driven but needs adaptive conversation
- Step 6 (review screen) — rendered by LLM
- Step 7 scaffold — called by LLM after review

## Research Area 2 — Current CLI

`packages/cli/index.js` currently does:

1. Banner display
2. Git repo check (`checkGitRepo`)
3. Already-installed check (exits if `.squidsquad/` exists)
4. Prerequisites: Node 18+, Python 3.8+, gh CLI + auth, Claude CLI
5. File fetching from GitHub (`installFiles` via `installer-files.txt` manifest)
6. Git commit of fetched files
7. Ask to launch Claude with `/squidsquad-setup`
8. Launch Claude

**New steps slot in between steps 6 and 7:**
- After file fetching and commit (step 6), the repo scan script is available locally
- repo_scan.py runs against the repo
- Model routing: `model_router.py list-providers`, interactive provider/model selection, key setup
- Loop interval: simple readline prompt for minutes + threshold
- Second commit with scan results stored somewhere accessible to the wizard
- Then launch Claude

**Key architectural insight**: The CLI uses `execSync` for mechanical steps and `readline` for interactive prompts. Adding repo scan, model routing prompts, and loop config fits this pattern cleanly.

## Research Area 3 — SOUL.md Templates

All 5 role SOUL.md templates share an identical structure:

```markdown
## Soul — [Role Name]

### Professional Identity
### Quality Bar
### Decision-Making Style
### Communication Style
### Boundaries
### Collaboration Posture
### Improvement Scan
### Project Context
_Populated during setup. Describes what this project does, its tech stack, conventions, and key tools._
```

The `### Project Context` section is the last section in every template and contains a placeholder stub. The scaffolder (`wizard.py scaffold_install`) replaces this stub with the `domain_context` from the install spec.

**Where `### Project-Specific Responsibilities` fits:**
- Should go between `### Improvement Scan` and `### Project Context`
- Or as a subsection within `### Project Context`
- Recommendation: **New section `### Project-Specific Responsibilities`** after `### Project Context` — keeps it distinct and scannable

**Current seeding mechanism** (in `wizard.py` `scaffold_install`, lines 786-797):
```python
placeholder = "_Populated during setup. Describes what this project does..."
if placeholder in soul_text:
    soul_text = soul_text.replace(placeholder, domain_ctx)
```

The same pattern works for responsibility seeding: add a placeholder in the template, replace it during scaffold.

## Research Area 4 — repo_scan.py Scope

### File Patterns to Detect

**Language/Framework markers:**

| File | Detects |
|------|---------|
| `package.json` | Node.js ecosystem; parse for framework (next, react, vue, angular, express, fastify) |
| `pnpm-lock.yaml` / `yarn.lock` / `package-lock.json` | Package manager |
| `requirements.txt` / `pyproject.toml` / `setup.py` / `Pipfile` | Python ecosystem |
| `Cargo.toml` | Rust |
| `go.mod` | Go |
| `pom.xml` / `build.gradle` / `build.gradle.kts` | Java/Kotlin |
| `Gemfile` | Ruby |
| `composer.json` | PHP |
| `*.csproj` / `*.sln` | .NET/C# |
| `mix.exs` | Elixir |
| `pubspec.yaml` | Dart/Flutter |

**CI/CD markers:**

| File/Dir | Detects |
|----------|---------|
| `.github/workflows/*.yml` | GitHub Actions |
| `Jenkinsfile` | Jenkins |
| `.gitlab-ci.yml` | GitLab CI |
| `.circleci/config.yml` | CircleCI |
| `.travis.yml` | Travis CI |
| `azure-pipelines.yml` | Azure DevOps |
| `bitbucket-pipelines.yml` | Bitbucket Pipelines |

**Test markers:**

| File | Detects |
|------|---------|
| `jest.config.*` / `jest` in package.json | Jest |
| `vitest.config.*` / `vitest` in package.json | Vitest |
| `pytest.ini` / `pyproject.toml [tool.pytest]` / `conftest.py` | pytest |
| `*.test.ts` / `*.spec.ts` patterns | TypeScript tests |
| `.mocharc.*` | Mocha |
| `karma.conf.*` | Karma |
| `cypress.config.*` / `cypress/` | Cypress (E2E) |
| `playwright.config.*` | Playwright (E2E) |

**Deploy targets:**

| File | Detects |
|------|---------|
| `Dockerfile` / `docker-compose.yml` | Docker |
| `vercel.json` / `.vercel/` | Vercel |
| `netlify.toml` | Netlify |
| `fly.toml` | Fly.io |
| `railway.json` / `railway.toml` | Railway |
| `render.yaml` | Render |
| `app.yaml` (GCP) | Google Cloud App Engine |
| `serverless.yml` | Serverless Framework |
| `terraform/` / `*.tf` | Terraform |
| `k8s/` / `kubernetes/` / `*.k8s.yml` | Kubernetes |

**Other markers:**

| File/Dir | Detects |
|----------|---------|
| `.storybook/` | Storybook (component library) |
| `docs/` / `mkdocs.yml` / `docusaurus.config.js` | Documentation site |
| `openapi.yaml` / `swagger.yaml` / `openapi.json` | API spec |
| `.eslintrc.*` / `eslint.config.*` | ESLint (linting) |
| `.prettierrc.*` | Prettier (formatting) |
| `tsconfig.json` | TypeScript |
| `tailwind.config.*` | Tailwind CSS |
| `prisma/schema.prisma` | Prisma ORM |
| `drizzle.config.*` | Drizzle ORM |
| `.env.example` | Environment variables pattern |

### Output Format

```json
{
  "languages": ["typescript", "python"],
  "frameworks": ["next.js", "fastapi"],
  "package_managers": ["pnpm", "pip"],
  "test_runners": ["jest", "pytest"],
  "test_commands": {"unit": "pnpm test", "e2e": "pnpm cypress"},
  "ci": ["github-actions"],
  "deploy_targets": ["vercel", "docker"],
  "has_api_spec": true,
  "has_docs": true,
  "has_storybook": false,
  "linting": ["eslint", "prettier"],
  "orm": "prisma",
  "monorepo": false,
  "project_type": "web-app"
}
```

## Research Area 5 — Responsibility Mapping Table

For each detected technology, which role gets which project-specific responsibility:

### PM Responsibilities (by detection)

| Detection | Responsibility |
|-----------|---------------|
| GitHub Actions CI | Monitor CI status in PRs; block shipping on red CI |
| API spec (openapi/swagger) | Ensure new endpoints are documented in the API spec |
| Monorepo | Coordinate cross-package changes; track dependency graph |
| Multiple deploy targets | Coordinate staged rollouts across environments |
| E2E tests present | Include E2E pass/fail in verification gate |

### Dev Responsibilities (by detection)

| Detection | Responsibility |
|-----------|---------------|
| TypeScript + tsconfig | All new code must be TypeScript; maintain strict mode |
| Jest/Vitest | Write unit tests for all new functions; maintain >80% coverage |
| pytest | Write pytest tests for all new modules; use fixtures |
| ESLint + Prettier | Run lint+format before committing; fix all warnings |
| Prisma/Drizzle ORM | Database changes go through migrations; never raw SQL |
| Tailwind CSS | Use Tailwind utility classes; avoid custom CSS unless necessary |
| Docker | Ensure Dockerfile builds cleanly after changes |
| Next.js | Follow app router conventions; use server components where possible |
| FastAPI | Use Pydantic models for all request/response; type all endpoints |
| Monorepo | Scope changes to the correct package; update shared deps carefully |
| API spec present | Update openapi.yaml when adding/changing endpoints |

### Designer Responsibilities (by detection)

| Detection | Responsibility |
|-----------|---------------|
| Tailwind CSS | Design specs must use Tailwind's spacing/color scale |
| Storybook | New components need Storybook stories in design spec |
| Design tokens detected | Reference existing tokens; propose new ones through the system |
| React/Vue/Angular | Component specs must map to framework component boundaries |

### QA Responsibilities (by detection)

| Detection | Responsibility |
|-----------|---------------|
| Jest/Vitest | Run unit test suite and verify no regressions |
| pytest | Run pytest suite and verify no regressions |
| Cypress/Playwright | Run E2E suite as part of verification |
| ESLint | Verify zero lint warnings in changed files |
| TypeScript strict | Verify no type errors in changed files |
| Docker | Verify Docker build succeeds after changes |
| API spec present | Verify API responses match spec |

### DM Responsibilities (by detection)

| Detection | Responsibility |
|-----------|---------------|
| Vercel/Netlify | Trigger preview deploy for PR review; verify production deploy |
| Docker + K8s | Include deployment steps in delivery notes |
| Docs site (mkdocs/docusaurus) | Update docs site when user-facing features ship |
| CHANGELOG present | Maintain CHANGELOG.md in Keep a Changelog format |
| API spec present | Ensure API changelog accompanies endpoint changes |
| npm package (package.json has "main") | Version bump follows semver; publish to npm |

### Implementation Approach

The mapping should be a static dict in `repo_scan.py` (or a companion `responsibility_map.py`):

```python
RESPONSIBILITY_MAP = {
    "pm": {
        "github-actions": "Monitor CI status in PRs; block shipping on red CI",
        "openapi": "Ensure new endpoints are documented in the API spec",
        ...
    },
    "dev": {
        "typescript": "All new code must be TypeScript; maintain strict mode",
        ...
    },
    ...
}
```

The wizard reads the scan output, looks up each detection in the map, and collects per-role responsibility lists. These get written to each role's SOUL.md during scaffold.

## Research Area 6 — wizard.py Capabilities

Key helpers that exist and are reusable:

- `check_gh()` — Step 0 prerequisite check
- `detect_existing_install()` — Step 0b re-run detection
- `validate_rerun_action()` — re-run action normalization
- `get_repo_info()` — Step 1 repo metadata (gh + git fallback)
- `project_name_default()` — name inference
- `is_valid_project_name()` — name validation
- `validate_interval()` — loop interval validation (Step 5)
- `build_config_md()` — config.md writer from install spec
- `scaffold_install()` — full `.squidsquad/` tree writer
- `ensure_labels()` — GitHub label seeding

**New helper needed**: `seed_responsibilities(spec, scan_results)` — takes the install spec and scan output, returns a dict mapping role_id to a markdown string of project-specific responsibilities. This gets consumed by `scaffold_install` to write into SOUL.md.

## Research Area 7 — Manifest System

Role manifests (`references/roles/*/manifest.yaml`) define:
- `id`, `display_name`, `tagline`, `description`
- `show_in_roster`, `always_installed`, `iteration_mode`
- `soul_template`, `claude_template` — file paths relative to role dir
- `routes_to` — hand-off targets
- `requires_sub_skills` — capability dependencies
- `setup_requirements` — per-install questions

Responsibilities are NOT in manifests currently. Two options:
1. **Add to manifests** — a new `scan_responsibilities` field mapping detection keys to responsibility strings
2. **Separate mapping file** — `repo_scan.py` or `responsibility_map.py` owns the mapping

Recommendation: **Separate mapping file.** Manifests are the role's public contract (Q-new14, domain-only language). Responsibility mappings are implementation detail of the setup flow. A static Python dict in `repo_scan.py` keeps the scanning and mapping co-located.

## Research Area 8 — Side Effects / What Breaks

### Wizard Step Merge Impact

The locked design merges Steps 1+1b into a single "project identity + scan review" step. The current Step 1b (adaptive context questions) asks 3-5 questions to populate `project.description`, `project.domain_context`, and seed SOUL.md. With repo scan, many of these answers come from file detection instead.

**Risk**: If the scan misdetects (e.g., finds `package.json` but the project is actually a Python backend that happens to have a JS build tool), the seeded responsibilities will be wrong.

**Mitigation**: The merged step presents scan results to the user for review ("I detected: TypeScript, Next.js, Jest, Vercel. Is this right?"). The user can correct before proceeding.

### CLI Step Ordering

Moving model routing to CLI means it happens BEFORE the wizard. The wizard currently handles model routing at Step 5b. If the CLI handles it, the wizard must NOT re-ask.

**Mitigation**: Store model routing config in a temp file or pass it through to the wizard's launch. The CLI writes `--model-routing` data to a JSON file the wizard reads at startup.

### Existing Installs

Existing `.squidsquad/*/SOUL.md` files will NOT have the `### Project-Specific Responsibilities` section. The scaffolder never overwrites SOUL.md (by design — it may contain user customizations).

**Impact**: Existing installs continue working with generic SOUL.md. The new section is additive.

### Template Refresh on Upgrade

`/squidsquad-upgrade` regenerates CLAUDE.md but preserves SOUL.md. A new upgrade path would need to:
1. Detect missing `### Project-Specific Responsibilities` section
2. Run repo scan
3. Append the section

This is a separate upgrade task, not part of the initial implementation.

## Research Area 9 — Edge Cases

### Empty Repos (No Code Yet)

- Scan returns empty results for all categories
- Responsibilities section would be: "No tech stack detected yet. Re-run setup after adding code."
- The wizard should handle this gracefully — skip the scan review substep if nothing was detected

### Monorepos

- Multiple `package.json`, `pyproject.toml` etc. at different paths
- Scan should detect the root-level markers AND scan one level of subdirectories
- Responsibilities may differ per package — but SquidSquad v1 treats the whole repo as one project
- Recommendation: scan the root + immediate subdirs, report the union of all detected tech

### Non-Standard Structures

- Custom build tools (Bazel, Buck, Pants) — scan won't detect these
- Vendored dependencies (e.g., `vendor/` with their own `package.json`) — exclude common vendor paths
- Generated files — exclude `dist/`, `build/`, `out/`, `node_modules/`, `.git/`

### Projects with No CI

- Scan reports `ci: []`
- PM responsibility for CI monitoring is omitted
- QA responsibilities fall back to local test commands only

### Projects with No Tests

- Scan reports `test_runners: []`
- Dev responsibility to "write tests" becomes generic: "Add a test framework appropriate for the stack"
- QA verification relies on manual checks rather than test suite

## Research Area 10 — Upgrade & Migration

### New Config Values

- `scan_results` — stored in config.md or as a separate file? Recommendation: separate file `.squidsquad/scan-results.json` so the wizard can re-read it without parsing config.md
- No new config.md fields needed — responsibilities live in SOUL.md, not config

### New Files

- `references/scripts/repo_scan.py` — new script
- `.squidsquad/scan-results.json` — scan output (generated at install time)
- Updated `references/roles/*/SOUL.md` — new placeholder section

### Template Changes

- All 5 SOUL.md templates gain `### Project-Specific Responsibilities` section with placeholder
- WIZARD.md rewritten with merged steps
- CLI `index.js` gains new step functions

### Upgrade Steps

- `/squidsquad-upgrade` should detect missing `### Project-Specific Responsibilities` in SOUL.md
- Run `repo_scan.py` against the repo
- Append the new section to each role's SOUL.md
- This is a separate follow-up task — initial implementation only covers fresh installs

### Graceful Degradation

- Existing installs without the new section: **no breakage** — SOUL.md works without it
- Existing installs running old CLI: **no breakage** — old CLI still works, just doesn't scan
- Old wizard with new CLI: **potential issue** if CLI writes scan results the old wizard doesn't expect — mitigate by making scan results optional (wizard checks for file existence)

## Open Questions

- **Q1**: Should scan results persist in `.squidsquad/scan-results.json` or be ephemeral (passed to wizard via temp file)? Persisting allows re-scan on upgrade. Ephemeral is cleaner.
  - **Why**: Affects upgrade story and whether users can manually edit detected tech.

- **Q2**: Should the responsibility map be exhaustive (cover every possible detection) or minimal (top 10-15 common stacks)?
  - **Why**: Exhaustive = more maintenance. Minimal = covers 90% of users. Unknown detections get no responsibilities (graceful).

- **Q3**: How should the CLI pass scan results + model routing config to the wizard session?
  - **Why**: CLI runs before Claude launches. Options: temp JSON file, environment variable, command-line argument to Claude.

- **Q4**: Should the wizard still ask adaptive context questions (Step 1b) if the scan already detected the tech stack?
  - **Why**: Scan covers tech stack but not project purpose, domain context, or conventions. Adaptive questions may still be needed for non-technical context.

## Recommendation

**Feasible with caveats.** The core changes (repo_scan.py, responsibility mapping, SOUL.md seeding) are well-scoped and follow existing patterns. The CLI enhancement is additive. The wizard step merge requires careful attention to the adaptive questioning flow.

Key caveats:
1. Upgrade path for existing installs should be a separate follow-up task
2. The responsibility map should start minimal (top 15 detections) and grow based on user feedback
3. Scan results should persist in `.squidsquad/scan-results.json` so upgrades can re-seed
4. CLI-to-wizard data handoff needs a clean mechanism (recommend temp JSON file)
