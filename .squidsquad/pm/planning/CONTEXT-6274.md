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

Implementation in sub-phase 6274.1 (enumerated; this list is exhaustive — any future dual-aware addition MUST be appended here AND covered by an AC):
- `compose.py._list_known_role_identities()` returns `{worker, verifier, pm, dm, dev, qa}` during dual-aware window. After 6274.3, returns `{worker, verifier, pm, dm}`.
- `compose.py._resolve_variant()` accepts both `dev-skill` and `worker-skill` as INPUT, and always returns the CANONICAL `(base, variant)` matching whichever directory exists on disk: pre-6274.2 returns `(dev, skill)` (because `references/roles/dev/skill/` is what exists); post-6274.2 returns `(worker, skill)` (because the directory was renamed and `references/roles/dev/` no longer exists). The same rule applies to `qa-*` → `(qa, ...)` pre-rename, `(verifier, ...)` post-rename. Input normalization is independent of directory state; return value tracks the directory.
- `compose.py` L4 prefix routing (per CONTEXT-9925 D6b — filename-prefix routing at `compose.py:404-410`) accepts BOTH `dev-`/`qa-` and `worker-`/`verifier-` filename prefixes when scanning `.squidsquad/project/`. Routes to the canonical (worker / verifier) consumer in either case. Old prefixes rejected in 6274.3.
- `config.py.get_field()` reads both `Workers` and `Dev Agents` keys; logs a deprecation warning if the old key is found.
- `boot_remote.py._parse_dev_agents()` renamed to `_parse_workers()` with a backward-compat alias function `_parse_dev_agents()` calling through. Deleted in 6274.3.
- `add_role.py` mandatory-roles set `("pm", "qa", "dm")` updated to `("pm", "verifier", "dm")`; emits a warning if a call site still uses the old set.
- `tracker.py` `*-lead` role-suffix consumer (see D11): accepts both old (`qa-lead`, `dev-lead`) and new (`verifier-lead`, `worker-lead`) as input to `--role`; emits deprecation warning on old; normalizes to canonical internally.

Rollback during the window: revert the shim code; old paths still work pre-6274.2 (files haven't moved). Post-6274.2 rollback means reverting the rename PR; the shim accepts whichever name corresponds to the on-disk state at HEAD.

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
- Updates `.squidsquad/.harness-state.json` agent dict keys per the schema in RESEARCH §2 (top-level `agents.<role>` keys; rewrites `agents.qa` → `agents.verifier` if present, and `agents.dev` → `agents.worker` in the rare case it exists — worker variants like `agents.skill` stay as-is because variant names don't change per D5).
- Prints a one-line stdout summary listing what was migrated.
- **Idempotency detection rule (single canonical check)**: Migration is considered complete iff config.md contains `Workers:` (no `Dev Agents:` key remains) AND `.squidsquad/worker/` exists (and `.squidsquad/dev/` does not). Both true → no-op and return code 0. Both false → perform the migration. Mixed (one of: `Workers:` present but `.squidsquad/dev/` still exists, or `.squidsquad/worker/` exists but `Dev Agents:` still in config.md) → halt with exit code 2 and stderr message "partial migration detected: <which mismatch>; manual intervention required". Same rule applies to qa↔verifier pair, checked independently — verifier may complete before worker or vice-versa across wizard runs but each pair is atomic per run.

Wizard runs the upgrade step BEFORE any other install/upgrade logic in 6274.2+.

### D5 — L3 variant directory layout: in-place rename (LOCKED, Q6)

- `references/roles/dev/` → `references/roles/worker/`
- `references/roles/qa/` → `references/roles/verifier/`
- Worker variant names UNCHANGED: `worker/skill/`, `worker/ios/`, `worker/android/`, `worker/fullstack/`, `worker/web/`
- Verifier variant directories exist on disk today under `references/roles/qa/` (`android/`, `fullstack/`, `ios/`, `skill/`, `web/`) but are NOT in active use (per RESEARCH §2 corrected) — currently scaffolding only. They follow the same rename pattern: `references/roles/verifier/{android,fullstack,ios,skill,web}/`. Same in-place rename, no content edits beyond what AC2.2 covers.
- L3 stub layouts from #9925 follow the same rename — `references/roles/worker/<variant>/responsibility.md` and `references/roles/verifier/<variant>/responsibility.md`.
- L2 sub-skill trees (`references/sub-skills/roles/dev/`, `references/sub-skills/roles/qa/`) follow the same rename pattern to `worker/` and `verifier/` respectively.

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

### D11 — `*-lead` suffix renames in tracker.py role-string (LOCKED, derived from Out-of-Scope inclusion + F9 audit)

Two specific suffix renames are IN SCOPE (called out so they're not missed):
- `qa-lead` → `verifier-lead` (every tracker.py call site uses `--role pm-lead` / `--role qa-lead` etc.; the prefix swaps but `-lead` suffix stays)
- `dev-lead` → `worker-lead` (rare — only used by dev sub-roles that today identify as `dev-lead` for cross-role transitions; today's tree mostly uses `skill-lead`, `pm-lead`, etc.; check `tracker.py` source for actual call sites)

Wired into:
- Sub-phase 6274.1 dual-aware shim in tracker.py: `--role qa-lead` and `--role verifier-lead` both accepted; old emits deprecation warning. Covered by AC1.4 (extended below).
- Sub-phase 6274.2 file content edits: every prose/template/CLAUDE.md occurrence of `qa-lead` rewritten to `verifier-lead`. Covered by AC2.2 (extended below).
- Sub-phase 6274.3 cleanup: old suffix rejected. Covered by AC3.5 (extended below).

NOT renamed: `pm-lead`, `dm-lead`, `skill-lead` (worker variant suffix), and all other variant `-lead` suffixes (`ios-lead`, `android-lead`, etc.) — these are unaffected.

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
- **AC1.4** — `tracker.py.create_issue()` and `create_task()` dual-tag every new issue with both old and new `role:*` labels. Also: `tracker.py` `--role` argument accepts both old (`qa-lead`, `dev-lead`) and new (`verifier-lead`, `worker-lead`) per D11; emits deprecation warning on old. Verified by `test_tracker.py::test_create_dual_label_during_migration` and `test_tracker.py::test_role_suffix_dual_aware_6274`.
- **AC1.5** — One-shot script `references/scripts/migrate_labels_6274.py` walks all OPEN issues with `role:dev` or `role:qa` and adds the new label alongside. Idempotent. Includes a `--dry-run` flag.
- **AC1.6** — Vault note `migration-6274-cutover` created as a PLACEHOLDER in 6274.1 with body `"target cutover date: TBD — populated in 6274.2 PR"`. The actual cutover date (T+30 from 6274.2 merge commit timestamp) is populated as the LAST commit in the 6274.2 PR (i.e., post-rename, pre-merge), so the note is correct at merge time. See also AC2.9.
- **AC1.7** — All existing tests pass (no regression). `pytest tests/` exits 0.

### Sub-phase 6274.2

- **AC2.1** — Directories renamed: `references/roles/dev/` → `references/roles/worker/`, `references/roles/qa/` → `references/roles/verifier/`, `references/sub-skills/roles/dev/` → `worker/`, `references/sub-skills/roles/qa/` → `verifier/`. All variant subdirs preserved per D5.
- **AC2.2** — All "role-string references" updated. **Positive definition** of a role-string reference (replaces the prior ambiguous parenthetical, per DS F4):
  - (a) Role identity names in prose meant for agent consumption — manifest entries, `instructions.md`, `responsibility.md`, `prohibitions.md`, `SOUL.md`, `agent-boundaries.md`, composed CLAUDE.md templates, and any `references/sub-skills/**/*.md` content that an agent reads as instructions.
  - (b) Hardcoded role-set constants in Python — e.g., `{"pm", "qa", "dm"}`, `("pm", "qa", "dm")`, or any literal tuple/set/list of role identity strings. (Found by AST scan of constant literals — not by raw text grep.)
  - (c) Template-embedded role routing keys — keys in YAML manifests (`role: dev` → `role: worker`), keys in `tracker.py` label format strings (`role:dev` → `role:worker`), keys in `compose.py` role-id maps.
  - (d) tracker.py `*-lead` suffix consumers per D11: `qa-lead` → `verifier-lead`, `dev-lead` → `worker-lead` in prose, docs, examples, and CLAUDE.md templates.
  - **Explicitly EXCLUDED**: file paths in code comments (e.g., `# see references/roles/dev/old-notes.md` historical refs), Python variable names (`dev_agent`, `qa_runner`), CLI argument names if any, English words that contain `dev`/`qa` as substrings (`developer`, `development`, `qaeda` — none expected but possible).
  - Sweep scope: all L1/L2/L3/L4 template files, all `references/**/*.{md,py,yml,yaml}` matching (a)–(d). Plus `references/agent-instructions.md`, `references/statusline.sh` role-display strings, `references/wizard/WIZARD.md` operator docs, `references/sub-skills/manifest.md`.
- **AC2.3** — L4 stub files renamed per D7: `references/sub-skills/project/{dev,qa}-*.md` → `{worker,verifier}-*.md`, and same in `.squidsquad/project/`.
- **AC2.4** — `wizard.py` gets the upgrade step from D4 (full spec there). Idempotent per the D4 detection rule. Detects + rewrites old config field + old per-install dirs + harness-state.json keys.
- **AC2.5** — `wizard.py` also handles the #9925-deferred L4 stub auto-copy from seed templates per D6.
- **AC2.6** — All tests pass after rename (per D10). Tests updated to assert new identities.
- **AC2.7** — `compose.py deploy-all` produces composed CLAUDE.md files for all 4 roles with the new identities. No regression in #9925 ACs (4-layer responsibility model still works).
- **AC2.8** — Live-system smoke test: re-run a sample agent boot using the new directory layout; verify the agent reads its composed CLAUDE.md correctly and emits `booted` with the right role name. Documented in `QA-RESULTS-6274-sub2.md`.
- **AC2.9** — Final commit of the 6274.2 PR populates the vault note `migration-6274-cutover` placeholder (created in 6274.1 per AC1.6) with the actual target date `T = merge_commit_timestamp + 30 days` (ISO 8601 date in UTC). Commit message must reference #6274 and AC2.9 for traceability. Pre-merge gate G1→2 verifies this commit exists in the PR.

### Sub-phase 6274.3

- **AC3.1** — Dual-aware shim code removed from `compose.py` + `config.py`. `_list_known_role_identities()` returns `{worker, verifier, pm, dm}` only.
- **AC3.2** — `config.py` no longer reads `Dev Agents:` key; emits an error if found (operator forgot to upgrade).
- **AC3.3** — Backward-compat alias functions (`_parse_dev_agents`, etc.) deleted.
- **AC3.4** — One-shot script `references/scripts/cleanup_labels_6274.py` deletes `role:dev` and `role:qa` GitHub labels via `gh api`. Idempotent. Includes a `--dry-run` flag.
- **AC3.5** — `tracker.py.create_*` no longer dual-tags; emits only the new `role:worker` / `role:verifier`. `tracker.py` `--role` argument rejects old `qa-lead` / `dev-lead` per D11 (raises with exit code 2 and message instructing operator to use new suffix).
- **AC3.6** — Vault note `migration-6274-cutover` updated to "cutover complete" with the actual cutover commit hash.
- **AC3.7** — New test `test_terminology_cutover_6274.py` performs **two narrowly-scoped** checks (replaces the prior naive grep, per DS F5):
  - (a) **Structural scan**: walks `references/**/*.py` and `references/scripts/**/*.py`, parses each with `ast` (skipping comments and string literals that are docstrings or string-formatted output). For every `Constant` node with string value in the set `{"dev", "qa", "dev-lead", "qa-lead", "role:dev", "role:qa"}`, fail. (Misses none of categories (b)/(c)/(d) from AC2.2 because those are constant literals.)
  - (b) **Prose scan**: walks `references/**/*.{md,yml,yaml}` and matches the regex `r"\b(role:dev|role:qa|qa-lead|dev-lead)\b"` (exact tokens — no substring matches on `developer`/`development`/etc.). Plus a separate scan for headings/manifest entries: `r"^(role|agent|dev_agents|qa_agents):\s*(dev|qa)\b"` (anchored to start-of-line key:value patterns). Fails on any match.
  - (c) NOT scanned: `tests/**`, `docs/**` (historical references allowed), `.squidsquad/**` (per-install state), `__pycache__/**`, anything outside `references/`.
  - Both checks must pass with zero hits for AC3.7 to be green.
- **AC3.8** — All existing tests pass; no regression.

### Pre-conditions (gates between sub-phases)

- **G1.→2**: sub-phase 6274.1 PR merged AND green for 24h on main before starting 6274.2. Pre-merge of 6274.2 PR: AC2.9 commit populating the vault note cutover date must be the last commit in the PR (script-verifiable by walking the PR commit list).
- **G2.→3**: sub-phase 6274.2 PR merged AND 30-day window elapsed (measured from the 6274.2 merge commit timestamp recorded in the vault note per AC2.9) AND a script-verifiable check confirms **dual-labeling has been working correctly throughout the window** — i.e., every issue created in the trailing 7 days carries BOTH the new `role:worker`/`role:verifier` label AND the corresponding old `role:dev`/`role:qa` label. Zero single-old-label issues in the trailing 7 days. (Rationale per DS F1: the original "zero new old labels" gate was unsatisfiable because D3 keeps the dual-labeling code emitting both labels through the entire window — that's the intended behavior, not a bug to catch. The corrected gate verifies the intended dual-labeling continued to function up to the cutover moment, which is what we actually want to confirm before deleting the old labels.) Script lives at `references/scripts/verify_dual_label_6274.py`; lands in 6274.1 PR alongside `migrate_labels_6274.py` for symmetry.

---

## Out of Scope

- Rename of `pm` or `dm` (already categorical; no value in renaming).
- Renaming variant names (`skill`, `ios`, etc.) — those stay.
- Changes to the agent state machine, tracker.py state transitions, harness API, or any semantic logic — pure naming + scaffolding.
- New role types (designer, security-auditor) — separate filings post-6274.
- Renaming `tracker.py` role-suffix conventions (`pm-lead`, `dm-lead`, `skill-lead`, etc.) beyond the prefix swap. The two prefix-swap suffix renames `qa-lead` → `verifier-lead` and `dev-lead` (rare) → `worker-lead` ARE in scope and are explicitly wired in D11 + AC1.4 + AC2.2(d) + AC3.5.
- TUI rebranding — TUI per event-arch §15.6 polls harness HTTP, not bus; any role-name strings in TUI display update naturally when manifests change.

---

## DS Review Findings — Resolution Map

DS audit (`REVIEW-6274-DEEPSEEK.md`, 2026-05-23): **10 findings** — 3 errors, 7 warnings. All resolved inline below.

| # | Severity | Location | Issue (summary) | Resolution |
|---|---|---|---|---|
| F1 | error | G2→3 gate | Required "zero new role:dev/qa labels in 7d" but D3 keeps emitting both labels through window — gate unsatisfiable | G2→3 rewritten to verify dual-labeling has been WORKING (every trailing-7d issue has BOTH labels). New script `verify_dual_label_6274.py` lands in 6274.1. |
| F2 | error | AC1.6 | Demanded cutover date (T+30 from 6274.2 merge) be set in 6274.1, but 6274.2 merge time unknown then | AC1.6 → placeholder vault note in 6274.1. New AC2.9 populates the date as the last commit in 6274.2 PR. G1→2 verifies that commit exists. |
| F3 | error | D2 `_resolve_variant` | Said `(dev, skill)` returned post-rename, but `references/roles/dev/` is gone then | D2 clarified: input normalization is independent of directory state; return value tracks whichever directory exists on disk. Pre-6274.2: `(dev, ...)`. Post-6274.2: `(worker, ...)`. Input accepts both forms throughout. |
| F4 | warning | AC2.2 | "Role-string reference" had no objective decision rule | AC2.2 rewritten with positive definition (a)–(d): prose role identities, hardcoded role-set constants, template routing keys, `*-lead` suffix consumers. Explicit EXCLUDED list. AST-scan for (b). |
| F5 | warning | AC3.7 | `\bdev\b` grep would hit `developer`/`development` false positives | AC3.7 rewritten with two narrow checks: (a) AST scan of `references/**/*.py` for `Constant` nodes with role-string values, (b) prose scan with anchored regex `\b(role:dev|role:qa|qa-lead|dev-lead)\b` + start-of-line key:value patterns. Test scope excludes `tests/`, `docs/`, `.squidsquad/`. |
| F6 | warning | D4 idempotency | "Detects already migrated" mechanism unspecified | D4 spells out single canonical check: `Workers:` in config.md AND `.squidsquad/worker/` exists. Both → no-op. Both absent → migrate. Mixed → halt with exit code 2 and named-mismatch error. |
| F7 | warning | D4 harness-state | `.harness-state.json` schema undocumented | RESEARCH §2 updated with the schema (top-level `agents.<role>` dict). D4 specifies exact key renames: `agents.qa` → `agents.verifier`, `agents.dev` → `agents.worker` (rare). Variant keys (`agents.skill`) untouched. |
| F8 | warning | D7 vs D2 | L4 prefix routing dual-awareness in D7 but missing from D2 inventory | D2 enumeration extended to include `compose.py` L4 prefix routing per CONTEXT-9925 D6b. D2 is now declared exhaustive — any future addition MUST be appended there AND covered by an AC. |
| F9 | warning | Out-of-Scope vs ACs | Said `qa-lead`→`verifier-lead`, `dev-lead`→`worker-lead` in scope but no AC wired them | New D11 ties the suffix renames into 6274.1 (dual-aware accept in tracker.py — AC1.4 extended), 6274.2 (file content rewrite — AC2.2(d)), 6274.3 (old rejected — AC3.5 extended). Out-of-Scope line updated. |
| F10 | warning | RESEARCH §2 / D5 | `references/roles/qa/` "5 variant dirs" contradicting "no variants in use"; D5 silent on verifier variants | RESEARCH §2 corrected: qa has 5 variant directories ON DISK but they are SCAFFOLDING-ONLY (no instructions.md content yet). D5 extended to enumerate verifier variants explicitly with the same in-place rename pattern. |

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
