Now I have all evidence needed for the full audit. Here are the results:

---

## Feasibility Audit — #10781 Phase 2 Locked Decisions

---

### Concern 1 — Claude Skill `args:` mechanism (Q3 critical)

**Severity: BLOCKER**

- **File**: `SKILL.md` (repo root)
- **Line**: 1–6 (frontmatter)
- **Evidence**: The sole on-disk `SKILL.md` defines exactly four frontmatter fields: `name:`, `description:`, `version:`, `license:`. There is zero evidence of an `args:` field, `parameters:`, or any mechanism for passing runtime arguments to a Claude Skill. The `SKILL.md` body (all 522 lines) contains no mention of invocation arguments, argument passing, or parameterization of skills. A search for `args`, `argument`, or `parameter` across `SKILL.md` returns zero matches.
- **Why this blocks Q3**: The Phase 2 Q3 decision states: *"the SKILL.md instructs Claude to read `role` from invocation args; each agent's CLAUDE.md becomes `→ run sub-skill: vault-remember (role=pm)`."* This presumes the Claude Skill format supports runtime arguments. There is no on-disk evidence to support this assumption. The only known SKILL.md schema (`name:` / `description:` / `version:` / `license:`) has no args capability.
- **Proposed alternative**: Fall back to **per-role-class materialization** (the option RESEARCH-10781.md describes as "Option (a) — resolve at packaging/materialization time"). The deploy-time generator produces skill files at `.claude/skills/<name>/SKILL.md` with `[ROLE]` already substituted to the alias's role-class name at materialization time. The `→ run sub-skill: <name>` reference grammar stays unchanged. Each sub-skill shared across role-classes that differ only in placeholder values (e.g., `vault-remember` used by PM and worker) would need identical SKILL.md files at each role-class's subdirectory, or the skill needs to be written to use a role-agnostic approach (read role from environment/config instead of hardcoded placeholder). This avoids relying on an unproven `args:` mechanism.

---

### Concern 2 — Reference grammar (Q3)

**Severity: CONFIRMED (with caveat)**

- **Evidence**: Three regexes parse the `→ run sub-skill: <name>` reference grammar:
  - `references/scripts/v2_catalog_gate.py:44`: `r"→\s+run\s+sub-skill:\s+([a-z][a-z0-9/_-]*)"`
  - `references/scripts/assemble_verifier.py:30`: `r"→\s*run\s+sub-skill:\s*([A-Za-z0-9_-]+)"`
  - `references/scripts/link_stage_validator.py:32`: `r"→\s*run\s+sub-skill:\s*([A-Za-z0-9_-]+)"`
- **Analysis**: Adding `(role=pm)` to produce `→ run sub-skill: vault-remember (role=pm)` would NOT break reference extraction — all three regexes would still capture `vault-remember` since the capture group stops at the space before `(`. The `(role=pm)` suffix would pass through compose verbatim (the assemble pass preserves sub-skill refs verbatim per `assemble_verifier.py:9` contract).
- **Caveat (pre-existing bug, not caused by this change)**: `assemble_verifier.py:30` and `link_stage_validator.py:32` do NOT allow slashes in sub-skill names (`[A-Za-z0-9_-]+` vs `v2_catalog_gate.py:44`'s `[a-z][a-z0-9/_-]*`). For slash-bearing names like `roles/dm/events/pr-merge-wait`, the verifier and validator capture only `roles` instead of the full name — the sub-skill ref set equality check in the assemble pass would falsely report a mismatch on any output containing slash-bearing sub-skill refs. This is an existing inconsistency, not introduced by Q3, but should be fixed before PRD-D lands.

---

### Concern 3 — Generator hook point (route β)

**Severity: RISK**

- **File**: `references/scripts/compose.py`
- **Line**: 1661–1710 (`deploy_alias_v2` function)
- **Evidence**: The current v2 compose pipeline is: `emit_v2_linked` → `v2_catalog_gate.validate_v2_compose` → `assemble_pipeline.atomic_emit`. There is no existing hook for a SKILL.md generator. The PHASE2-LOCKED.md says "deploy-time generator reads `references/sub-skills/` templates → writes `.claude/skills/<name>/SKILL.md` artifacts" but does not specify where this generator slots in.
- **Why it's a risk**: Three options exist with different implications:
  1. **Before compose**: The catalog gate at `v2_catalog_gate.py:141` validates `→ run sub-skill:` refs against the catalog → `references/sub-skills/` source files. It does NOT check `.claude/skills/` existence (by design — AC5 guard at `catalog_parser.py:394` blocks `.claude/skills/` paths). If the generator runs before compose, the gate still can't validate SKILL.md artifact existence. The generator needs its own validation step.
  2. **Inside compose (new step between gate and assemble)**: Tight coupling; every compose run regenerates skills. Interacts with PRD-E freshness checks.
  3. **Separate installer step**: Run once at install/upgrade. Skills become stale if catalog changes without re-running. Needs its own freshness check.
- **Recommendation**: Lock this in Phase 2 follow-up. The generator should be a separate installer step (option 3) that runs at install and at `squidsquad-upgrade`, with its own freshness check (catalog hash vs last-materialized hash, analogous to COMPOSE-ARCHITECTURE §8.1). This keeps compose fast and decouples skill materialization from per-alias compose.

---

### Concern 4 — Tier classification authority (Q1)

**Severity: CONFIRMED**

- **File**: `references/scripts/catalog_parser.py`
- **Line**: 170–182 (header parsing), 310–322 (`_split_row`), 325–339 (`_resolve_description_column`)
- **Evidence**: The parser handles N-column tables flexibly:
  - `_split_row` (line 310) splits by `|` and returns ALL cells — no column-count validation.
  - `_resolve_description_column` (line 325) looks for header names `"one-liner"`, `"description"`, `"purpose"`, `"summary"` in column headers; defaults to index 1 if none found.
  - Additional columns beyond the description column are silently ignored — the parser accesses `description_col_index` specifically (line 256) but never validates total column count.
- **Implication**: Adding a `tier` column and/or `skill-description` column at the END of the table (after `Used by`) would NOT break the parser. However, the `skill-description` column must have a header name that does NOT match the existing description-column candidates (`"one-liner"`, `"description"`, `"purpose"`, `"summary"`) — otherwise the parser would treat it as the description column and the actual one-liner column would be ignored. Also, the parser would need to be extended to extract the new columns (currently only the description column is read from optional columns).
- **Note**: The existing D8 validation (`_validate_row_schema` at line 279) requires every row to have a non-empty description. Adding a `skill-description` column should NOT relax this — the one-liner is still required. A `skill-description` would be an additional, separate field for SKILL.md generation.

---

### Concern 5 — Wikilink ordering (Q4)

**Severity: RISK**

- **Evidence**: Wikilinks in sub-skills fall into two categories:
  1. **Sub-skill-to-sub-skill wikilinks** (e.g., `references/sub-skills/common-events/event-driven-workflow.md:12-16` using `[[l1-base]]`, `[[cursor-management]]`, `[[forge-read-pattern]]`, `[[idle-cooldown-loop]]`, `[[comment-handling]]`) — these are in `common-events/` fragments which are **NOT being converted to Claude Skills** (they're runtime-loaded via `boot-bootstrap.md:36-46`).
  2. **Sub-skill-to-vault wikilinks** (e.g., `references/sub-skills/roles/dm/delivery-packaging.md:58,85` referencing `[[feedback_never_rebase_merge_instead]]`; `references/sub-skills/roles/pm/task-intake.md:83-86` referencing `[[note-name]]`) — these reference vault notes, NOT sub-skills, and would NOT be transformed by #10690.
- **Why it's a risk**: The dependency chain E6 → E7 → #10690 → PRD-D is partially valid but may be **overly serialized**. The wikilinks that #10690 would transform (sub-skill-to-sub-skill) are concentrated in `common-events/` fragments — which are explicitly EXCLUDED from PRD-D's scope (they stay runtime-loaded, not converted to Claude Skills). Situational sub-skills that WOULD be converted (like `delivery-packaging`, `task-intake`) wikilink to vault notes, not sub-skills. This means PRD-D could potentially ship the SKILL.md generator for situational sub-skills **without** waiting for #10690, as long as vault-note wikilinks are preserved as-is in the generated SKILL.md body (which is the correct behavior — vault notes are not Skills).
- **Recommendation**: Split PRD-D into two sub-tranches: (a) SKILL.md materialization for sub-skills with no sub-skill-to-sub-skill wikilinks (can ship before #10690), and (b) `common-events/` → Skill conversion + wikilink transform (gated on #10690).

---

### Concern 6 — Tier mandatory/situational drift risk (Q1)

**Severity: BLOCKER**

- **Evidence**: Several sub-skills classified as "situational" in the Phase 2 decision have **fixed ordering positions within their role-class cycle** and must fire deterministically:

  | Sub-skill | Evidence of ordering constraint | File:Line |
  |---|---|---|
  | `checkin` | Listed as `#### step:cycle/check-in`, the **first PM cycle step** after boot | `references/roles/pm/instructions.md:172-176` |
  | `task-intake` | Listed as `#### step:cycle/task-intake` under `### insert-after step:cycle/pickup` — must run AFTER pickup, BEFORE approval | `references/roles/pm/instructions.md:178-184` |
  | `pipeline-sentinel` | Listed as `#### step:cycle/pipeline-sentinel` under `### insert-after step:cycle/work` — must run AFTER work, BEFORE cleanup | `references/roles/pm/instructions.md:192-198` |
  | `triage-issues` | Listed as `#### step:cycle/triage-issues` under `### insert-after step:cycle/resume` — must run AFTER resume, BEFORE implement | `references/roles/worker/instructions.md:116-122` |
  | `implement-tasks` | Listed as `#### step:cycle/implement` under `### append` — the main work step, must run after triage | `references/roles/worker/instructions.md:124-134` |
  | `verification` | Referenced twice in `references/roles/verifier/instructions.md:149,157` as the core cycle work | `references/roles/verifier/instructions.md:149-157` |
  | `delivery-packaging` | Listed in DM instructions as a core cycle step | `references/roles/dm/instructions.md:164` |

- **Why this blocks Q1**: Claude Skill invocation is **discretionary** (model-driven, description-matching). A sub-skill converted to a Claude Skill will only fire if the model decides its description matches the current situation. For the sub-skills above, the model MUST fire them in a specific order on every cycle — description-matching cannot guarantee this. If `pipeline-sentinel` becomes a Claude Skill, the PM model might simply not invoke it, and pipeline stalls would go undetected.

- **Proposed alternative**: Introduce a **three-tier classification**:
  1. **Mandatory-core** (~5): `boot-bootstrap`, `cycle-runner`, `context-pressure`, `self-restart`, `agent-lifecycle` — stay **inlined** in composed CLAUDE.md for ALL role-classes (same as Phase 2).
  2. **Role-mandatory** (~12): `checkin`, `task-intake`, `task-approval`, `pipeline-sentinel`, `health-check`, `vault-synthesis` (PM); `triage-issues`, `implement-tasks` (worker); `verification` (verifier); `delivery-packaging`, `version-bumps` (DM); plus role-specific boot/cleanup steps — stay **inlined** as `→ run sub-skill: <name>` references in the composed CLAUDE.md's ordered cycle checklist, but NOT as standalone Claude Skills. The composed CLAUDE.md preserves ordering; the agent reads the references and resolves them via the current file-read mechanism (not Skill tool). These are "thin orchestration references" — the distinction from mandatory-core is that their bodies are referenced, not inlined.
  3. **Truly-situational** (~10): `vault-remember`, `vault-optimize`, `improvement-scan`, `improvement-scan-slim`, `soul-shepherd`, `issue-filing`, `discussion`, `git-commit`, `l4-curation`, `boot-remote-agents` — converted to **Claude Skills** at `.claude/skills/`. These fire conditionally (e.g., `vault-remember` only on non-quiet cycles, `improvement-scan` only every N quiet cycles).

  The test: a sub-skill is "truly-situational" only if the cycle still produces correct results when the sub-skill is **skipped entirely**. `pipeline-sentinel` being skipped means pipeline stalls go undetected — it's not situational. `vault-remember` being skipped means one cycle's reflection is lost — acceptable.

---

### Concern 7 — Existing install upgrade path (Q5 + Q6)

**Severity: CONFIRMED**

- **Evidence**: 
  - Current composed CLAUDE.md files at `.squidsquad/<alias>/CLAUDE.md` contain inlined sub-skill bodies (v1 path) or `→ run sub-skill: <name>` references to `references/sub-skills/` source files (v2 path per `v2_link_stage.py:84-100`).
  - After PRD-D, situational sub-skills no longer appear inlined — they're at `.claude/skills/` instead.
  - The `squidsquad-upgrade` skill (described in `SKILL.md:350-418`) handles migration steps: detect version gap → read install spec → regenerate templates → patch config → sync labels → update version.
  - The upgrade flow already runs `compose.py deploy-all` (Step 3, `SKILL.md:368-374`), which regenerates CLAUDE.md files. After PRD-D, this same step would produce CLAUDE.md output with references instead of inlined bodies.
- **What's needed**: A new migration step in `squidsquad-upgrade` that:
  1. Creates `.claude/skills/` directory if absent.
  2. Runs the SKILL.md materializer for all situational-tier catalog entries.
  3. Then runs the existing `compose.py deploy-all` (which regenerates CLAUDE.md with references).
  4. Harness reboots agents (already handled by upgrade flow).
- **No manual operator intervention required** — `squidsquad-upgrade` handles it. The catalog gate at `catalog_parser.py:394-407` stays unchanged (correct — it guards the source-path column, not the generated artifact path).

---

## Summary

| Concern | Verdict | Key evidence |
|---|---|---|
| Q3 — Claude Skill `args:` mechanism | **BLOCKER** | `SKILL.md:1-6` — only `name:`/`description:`/`version:`/`license:` fields; zero evidence of args support |
| Q3 — Reference grammar extension | **CONFIRMED** | `v2_catalog_gate.py:44` regex captures name correctly even with `(role=pm)` suffix |
| Route β — Generator hook point | **RISK** | `compose.py:1661-1710` — no existing hook; three options with different freshness/PRD-E implications |
| Q1 — Tier classification parser support | **CONFIRMED** | `catalog_parser.py:310-339` — N-column flexible; new columns at end silently ignored |
| Q4 — Wikilink ordering dependency | **RISK** | `common-events/` wikilinks are NOT in PRD-D scope; situational sub-skills wikilink to vault notes, not sub-skills |
| Q1 — Mandatory/situational drift | **BLOCKER** | `references/roles/pm/instructions.md:172-198` — `checkin`, `task-intake`, `pipeline-sentinel` have fixed cycle ordering; cannot be description-matched |
| Q5+Q6 — Upgrade path | **CONFIRMED** | `SKILL.md:350-418` — existing `squidsquad-upgrade` flow handles recompose; needs new materializer step |