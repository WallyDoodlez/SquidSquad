# CONTEXT-6274 — Terminology generalization (`dev → worker`, `qa → verifier`)

**Issue**: #6274
**Phase**: 2 (Locked Decisions)
**Author**: pm-lead
**Date**: 2026-05-23
**Status**: planning → planned (after human approval of these locks)
**Depends on**: event-arch v2 doc (PR #9945 merged 2026-05-23 commit `5b21ec5f`)
**Companion**: `.squidsquad/pm/planning/RESEARCH-6274.md` (Phase 1)

> **AUTHORITATIVE SCOPE**: `.squidsquad/pm/planning/CONTEXT-6274.md` + `RESEARCH-6274.md` + the GitHub issue body for #6274. Read all three before pickup. The issue body is a summary; the planning artifacts are the contract.

---

## Authoritative Scope Statement

Rename `dev` → `worker` and `qa` → `verifier` across the entire codebase, in 3 reversible sub-phases. Migration uses a code-level dual-aware shim during the transition (not symlinks, not file copies). `pm` and `dm` stay — already categorical. No semantic change to the agent state machine; this is naming + scaffolding rename.

The event-arch v2 doc (`docs/EVENT-ARCHITECTURE.md`) already uses `worker`/`verifier`; this task makes the codebase catch up. After this task ships, the implementation epic from event-arch §15 can spawn its 6 PRs.

---

## Locked Decisions

### D1 — Field name: `Workers:` in config.md (LOCKED, Q1)

The per-install field becomes `Workers: skill` (replacing today's `Dev Agents: skill`). Short, clean, matches the L2 categorical name.

`Verifiers:` field NOT added — verifier is currently single-instance (`qa`) and PM/QA/DM are already implicit/mandatory per the existing config pattern. If multiple verifier variants land in the future, a `Verifiers:` field can be added then.

`config.py` reads both `Workers:` AND `Dev Agents:` during the dual-aware window (sub-phase 6274.1 + 6274.2); deletes the old key in 6274.3.

### D2 — Dual-aware mechanism: code-level (LOCKED, Q2)

Phase 1 mechanism is **code-level dual support** in `compose.py` + `config.py`. NOT symlinks (brittle on Windows; breaks template-embedded paths). NOT file copies (drift risk + disk cost).

Implementation in sub-phase 6274.1:
- `compose.py._list_known_role_identities()` returns `{worker, verifier, pm, dm, dev, qa}` during dual-aware window. After 6274.3, returns `{worker, verifier, pm, dm}`.
- `compose.py._resolve_variant()` accepts both `dev-skill` and `worker-skill` (returning `(dev, skill)` and `(worker, skill)` respectively). Both `references/roles/dev/skill/` and `references/roles/worker/skill/` paths resolve correctly during the window.
- `config.py.get_field()` reads both `Workers` and `Dev Agents` keys; logs a deprecation warning if the old key is found.
- `boot_remote.py._parse_dev_agents()` renamed to `_parse_workers()` with a backward-compat alias function `_parse_dev_agents()` calling through. Deleted in 6274.3.
- `add_role.py` mandatory-roles set `("pm", "qa", "dm")` updated to `("pm", "verifier", "dm")`; emits a warning if a call site still uses the old set.

Rollback during the window: revert the shim code; old paths still work since files haven't moved yet.

### D3 — Tracker label transition: dual-label, 30-day window (LOCKED, Q3 + Q5)

- During sub-phase 6274.1 + 6274.2 + the 30-day window:
  - Every NEW issue gets BOTH labels: `role:worker` AND `role:dev` (or `role:verifier` AND `role:qa`).
  - `tracker.py.create_issue()` and `create_task()` dual-label on creation.
  - One-shot migration script during sub-phase 6274.1 lands: walks all OPEN issues, adds the new label alongside the old. Closed/historical issues left as-is.
- After the 30-day window (sub-phase 6274.3):
  - Bulk-delete `role:dev` and `role:qa` labels via `gh api`.
  - Dual-labeling code removed.

30-day window starts when sub-phase 6274.2 merges (the rename PR). Tracked via vault note `migration-6274-cutover` (to be created in 6274.1).

### D4 — Wizard auto-upgrade for existing installs (LOCKED, Q4)

`wizard.py` gets an upgrade step that runs on next wizard invocation:
- Detects old config field name (`Dev Agents:`) and old directory layout (`.squidsquad/dev/`, `.squidsquad/qa/`).
- Rewrites config.md atomically: `Dev Agents:` → `Workers:`.
- Renames `.squidsquad/dev/` → `.squidsquad/worker/` and `.squidsquad/qa/` → `.squidsquad/verifier/` (preserving all subfiles).
- Updates `.squidsquad/.harness-state.json` agent dict keys.
- Prints a one-line stdout summary listing what was migrated.
- Idempotent: re-running detects "already migrated" and no-ops.

Wizard runs the upgrade step BEFORE any other install/upgrade logic in 6274.2+.

### D5 — L3 variant directory layout: in-place rename (LOCKED, Q6)

- `references/roles/dev/` → `references/roles/worker/`
- `references/roles/qa/` → `references/roles/verifier/`
- Variant names UNCHANGED: `worker/skill/`, `worker/ios/`, `worker/android/`, `worker/fullstack/`, `worker/web/`
- L3 stub layouts from #9925 follow the same rename — `references/roles/worker/<variant>/responsibility.md`

Rationale: minimum cognitive shift. The variant names (`skill`, `ios`, etc.) are not affected by this rename; only the base directory parent changes.

### D6 — Wizard L4 stub copy absorption (LOCKED, Q7)

The wizard automation deferred by #9925 (auto-copy L4 stubs from `references/sub-skills/project/` seed templates to `.squidsquad/project/` for new installs) is ABSORBED into sub-phase 6274.2. Same wizard.py change covers:
- D4 auto-upgrade for existing installs
- New L4 stub copy for new installs (under the new `worker-responsibility.md` / `verifier-responsibility.md` names per D7)
- One PR; one wizard.py change.

### D7 — L4 stub file renames (LOCKED, derived from D5 + D6)

L4 stubs in BOTH locations get renamed in sub-phase 6274.2:
- `references/sub-skills/project/dev-*.md` → `worker-*.md` (4 files: `dev-instructions.md`, `dev-soul-directives.md`, `dev-responsibility.md`, and any future dev-prefixed)
- `references/sub-skills/project/qa-*.md` → `verifier-*.md` (3 files: same shape)
- `.squidsquad/project/{dev,qa}-*.md` → `{worker,verifier}-*.md` (mirror)
- Compose.py L4 prefix routing (per CONTEXT-9925 D6b) reads both old and new prefixes during the dual-aware window; only new prefixes after 6274.3.

### D8 — Compose-needed throttle: default behavior (LOCKED, Q8)

Per event-arch v2 §15.5, harness emits ONE `assigned-to(pm, event_context="compose-needed")` per `references/` merge. #6274's big rename merges (especially 6274.2) trigger ONE such event each, not per-file. PM runs one `compose.py deploy-all` per merge. No special handling needed.

The 6274.2 merge will be large (100+ files touched). PM's deploy-all run may take longer than normal but is single-shot.

### D9 — 3-sub-phase PR sequence (LOCKED, Q9, mirrors event-arch §15.5 E1/E2/E3 naming)

| Sub-phase | What lands | Reversibility | PR size |
|---|---|---|---|
| **6274.1** | Dual-aware shim in `compose.py` + `config.py`. New label dual-tagging in `tracker.py.create_*`. One-shot script to dual-label OPEN issues. Vault note `migration-6274-cutover` created. | Revert the shim code; nothing else has changed. | Medium |
| **6274.2** | Directory rename (`references/roles/dev/` → `worker/`, `qa/` → `verifier/`). All file content edits to update embedded role-name references. L4 stub renames. Wizard auto-upgrade step (D4 + D6). | Revert the merge; dual-aware shim from 6274.1 still resolves both names. | Largest of the three (~150-200 files) |
| **6274.3** | Delete the dual-aware shim code. Delete `role:dev` / `role:qa` labels via `gh api`. Delete backward-compat alias functions. Update vault note to "cutover complete." | Irreversible cleanup; main goes name-pure. Pre-merge requires QA verify the 30-day window has elapsed. | Small |

Each sub-phase its own PR, merging in sequence. 6274.3 lands only after 30 days have elapsed since 6274.2 merge.

### D10 — Test rewrites coupled to each sub-phase PR (LOCKED, Q10)

Each sub-phase PR includes the test updates required to keep green-on-merge:
- 6274.1 PR: dual-aware compose.py + config.py tests. New unit test `test_terminology_dual_aware_6274.py` covering both old and new name resolution.
- 6274.2 PR: rename references in existing tests; assertions on the new identities. Update `test_compose*.py`, `test_config*.py`, `test_boot_remote*.py`, `test_add_role*.py`, `test_wizard*.py`, `test_agent_boundaries.py` (from #9925).
- 6274.3 PR: delete dual-aware tests (no longer applicable); add a `test_terminology_cutover_6274.py` that grep-asserts no stale `\bdev\b` or `\bqa\b` role-string references survive in the active codepaths.

Larger per-PR diffs but each one fully validated atomically.

---

## Acceptance Criteria

### Sub-phase 6274.1

- **AC1.1** — `compose.py._list_known_role_identities()` returns the dual set `{worker, verifier, pm, dm, dev, qa}`. Verified by `test_compose.py::test_dual_aware_identities`.
- **AC1.2** — `compose.py._resolve_variant("worker-skill")` and `_resolve_variant("dev-skill")` both return valid resolutions. Tested.
- **AC1.3** — `config.py.get_field("workers")` reads both `Workers:` and `Dev Agents:` keys. Logs a deprecation warning when `Dev Agents:` is the source. Tested.
- **AC1.4** — `tracker.py.create_issue()` and `create_task()` dual-tag every new issue with both old and new `role:*` labels. Verified by `test_tracker.py::test_create_dual_label_during_migration`.
- **AC1.5** — One-shot script `references/scripts/migrate_labels_6274.py` walks all OPEN issues with `role:dev` or `role:qa` and adds the new label alongside. Idempotent. Includes a `--dry-run` flag.
- **AC1.6** — Vault note `migration-6274-cutover` created with target cutover date (T+30 days from 6274.2 merge).
- **AC1.7** — All existing tests pass (no regression). `pytest tests/` exits 0.

### Sub-phase 6274.2

- **AC2.1** — Directories renamed: `references/roles/dev/` → `references/roles/worker/`, `references/roles/qa/` → `references/roles/verifier/`. Variant subdirs preserved.
- **AC2.2** — All file content updated: any embedded role-string reference to `dev`/`qa` AS A ROLE (not as file paths in code comments, not as command-line variable names) updated to `worker`/`verifier`. Templates, manifest entries, includes.yml, instructions.md, responsibility.md, prohibitions.md across all 4 roles' L2 trees.
- **AC2.3** — L4 stub files renamed per D7: `references/sub-skills/project/{dev,qa}-*.md` → `{worker,verifier}-*.md`, and same in `.squidsquad/project/`.
- **AC2.4** — `wizard.py` gets the upgrade step from D4. Idempotent. Detects + rewrites old config field + old per-install dirs.
- **AC2.5** — `wizard.py` also handles the #9925-deferred L4 stub auto-copy from seed templates per D6.
- **AC2.6** — All tests pass after rename (per D10). Tests updated to assert new identities.
- **AC2.7** — `compose.py deploy-all` produces composed CLAUDE.md files for all 4 roles with the new identities. No regression in #9925 ACs (4-layer responsibility model still works).
- **AC2.8** — Live-system smoke test: re-run a sample agent boot using the new directory layout; verify the agent reads its composed CLAUDE.md correctly and emits `booted` with the right role name. Documented in `QA-RESULTS-6274-sub2.md`.

### Sub-phase 6274.3

- **AC3.1** — Dual-aware shim code removed from `compose.py` + `config.py`. `_list_known_role_identities()` returns `{worker, verifier, pm, dm}` only.
- **AC3.2** — `config.py` no longer reads `Dev Agents:` key; emits an error if found (operator forgot to upgrade).
- **AC3.3** — Backward-compat alias functions (`_parse_dev_agents`, etc.) deleted.
- **AC3.4** — One-shot script `references/scripts/cleanup_labels_6274.py` deletes `role:dev` and `role:qa` GitHub labels via `gh api`. Idempotent. Includes a `--dry-run` flag.
- **AC3.5** — `tracker.py.create_*` no longer dual-tags; emits only the new `role:worker` / `role:verifier`.
- **AC3.6** — Vault note `migration-6274-cutover` updated to "cutover complete" with the actual cutover commit hash.
- **AC3.7** — New test `test_terminology_cutover_6274.py` grep-asserts no stale `\bdev\b` or `\bqa\b` role-string references in active code paths. (File paths, variable names, comments may still legitimately contain "dev"/"qa" — the test excludes those.)
- **AC3.8** — All existing tests pass; no regression.

### Pre-conditions (gates between sub-phases)

- **G1.→2**: sub-phase 6274.1 PR merged AND green for 24h on main before starting 6274.2.
- **G2.→3**: sub-phase 6274.2 PR merged AND 30-day window elapsed AND zero new `role:dev` / `role:qa` labels created in the trailing 7 days (script-verified) before starting 6274.3.

---

## Out of Scope

- Rename of `pm` or `dm` (already categorical; no value in renaming).
- Renaming variant names (`skill`, `ios`, etc.) — those stay.
- Changes to the agent state machine, tracker.py state transitions, harness API, or any semantic logic — pure naming + scaffolding.
- New role types (designer, security-auditor) — separate filings post-6274.
- Renaming `tracker.py` role-suffix conventions (`pm-lead`, `qa-lead`, etc.) beyond the prefix swap — only `qa-lead` → `verifier-lead` and `dev-lead` (rare) → `worker-lead` are in scope.
- TUI rebranding — TUI per event-arch §15.6 polls harness HTTP, not bus; any role-name strings in TUI display update naturally when manifests change.

---

## DS Review Findings — Resolution Map

To be populated after DS review. Expected ~5-15 findings given the complexity (compare to CONTEXT-9925 which had 7 findings).

---

## Risk register (carried from RESEARCH §8)

| Risk | Severity | Mitigation in this CONTEXT |
|---|---|---|
| Existing installs break on upgrade | High | D2 + D4 dual-aware shim during transition; wizard auto-upgrade in 6274.2 |
| Composed CLAUDE.md regresses for in-flight tasks | Medium | 6274.2 lands during low-activity window; cycle_post triggers respawn on new templates per AC2.7 |
| GitHub label history confusion | Low-medium | D3 dual-label transition + vault note for audit trail |
| 100+ touchpoints means missed renames likely | High | AC3.7 grep-test catches stale references in active code |
| `tracker.py` label commands embedded in agent CLAUDE.md prose | Medium | Comprehension testing per `feedback_comprehension_testing` — spawn fresh agent post-6274.2 to quiz |
| 30-day window operator forgetfulness | Low | D3 vault note + 6274.3 gate (G2.→3) verifies zero new old-label creation in trailing 7 days |
