# Working State

- **Task**: #328
- **Status**: in-progress
- **Started**: 2026-04-11 14:39
- **Quiet Cycle Counter**: 0

## Feature

FEAT-328 — Intent-driven setup wizard with role manifest registry.

This is a multi-cycle feature (~2000 lines of spec). I'm executing it in
discrete phases, each landing as its own atomic commit.

## Phase Plan

- [x] **Phase A — Role manifest files** (commit 1620094)
  - 5 YAML files under `references/roles/<role>/manifest.yaml`
  - Pure data, no code changes, no risk to existing flow
  - Domain-only language per Q-new14
  - Topology matches CONTEXT.md final inventory table (line 702)
- [x] **Phase A.1 — `always_installed` schema addition** (this cycle)
  - Anticipates #347 (Separate PM from QA) per PM's comment hint on #328
  - pm/dm: `always_installed: true`; designer/dev/qa: `false`
  - v1 invariant: `always_installed == !show_in_roster` (but both fields
    kept because they mean different things conceptually)
- [x] **Phase B — Tool registry** (commit 5f315c8)
  - `references/tools/{figma,google_stitch,local_html,local_delivery}/`
  - Each with `manifest.yaml`, `setup.md`, `sub-skill.md`
  - 3 designer tools + 1 DM tool
  - Cross-references validated: every role's `requires_tools` ID resolves
- [x] **Phase C — Preset manifests** (this cycle)
  - `references/presets/{software-dev,design}/manifest.yaml`
  - Declares `role_install_order` (PM/DM implicit)
- [x] **Phase D — Validator (`references/scripts/manifest.py`)** (this cycle)
  - Schema validation (fields, types, schema_version, iteration_mode,
    provider, category, etc.)
  - Cross-reference (routes_to targets exist; requires_tools IDs exist;
    preset role_install_order entries exist and are not always_installed;
    tool applicable_roles entries exist)
  - Tool sub_skill + setup.md file-existence checks
  - Domain-only linter for Q-new14 (rejects mentions of `config.md`,
    `.squidsquad`, `CLAUDE.md`, `SOUL.md`, `sub-skill`, internal script paths)
  - **Cycle detection INTENTIONALLY OMITTED** — v1 topology locks bidirectional
    PM ↔ Designer routing (Q1 + Q7), which the spec's side-effect mitigation
    didn't anticipate. `routes_to` is a per-item hand-off preference, not a
    flow DAG, so graph cycles are legitimate. Documented in manifest.py
    module docstring.
  - CLI: `validate`, `list <kind>`, `load <kind> <id>`, `resolve <preset>`
  - tests/test_manifest_registry.py — 35 tests covering happy path, shipped
    smoke, schema errors per kind, cross-references, domain-only linter,
    YAML errors, Issue formatting. Uses tmp_path fixtures for negative tests,
    real registry for smoke test.
- [x] **Phase E — Status label additions (additive only)** (this cycle)
  - Added `pending-human-approval`, `pending-human-review`, `pending-human-setup`
    to STATUS_LABELS, LEGAL_TRANSITIONS, and ROLE_AUTHORITY
  - Created the three labels on GitHub via `gh label create` (with
    domain-appropriate colours and descriptions)
  - Updated test_labels.py EXPECTED_STATUS_LABELS to include the three new
    labels so future drift is caught by the live GitHub check
  - 16 new unit tests in test_tracker_authority.py:
    - `TestPendingHumanApproval` — PM owns intake edges, others rejected
    - `TestPendingHumanReview` — assignee drives self-pause + redirect +
      approve; PM cannot bypass assignee on HITL approval
    - `TestPendingHumanSetup` — assignee self-pauses, PM resumes; worker
      cannot resume own setup (forces actual infra change before continuing)
    - `TestPhaseECoverage` — legal/authority invariant still holds after
      additions; STATUS_LABELS map includes new short names; old `pending`
      label remains legal (additive phase guarantee)
  - `pending` NOT yet removed — migration happens in Phase I
- [x] **Phase F — Role template migration (Q-new22)** (this cycle)
  - Migrated 10 files via `git mv` to preserve history:
    - 5 souls from `references/sub-skills/souls/*.md` → `references/roles/<role>/SOUL.md`
    - 5 role templates from `references/sub-skills/roles/*.md` → `references/roles/<role>/CLAUDE.md`
  - Retired `pm-lean.md` and its 4 supporting lean-* sub-skills (option B —
    no longer needed; setup_requirements will drive variant selection)
  - Removed empty `references/sub-skills/souls/` and `.../roles/` directories
  - Added `soul_template` + `claude_template` fields to all 5 role manifests
    (relative to the role's own directory)
  - Validator now requires both fields and checks the files exist on disk
  - `compose.py`: entry files come from `references/roles/<role>/CLAUDE.md`;
    SOUL.md copied verbatim from `references/roles/<role>/SOUL.md`;
    dispatch table replaced with simple "known roles" set; dev variants
    (skill/fe/be) resolve to the `dev` role identity
  - `sub-skills/manifest.md` updated: inventory tree drops `souls/` and
    `roles/` branches; composition-order sections point at the new
    `references/roles/<role>/CLAUDE.md` entry-file paths
  - Added defensive tests: legacy dirs must not reappear, legacy include
    namespaces must not be referenced in manifest.md
  - Full static suite: 218/218 pass (was 208, +10)
- [~] **Phase G — Wizard implementation** (was Phase F before Q-new22 arrived)
  - [x] **Phase G.1 — Wizard helpers: Step 0 / 0b / 1** (this cycle)
    - references/scripts/wizard.py: check-gh, check-existing,
      validate-rerun-action, repo-info, project-name-default,
      validate-name — all JSON-output CLI commands
    - Architecture: Python helpers own mechanical pieces; prose runbook
      (future cycle) owns LLM-driven pieces (intent classification,
      setup_requirements walker, natural conversation)
    - Q8 re-run action parser: "", "1"/"2"/"3", "a"/"r"/"f", full names,
      case-insensitive, None → default "abort"
    - Git slug parser: HTTPS / SSH / ssh:// forms; rejects non-GitHub
    - get_repo_info: gh primary → git fallback → none (structured result
      with `source` field so the prose runbook can explain its data source)
    - project_name_default: gh name → cwd basename; invalid gh names
      (contain spaces, slashes, etc.) fall through to dirname
    - tests/test_wizard.py: 68 unit tests, ALL subprocess calls stubbed
      via monkeypatched wizard._run — zero real gh/git invocations
  - [~] **Phase G.2 — Wizard helpers: writers + scaffolder + labels**
    - [x] **Phase G.2a — config.md writer (Q-new17 schema)** (this cycle)
      - wizard.py: build_config_md(spec) → deterministic text
      - CLI: `wizard.py build-config-md <spec.json|->` for integration use
      - Architecture Version bumped to 2 in the new-schema header
      - Section order: Project → Preset → Agents → Tools → Loop → Flags
        (matches TC-06 exactly)
      - Agent nested-field order is deterministic regardless of dict
        insertion: role → variant → iteration_mode → stack → test_command
      - Values with spaces/commas/colons/hashes auto-quoted
      - Deferred tool placeholder: `(unset — PM will configure on first use)`
      - Flags sorted alphabetically, rendered yes/no for booleans
      - 53 new tests covering: section order, determinism, header version,
        project description optional, alias defaults to id, designer with
        iteration_mode + setup block, dev variant + stack + test_command,
        multiple dev agents share role, nested field ordering, empty
        field omission, setup block omitted when empty, missing id/role
        errors, non-dict agent errors, 6 missing top-level sections,
        tools placeholder variants, loop defaults, flags sort order,
        TC-01 full regression, 11 parametrized quote rules, 5 flag labels
    - [x] **Phase G.2b — `.squidsquad/` folder scaffolder** (this cycle)
      - wizard.scaffold_install(spec, target_root, overwrite_existing=False)
      - Calls compose.deploy_role per installed agent for CLAUDE.md + SOUL.md
      - Creates working-state.md (default template), iterations/, planning/
      - Writes composed config.md (calls G.2a)
      - Refuses to clobber existing install unless overwrite_existing=True
      - Even with overwrite, SOUL.md and working-state.md are preserved —
        user customisations and in-progress state are never lost
      - CLAUDE.md IS refreshed on overwrite so template bug fixes land
      - Refactored compose.deploy_role to accept optional target_root
        (defaults to REPO_ROOT — existing callers unchanged)
      - **Side-effect fix**: compose._read_config_value now catches
        SystemExit too. Previously it caught Exception but config.py
        calls sys.exit(1) on missing fields, which SystemExit inherits
        from BaseException, bypassing the guard. Dev variant scaffolds
        were hard-exiting the whole process. Now degrades to "" correctly.
      - 16 new unit tests in tests/test_wizard.py, all against tmp_path —
        nothing touches the real .squidsquad/ install
      - Full static suite: 355/355 pass (was 339, +16)
    - [x] **Phase G.2c — Label migration + creation** (this cycle)
      - `build_label_inventory()` — derives canonical label list from
        tracker.py STATUS_LABELS + TYPE_LABELS + PRIORITY_LABELS +
        SEVERITY_LABELS + DESIGN_LABELS + SPECIAL_LABELS (drift-proof)
      - `list_gh_labels()` — parse `gh label list --json name`
      - `ensure_labels(dry_run=False)` — idempotently create any missing
        labels with deterministic descriptions and colors; treats race
        "already exists" errors as existing; reports failures per label
      - `list_issues_with_label(label, state)` — parse `gh issue list --label`
      - `migrate_label(old, new, dry_run=False)` — walks every issue
        carrying `old` and rewrites the label via single `gh issue edit`
        command with both --remove-label and --add-label; counts
        skipped (already had the label) separately from failed
      - 3 new CLI commands: `ensure-labels [--dry-run]`,
        `list-issues-by-label <label>`, `migrate-label <old> <new>`
      - 21 new unit tests — all gh calls mocked via wizard._run monkey-
        patch; zero real gh invocations. Coverage includes: inventory
        drift-proofing, missing-label creation, dry-run non-calling,
        race-condition handling, API failure fallback, migration happy
        path, per-issue partial-failure reporting, already-labelled
        skip path
      - Full static suite: 376/376 pass (was 355, +21)
- [x] **Phase G.2 — Wizard helpers: writers + scaffolder + labels** — all three
  subphases shipped.
  - [x] **Phase G.3 — Prose runbook** (this cycle)
    - references/wizard/WIZARD.md — step-by-step runbook Claude follows
    - Covers 8 wizard steps: 0 (gh prereq) → 0b (re-run) → 1..7
    - Q-new18 intent classifier prompt embedded verbatim
    - Q-new15 specialist roster (conversational, no menus)
    - Q-new13 manifest-driven setup_requirements walker
    - Q-new19 per-agent answer parsing from single user exchange
    - Q-new17 config.md schema (via build_config_md)
    - Review screen (P/V/E/A) with preview via wizard.py helpers only —
      never touches real .squidsquad/ during preview
    - Installer agent lifecycle (Q-new21): ephemeral, exits at 7.6,
      no self-loop, no --force (human-only escape hatch)
    - Domain-only language rules (Q-new14) with tone guidance
    - Error recovery path with retry-or-abort per step
    - 23 new static tests in tests/test_wizard_runbook.py that enforce:
      - all 8 steps present in order
      - every wizard.py/manifest.py/compose.py command mentioned exists
        as a real subcommand (drift-proof)
      - critical helpers are explicitly called (check-gh, scaffold, etc.)
      - referenced presets and roles exist in the registry
      - no disk writes before Step 7 (explicit prohibition)
      - Step 7.6 has ephemeral exit instruction
      - Review screen has all 4 actions [P/V/E/A]
      - Preview uses dry-run helpers, not real writes
      - No --force flag in installer body
      - All 6 critical Q-new locks cited with their context word
    - Full static suite: 399/399 pass (was 376, +23)
  - [x] **Phase G.4 — SKILL.md rewrite + /squidsquad-setup slash command** (this cycle)
    - SKILL.md: replaced 605-line inline Setup Instructions (Steps 0-9
      + config.md template) with a 42-line pointer at
      references/wizard/WIZARD.md, describing the helper scripts and
      registry layout. Architecture section left intact.
    - Fixed 3 dangling "Step 4b in Setup Instructions" refs in the
      Upgrade Instructions section — now point at
      `compose.py deploy <role>` which is the actual canonical path.
    - packages/cli/index.js: npx squidsquad now fetches BOTH SKILL.md
      and references/wizard/WIZARD.md from the main branch, places
      them at their canonical paths in the target repo, and commits
      both as seed files.
    - .claude/commands/squidsquad-setup.md (seeded by CLI) rewritten
      to instruct Claude to read WIZARD.md (not SKILL.md's Setup
      Instructions section), cites the installer-agent lifecycle
      (ephemeral, no writes before Step 7, exits at 7.6), and
      authorises on-demand gh api / curl fetches for scripts and
      manifests.
    - 17 new tests in tests/test_installer_wiring.py enforcing
      three-way consistency:
      - SKILL.md Setup is present, points at runbook, is concise
        (<150 lines), has no legacy step headings, every
        references/... path it cites actually exists, no Step 4b
        refs remain
      - packages/cli/index.js fetches both files, writes runbook to
        canonical path, commits both, slash command points at
        runbook not SKILL.md Setup, mentions ephemeral installer,
        mentions "no writes before Step 7", prereq checks intact
      - references/wizard/WIZARD.md exists and is non-trivial
    - Full static suite: 416/416 pass (was 399, +17)
- [x] **Phase G — Wizard implementation** COMPLETE
      (G.1 helpers + G.2 writers/scaffolder/labels + G.3 runbook + G.4 wiring)
- [ ] **Phase H — compose.py + config.py deeper manifest refactor**
  - Phase F did the template migration. Remaining: drive the compose
    pipeline entirely from manifests (currently compose.py still has a
    hardcoded `known_roles` set)
  - Preserve backward compatibility for existing config.md files
- [ ] **Phase H — statusline.sh manifest-aware**
  - Read installed roles from manifest, not hardcoded list
- [ ] **Phase I — Migration script** (`migrate_status_labels.py`)
  - Rewrite `pending` → `pending-human-approval` on all issues
  - Transition window: both old and new accepted
  - After verification, drop `pending` from LEGAL_TRANSITIONS
- [ ] **Phase J — Tests**
  - Per TEST-PLAN.md — schema validation, resolver, wizard state, migration idempotency

## Completed Steps

- Read RESEARCH.md, CONTEXT.md (partial), TEST-PLAN.md (partial), PHASE2-PREP
- Picked up #328, transitioned to in-progress
- Wrote 5 role manifests (Phase A complete)
- Validated all 5 parse with PyYAML
- Ran full static test suite — 157 pass, no regressions

## Key Decisions (dev discretion, recorded for next-cycle context)

- **Manifest schema fields**: `schema_version`, `id`, `display_name`, `tagline`,
  `description`, `show_in_roster`, `iteration_mode`, `routes_to`,
  `requires_tools`, `setup_requirements`. All locked decisions honored.
- **Tool ID convention**: short name matching the tool folder (`figma` not
  `figma_mcp`). The `mcp_name` field inside the tool manifest maps to the
  actual MCP server — but role-level `requires_tools` uses the short form,
  per Q-new5's worked example.
- **Empty `requires_tools: {}` vs omission**: always present as a dict,
  possibly empty. Simpler for the validator than optional key.
- **`description` field added** (not strictly required by the spec but
  recommended by Q-new14's "public contract" framing). One sentence,
  domain-only. Makes the manifest self-documenting when browsed raw.

## Side Effects I MUST Mitigate (from CONTEXT §side-effect-mitigations)

1. PM CLAUDE.md hardcoded refs — Phase G
2. `compose.py` dispatch tables (lines 100-106, 166-167, 201-214) — Phase G
3. `config.py` FIELD_MAP + sync_agents — Phase G
4. `statusline.sh` agent loop — Phase H
5. Malformed manifest YAML → loud failure — Phase D
6. `routes_to` cycle detection — Phase D
7. Boot scripts (`start-role.sh/ps1`) must work for any new role — already
   parameterized per CONTEXT, no change needed

## References

- CONTEXT: `.squidsquad/skill/planning/FEAT-328-CONTEXT.md` (801 lines)
- TEST-PLAN: `.squidsquad/skill/planning/FEAT-328-TEST-PLAN.md` (307 lines)
- RESEARCH: `.squidsquad/skill/planning/FEAT-328-RESEARCH.md` (654 lines)
- Final inventory table: CONTEXT.md ~line 702
