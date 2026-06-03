Now I have all the evidence needed. Here is the audit.

---

# INSTALLER-ARCH.md Audit — Summary Table

| Verdict | Count |
|---|---|
| **CONFIRMED** | 13 |
| **IN PROGRESS** | 3 |
| **HELD** | 1 |
| **GAP** | 5 |
| **DRIFT** | 7 |
| **STALE** | 0 |

---

## CONFIRMED

### Finding 1 — Clone isolation mandatory (§1.2)

- **TRD**: §1.2 lines 57–63 — clone isolation is always-on; per-alias clone registry at `~/.squidsquad/clones/`.
- **Evidence**: `wizard.py` scaffold (lines 1162–1174) creates sibling clones for non-PM agents; `shared_fs.py` has `write_clone`/`read_clones` (lines 260–267, 239–257); `.local-config` maps aliases to clone paths.
- **Verdict**: CONFIRMED.

### Finding 2 — shared_fs.py init produces correct ~/.squidsquad/ tree (§4.2)

- **TRD**: §4.2 lines 157–162 — `~/.squidsquad/{secrets, config, clones/}`.
- **Evidence**: `shared_fs.py` `init()` (lines 29–61) creates exactly `secrets` (chmod 600), `config`, and `clones/` directory.
- **Verdict**: CONFIRMED.

### Finding 3 — wizard.py check-gh returns correct JSON envelope (§4.1, §6)

- **TRD**: §4.1 lines 170–172 — `check-gh` returns `ok: true|false` with `stage: ready|installed|authenticated`.
- **Evidence**: `wizard.py` `check_gh()` (lines 157–200) returns exactly this shape.
- **Verdict**: CONFIRMED.

### Finding 4 — No `event-driven:` config field (§3.2)

- **TRD**: §3.2 outputs row: "No `event-driven:` field — wake-mode selection happens at agent boot via harness probe."
- **Evidence**: Actual `.squidsquad/config.md` (67 lines) has no `event-driven:` field.
- **Verdict**: CONFIRMED.

### Finding 5 — GitHub labels via `gh label create` (§4.8 step 5)

- **TRD**: §4.8 step 5 lines 284–286 — idempotent label creation via `gh label create`.
- **Evidence**: `wizard.py` `ensure_labels()` (lines 1621–1678) calls `gh label create`, handles "already exists" idempotently.
- **Verdict**: CONFIRMED.

### Finding 6 — Forgejo backend script exists (§9)

- **TRD**: §9 lines 564–566 — Forgejo via `forgejo_setup.py`.
- **Evidence**: `references/scripts/forgejo_setup.py` exists (30 lines confirmed) with `check-docker`, `deploy`, `status`, `create-repo`, `create-token`, `teardown` subcommands.
- **Verdict**: CONFIRMED.

### Finding 7 — start.sh post-install boot script exists (§6)

- **TRD**: §6 helper table — `start.sh` "Ensures Python deps, syncs all clones, runs the harness."
- **Evidence**: `start.sh` (60 lines) verifies python3/pip, installs fastapi/uvicorn, syncs clones from `.local-config`, runs `harness.py`.
- **Verdict**: CONFIRMED.

### Finding 8 — WIZARD.md runbook exists (§7)

- **TRD**: §7 lines 430–431 — "Its full runbook is at references/wizard/WIZARD.md — 700+ lines."
- **Evidence**: `references/wizard/WIZARD.md` exists with Steps 0–7, error recovery, tone rules.
- **Verdict**: CONFIRMED.

### Finding 9 — Capabilities directory removed (§8.3)

- **TRD**: §8.3 lines 484–486 — `references/sub-skills/capabilities/` and `common/capability-check.md` "slated for removal."
- **Evidence**: `glob` for `references/sub-skills/capabilities/**` returned zero matches. Directory is already gone.
- **Verdict**: CONFIRMED.

### Finding 10 — Install spec serialization (§4.8 step 2)

- **TRD**: §4.8 step 2 — "Serializes the install spec to a temporary location."
- **Evidence**: `wizard.py` `save_install_spec()` (lines 864–881) writes to `.squidsquad/.install-spec.json`; `load_install_spec()` (lines 884–898) reads it back.
- **Verdict**: CONFIRMED.

### Finding 11 — Per-agent directory scaffold (§4.8 step 3)

- **TRD**: §4.8 step 3 — per-alias agent dirs with CLAUDE.md placeholders, working-state.md skeletons, planning/, iterations/.
- **Evidence**: `wizard.py` `scaffold_install()` (lines 975–1160) creates agent dirs, deploys CLAUDE.md via `deploy_role`, writes `working-state.md` skeleton, creates `iterations/` and `planning/` subdirs.
- **Verdict**: CONFIRMED.

### Finding 12 — Idempotent re-run guard (§11.1)

- **TRD**: §11.1 lines 651–668 — Phase 0a is idempotent; scaffold refuses overwrite; labels skip existing.
- **Evidence**: `shared_fs.py` `init()` uses `mkdir(exist_ok=True)`, checks file existence; `wizard.py` `scaffold_install()` raises `FileExistsError` unless `overwrite_existing=True` (line 1018); `ensure_labels()` handles "already exists" (line 1670).
- **Verdict**: CONFIRMED.

### Finding 13 — shared_fs.py init idempotent (§4.2 / §11.1)

- **TRD**: §4.2 — "Idempotent — re-runs are safe."
- **Evidence**: `shared_fs.py` `init()` (lines 39–61) creates dirs with `exist_ok=True` and files only if absent.
- **Verdict**: CONFIRMED.

---

## IN PROGRESS (do NOT flag as gaps)

### Finding 14 — compose.py deploy takes alias, not role (§4.9)

- **TRD**: §4.9 lines 300–301 — "`compose.py deploy <alias>` writes to `.squidsquad/<alias>/CLAUDE.md`, regardless of role-class."
- **Evidence**: Current v1 `deploy_role()` has separate `role_name`/`output_name` params; v1 usage string says `deploy <role>` (line 2159). v2 `deploy_alias_v2()` (line 1555) resolves alias→role_class via registry and writes alias-keyed output. The `--v2` flag is still required. The TRD itself notes the rename to `<alias>` is tracked in #10358.
- **Covered by**: E6 V2 CUTOVER (#10685) — will make v2 default and drop `--v2`.
- **Verdict**: IN PROGRESS.

### Finding 15 — Claude Skills installer not yet shipped (§4.9 "Current-state caveat")

- **TRD**: §4.9 lines 327–333 — "the project-scoped Claude-skills installer that materializes sub-skill references into invokable Skill tool entries is **not yet shipped** (COMPOSE-ARCHITECTURE §4.5.1, tracked in #10362)."
- **Evidence**: The current CLAUDE.md output uses `→ run sub-skill: <name>` refs that agents resolve manually from `sub-skill-catalog.md`.
- **Covered by**: PRD-D Sub-skills as Claude Skills (#10781) — manifest says "Folds #10362."
- **Verdict**: IN PROGRESS.

### Finding 16 — compose.py deploy-all v1 doesn't use `## Aliases` registry (§6)

- **TRD**: §6 helper table — `deploy-all` "Iterates the alias roster from `.squidsquad/config.md ## Aliases`."
- **Evidence**: v1 `deploy-all` (line 2238) calls `_collect_all_roles()` which reads `workers` config field + appends mandatory roles — does NOT parse `## Aliases`. v2 `deploy-all --v2` (line 2264) does use `parse_aliases_registry()`.
- **Covered by**: E6 V2 CUTOVER (#10685) will make v2 the default path; then deploy-all will use the registry as described.
- **Verdict**: IN PROGRESS.

---

## HELD (do NOT flag as gaps)

### Finding 17 — D6 Remove `event-driven:` config field (#10677)

- **TRD**: §3.2 — field is already absent in TRD spec.
- **Evidence**: Manifest says D6 is `status:approved`, gated on E6 ship. The field is already not present in config.md, so this is effectively a TRD-alignment cleanup.
- **Verdict**: HELD.

---

## GAP

### Finding 18 — Migration walk framework does not exist (§4.3, §10)

- **TRD sections**: §4.3 (Phase 0b — Re-run detection + migration walk), §10 (Migration walk — full specification with 5 steps, three-gate model, per-version migration files, migration file format).
- **Severity**: **high**
- **Evidence**: 
  - `references/migrations/` directory does not exist (glob returned no matches).
  - `wizard.py` `detect_existing_install()` (lines 257–306) returns `exists`/`contents`/`has_config`/`has_roles` — no version stamp reading, no migration iteration.
  - `wizard.py` has no migration-related code whatsoever.
  - `WIZARD.md` Step 0b (lines 63–97) offers a 3-way prompt (abort / regenerate templates / full rebuild) — not the sequential per-version migration walk with three-gate model.
  - TRD §10.5 acknowledges "as of this draft, `references/migrations/` is empty" but the framework code to *execute* migrations (walk, three-gate, stamp update) is entirely absent.
- **Suggested action**: Either (a) implement the migration walk in wizard.py with the three-gate model per TRD §10, or (b) downgrade TRD §10 to "planned" status and update WIZARD.md to match the current 3-way prompt reality.

### Finding 19 — `references/VERSION` file does not exist (§3.2, §4.8 step 3, §10 step 2)

- **TRD sections**: §3.2 outputs — version stamp written from `references/VERSION`; §4.8 step 3 — "the squidsquad_version: field read from references/VERSION already present in the installer source tree"; §10 step 2 — "installer-version reads from references/VERSION."
- **Severity**: **high**
- **Evidence**: `glob` for `references/VERSION` returned no matches. The actual `wizard.py` code at lines 2415–2421 reads version via `config.get_field("version")` with fallback `"0.36.0"` — a completely different mechanism than the TRD describes. The `build_config_md()` at line 662 uses `spec.get("squidsquad_version", "0.0.0")` — also not reading from a VERSION file.
- **Suggested action**: Either create `references/VERSION` and wire it into the wizard, or update TRD to describe the actual version source (`config.get_field("version")`).

### Finding 20 — Vault subdirectories not created (§5)

- **TRD**: §5 file layout lines 373–379 — vault contains `projects/`, `areas/`, `resources/`, `archives/`, `galaxy/` plus `BRIEFING.md`.
- **Severity**: **medium**
- **Evidence**: Actual `.squidsquad/vault/` contains only `BRIEFING.md` and `.relevance-index.json` — none of the five subdirectories exist. The `wizard.py` scaffolder does not create vault directories (no reference to vault creation in `scaffold_install()` lines 975–1160).
- **Suggested action**: Add vault subdirectory creation to the scaffold step, or update TRD to reflect that these are created at runtime by the vault sub-skill.

### Finding 21 — Phase 7 tracker setup (initial issues) not implemented (§4.10)

- **TRD**: §4.10 lines 338–340 — "the installer may seed initial issues — e.g. issue #1 with the project's roadmap or onboarding tasks. This is configurable per-install."
- **Severity**: **low**
- **Evidence**: No code in `wizard.py`, `WIZARD.md`, or any helper script implements initial-issue seeding. WIZARD.md Step 7 bundles everything into a single commit step with no separate issue-seeding sub-step. The TRD itself hedges with "may" — but describes it as a distinct Phase.
- **Suggested action**: Either implement initial-issue seeding in wizard.py or demote this to an aspirational note / remove Phase 7 from the phase decomposition.

### Finding 22 — Post-installer harness restart not implemented (§10.3)

- **TRD**: §10.3 lines 629–648 — after Phase 8 commit, installer triggers per-agent restart via `POST /agents/<alias>/stop` + `POST /agents/<alias>/start`, falling through to `start.sh`.
- **Severity**: **medium**
- **Evidence**: No code in `wizard.py` for HTTP calls to harness. WIZARD.md Step 7 ends with commit + push + "SquidSquad ready" message; no restart logic. `wizard.py` has no import or reference to HTTP client calls, harness port detection, or restart endpoints.
- **Suggested action**: Implement harness restart in the installer, or document it as deferred to a separate post-install step the human runs manually.

---

## DRIFT

### Finding 23 — `squidsquad_version:` field name mismatch (§3.2, §10 step 2)

- **TRD sections**: §3.2 — "`squidsquad_version: <semver>` field"; §10 step 2 — "one-line read of `.squidsquad/config.md`'s `squidsquad_version:` field."
- **Severity**: **high**
- **Evidence**: Actual `.squidsquad/config.md` line 3 uses `- **SquidSquad Version**: 0.43.0` — different key name (Title Case with spaces vs snake_case with colon), different format (bullet in markdown list vs YAML-like `key: value`). `wizard.py` `build_config_md()` line 662–665 renders it as `- **SquidSquad Version**: {version}`. The migration walk's ability to find/read the version field depends on this exact name.
- **Suggested action**: Either rename the config.md field to `squidsquad_version: <semver>` to match TRD, or update all TRD references to use the actual field name `SquidSquad Version`.

### Finding 24 — `## Aliases` registry format mismatch (§3.2, §4.8 step 3)

- **TRD**: §3.2 — "`## Aliases` registry section mapping each install-time alias to its role-class + L3 domain"; §4.8 step 3 shows a markdown table with `alias | role-class | L3 domain` columns.
- **Severity**: **medium**
- **Evidence**: Actual `.squidsquad/config.md` lines 15–20 have:
  ```
  ## Aliases
  - **skill**: skill
  - **pm**: pm
  - **dm**: dm
  - **qa**: qa
  ```
  This is a flat bullet list of `alias: alias` — no role-class column, no L3 domain column. The v2 compose code `parse_aliases_registry()` does parse from this section, but the format is different from the TRD's table schema.
- **Suggested action**: Align actual config.md `## Aliases` format with TRD table schema, or update TRD to document the actual key-value list format.

### Finding 25 — wizard.py subcommands in TRD §6 don't match code (§6)

- **TRD**: §6 helper table lists `wizard.py` subcommands: `check-gh`, `detect-stack`, `scaffold`, `enrich-l4`, `ensure-labels`, `serialize-spec`.
- **Severity**: **medium**
- **Evidence**: `detect-stack`, `enrich-l4`, and `serialize-spec` do not exist in `wizard.py`. Grep across `references/scripts/` returned zero matches for these names. Actual subcommands per `wizard.py` docstring (lines 11–34): `check-gh`, `check-existing`, `repo-info`, `project-name-default`, `build-config-md`, `scaffold`, `ensure-labels`, `list-issues-by-label`, `migrate-label`, `migrate-labels-staged`.
- **Suggested action**: Update TRD §6 helper table to list actual wizard.py subcommands, or implement the missing ones.

### Finding 26 — L4 Project Context seeding writes to wrong files (§4.8 step 4)

- **TRD**: §4.8 step 4 lines 257–266 — Phase 1 project-intake answers written to `.squidsquad/project/<role-class>.md` under `## Project Context` H2 section, in the unified L4 file per role-class.
- **Severity**: **medium**
- **Evidence**: `wizard.py` `_write_l4_project_files()` (lines 901–938) writes to `shared-stack-details.md` (stack + test commands), not to `<role-class>.md`. `_copy_l4_seed_stubs()` (lines 941–972) copies legacy multi-file stubs (`worker-instructions.md`, `worker-responsibility.md`, `worker-soul-directives.md`, etc.) from `references/sub-skills/project/` — the very pattern the TRD §4.8 "Historical context" note says is retired. The actual `<role-class>.md` files (e.g., `pm.md`, `worker.md`) in `.squidsquad/project/` exist but their content is not seeded by the installer from Phase 1 answers.
- **Suggested action**: Update `_write_l4_project_files()` to write to the unified `<role-class>.md` files under `## Project Context`, and remove `_copy_l4_seed_stubs()` or gate it on existing-install detection.

### Finding 27 — Legacy multi-file L4 stubs still created by installer (§4.8 "Historical context")

- **TRD**: §4.8 step 4 "Historical context" note lines 276–282 — "The installer does **not** carry migration code for the legacy pattern — fresh installs never see it."
- **Severity**: **low**
- **Evidence**: `wizard.py` `_copy_l4_seed_stubs()` (lines 941–972) explicitly copies `worker-*` and `verifier-*` files from `references/sub-skills/project/` to `.squidsquad/project/` for new installs. The actual `.squidsquad/project/` directory contains 19 files including the legacy multi-file pattern (`pm-instructions.md`, `worker-responsibility.md`, `shared-instructions.md`, `setup-upgrade-gate.md`, etc.) alongside the unified files. The comment at line 1063 says this "absorbs #9925 deferred work per D6/D7" — so this is deliberate, but contradicts the TRD.
- **Suggested action**: Reconcile: either the TRD's "retired" claim is premature and should be softened, or the `_copy_l4_seed_stubs()` function should be removed.

### Finding 28 — TRD phase decomposition vs WIZARD step numbering mismatch (§2, §4)

- **TRD**: §2 numbering note — "Phases 0–9" are an architectural decomposition; §4.11 calls it "Phase 8 — Commit + push."
- **Severity**: **low**
- **Evidence**: WIZARD.md uses Steps 0/0a/0b/1/1b/2/3/4/5/5b/5c/5d/6/7. These do not map cleanly to the TRD's Phase 0–9 decomposition. Specifically, WIZARD Step 7 is described as "Commit and write" — bundling everything the TRD separates into Phases 5 (scaffold), 6 (compose), 7 (tracker setup), and 8 (commit). The TRD acknowledges this at §2 numbering note but the deck is stacked too far apart — Phase 7 "Tracker setup" is listed as a separate phase in the TRD flowchart but doesn't exist as a distinct step in WIZARD.md.
- **Suggested action**: Either renumber WIZARD.md steps to mirror TRD phases, or collapse TRD's Phase 5–8 into a single "write + commit" phase matching WIZARD Step 7.

### Finding 29 — `compose.py deploy-all` v1 behavior differs from TRD description (§6)

- **TRD**: §6 — `deploy-all` "Iterates the alias roster from `.squidsquad/config.md ## Aliases` and runs `deploy <alias>` per entry."
- **Severity**: **medium**
- **Evidence**: v1 `deploy-all` (line 2285–2311) calls `_collect_all_roles()` which reads the `workers` config field string, splits on commas, and appends mandatory roles — it does NOT parse `## Aliases`. The `## Aliases` registry is only used by v2 `deploy-all --v2` (line 2264–2284). Since `--v2` is not yet default, the documented behavior doesn't match the default execution path.
- **Suggested action**: E6 will resolve this (making v2 default). In the interim, the TRD should note that `deploy-all` without `--v2` uses the legacy role iteration path.

---

## Summary of High-Severity Items

| # | Verdict | Section | Issue |
|---|---------|---------|-------|
| 18 | GAP | §4.3, §10 | Migration walk framework entirely unimplemented |
| 19 | GAP | §3.2, §4.8 | `references/VERSION` file missing; version sourced differently |
| 23 | DRIFT | §3.2, §10 | `squidsquad_version:` field name doesn't match actual config.md |

The TRD describes a sophisticated migration-walk system (§10) with per-version markdown files, a three-gate model, and clean-stop semantics — but zero code exists for any of it. The `squidsquad_version` field that the migration walk depends on doesn't exist in the specified format, and the `references/VERSION` file it would read from doesn't exist at all. These three findings together mean the entire re-install/upgrade story described in the TRD is aspirational, not implemented.