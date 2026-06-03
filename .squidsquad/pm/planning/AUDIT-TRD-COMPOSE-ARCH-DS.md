Now I have comprehensive evidence. Let me compile the full audit.

---

## COMPOSE-ARCHITECTURE.md Audit against shipped + in-flight work

### Summary Table

| TRD Section | CONFIRMED | IN PROGRESS | HELD | GAP | DRIFT | STALE |
|---|---|---|---|---|---|---|
| §1 Goal & model | 1 | 0 | 0 | 0 | 0 | 0 |
| §2 L1-L4 model recap | 3 | 0 | 0 | 0 | 0 | 0 |
| §3.0 Compose inputs | 2 | 0 | 0 | 0 | 1 | 0 |
| §3.1 DRY across layers | 1 | 0 | 0 | 0 | 0 | 0 |
| §3.2 Slot+ordinal | 3 | 0 | 0 | 0 | 1 | 1 |
| §3.3 L4 ops | 3 | 0 | 0 | 0 | 1 | 0 |
| §3.4 Soul semantic-merge | 1 | 0 | 0 | 0 | 0 | 0 |
| §4.1 Link: L1-L3 merge | 2 | 0 | 0 | 0 | 0 | 0 |
| §4.2 Link: L4 application | 3 | 0 | 0 | 0 | 0 | 0 |
| §4.5 Sub-skill ref resolution | 1 | 0 | 0 | 1 | 1 | 0 |
| §4.5.1 Claude-skills installer | 0 | 1 | 0 | 0 | 0 | 0 |
| §4.6 Assemble pass | 4 | 0 | 0 | 0 | 0 | 0 |
| §5 Composed-output structure | 3 | 0 | 0 | 0 | 0 | 0 |
| §5.5 Project Context | 2 | 0 | 0 | 1 | 1 | 0 |
| §6.1 Step ID grammar | 2 | 0 | 0 | 0 | 0 | 0 |
| §6.5 Wake-mode handling | 3 | 0 | 0 | 0 | 0 | 0 |
| §6.6 Subagent rules | 1 | 0 | 0 | 0 | 0 | 0 |
| §7 Runtime L4 writes | 4 | 0 | 0 | 0 | 0 | 0 |
| §8 Source-output sync | 3 | 0 | 0 | 0 | 0 | 0 |
| §9 Code-review checklist | 0 | 0 | 0 | 1 | 0 | 0 |
| §10 Migration plan | 0 | 2 | 2 | 1 | 0 | 1 |
| §11 Gaps & open questions | 4 | 0 | 0 | 0 | 0 | 0 |
| §12 Closure plan | 5 | 2 | 0 | 0 | 0 | 1 |
| §13 Glossary | 0 | 0 | 0 | 0 | 1 | 0 |
| **TOTAL** | **51** | **5** | **2** | **4** | **6** | **3** |

---

### Finding 1

- **TRD section**: §3.0 `## Aliases` canonical schema (lines 173-197)
- **Verdict**: DRIFT
- **Evidence**: TRD §3.0 specifies the canonical `## Aliases` format as a 3-column markdown table:
  ```
  | alias | role-class | L3 domain |
  |---|---|---|
  | pm | pm | — |
  ```
  The actual `.squidsquad/config.md` (lines 14-19) uses the legacy bullet form:
  ```
  - **skill**: skill
  - **pm**: pm
  - **dm**: dm
  - **qa**: qa
  ```
  The code at `references/scripts/config.py:336-401` (`_parse_aliases_bullet_form`) has an explicit fallback for this, acknowledging at line 458: "Real installs still ship the legacy `- **alias**: value` form." The bullet form lacks the explicit `L3 domain` column — L3 domain is inferred from the value (e.g., `skill` → `role_class="worker", l3_domain="skill"`).
- **Severity**: low
- **Suggested action**: Either (a) update the config.md to the canonical table format and retire the bullet-form parser, or (b) update TRD §3.0 to document both formats as valid, with the table form as preferred for new installs. The manifest's E6 V2 CUTOVER (#10685) may be a natural point for this migration.

---

### Finding 2

- **TRD section**: §3.2 "Every L1-L3 sub-skill source file declares structured frontmatter" (lines 226-231)
- **Verdict**: DRIFT
- **Evidence**: TRD §3.2 states: "Every L1-L3 sub-skill source file declares structured frontmatter at the top." The role source files (`references/roles/<role>/instructions.md`, `references/roles/<role>/SOUL.md`, `references/roles/instructions.md`, `references/roles/vault.md`) all have frontmatter ✓. However, the ~70 sub-skill body files under `references/sub-skills/common/`, `references/sub-skills/roles/<role>/`, and `references/sub-skills/common-events/` have NO frontmatter. The `v2_link_stage.py` at line 9-10 explicitly skips them: "Skip files that lack frontmatter — they are not yet migrated under #10394 and the v2 path treats unmigrated files as opt-out content." The D2 rule (#10673) intentionally suppresses `references/sub-skills/` from the instructions slot. The TRD uses "L1-L3 sub-skill source file" ambiguously — it could mean "source files that compose into L1-L3" (which have frontmatter) or "source files under references/sub-skills/" (which mostly don't). The shipped behavior matches the intent but the TRD wording is misleading.
- **Severity**: low
- **Suggested action**: Clarify TRD §3.2 to distinguish between "composition source files" (role instructions.md, SOUL.md, vault.md — require frontmatter) and "sub-skill body files" (under references/sub-skills/ — do not require frontmatter; their content is referenced, not composed). Reference #10394 as the tracking issue for the sub-skill body file migration.

---

### Finding 3

- **TRD section**: §3.2 SOUL.md shorthand convention (lines 273-278)
- **Verdict**: STALE
- **Evidence**: TRD §3.2 documents a filename convention: "`references/roles/<role>/SOUL.md` — compose treats as shorthand for a file with `slot: soul, ordinal: 1` frontmatter." However, all four SOUL.md files on disk (`references/roles/{pm,worker,verifier,dm}/SOUL.md`) declare explicit frontmatter with `ordinal: 20`, not `ordinal: 1`. The "shorthand" concept — implicit slot assignment by filename — does not appear to be implemented; the files just use normal explicit frontmatter. The SOUL.md filename convention is a documentation artifact, not a functional code path. The TRD says "May be replaced by a regular `.md` with explicit frontmatter; the shorthand is equivalent, not load-bearing" — but since the actual files already use explicit frontmatter, the shorthand description is misleading.
- **Severity**: low
- **Suggested action**: Remove or reword the SOUL.md "shorthand" description in §3.2. Either document it as "the conventional filename for the L2 soul source file (which declares `slot: soul` via explicit frontmatter like any other source file)" or remove the special-case entirely since it's not load-bearing.

---

### Finding 4

- **TRD section**: §3.3 Multi-file L4 pattern deprecation (lines 322-326)
- **Verdict**: DRIFT
- **Evidence**: TRD §3.3 says: "Deprecates the multi-file L4 pattern. Earlier installs scattered L4 content across per-slot files (`<role>-instructions.md`, `<role>-responsibility.md`, `<role>-soul-directives.md`, `shared-instructions.md`, etc.) under `.squidsquad/project/`. Those are legacy." The new unified files exist (`pm.md`, `worker.md`, `verifier.md`, `dm.md`). However, the legacy per-slot files still exist on disk: `pm-instructions.md`, `pm-responsibility.md`, `pm-soul-directives.md`, `shared-instructions.md`, `shared-responsibility.md`, `shared-soul-directives.md`, and equivalents for worker, verifier, dm. The catalog at `docs/sub-skill-catalog.md:269-273` acknowledges: "Legacy multi-file L4 seeds (deprecated) — earlier installs scattered L4 content across per-slot files. These remain on disk until the unified model is implemented." The manifest does not list this cleanup as shipped, in-progress, or held.
- **Severity**: low
- **Suggested action**: File a cleanup task to remove legacy per-slot L4 files from `.squidsquad/project/` after confirming all content has been migrated to the unified `<role-class>.md` files. Add to manifest as either in-progress or held with an explicit gate.

---

### Finding 5

- **TRD section**: §4.5 step 4 — Catalog drift check in compose pipeline (lines 532-545)
- **Verdict**: GAP
- **Evidence**: TRD §4.5 step 4 states: "every catalog entry must resolve to a real source file on disk, AND every sub-skill source file under `references/sub-skills/` must have a catalog entry. If either side is out of sync, compose emits a warning listing the drifted entries, then aborts with a diagnostic." The two-way drift check exists as `references/scripts/catalog_drift.py` (shipped as PRD-D D4, #10675). However, it is only available as a standalone subcommand (`compose.py drift-check`, wired at `compose.py:2345-2389`), NOT as part of the `deploy_alias_v2` pipeline. The deploy pipeline calls `v2_catalog_gate.validate_v2_compose()` (line 1681) which only checks forward resolution (references → catalog → file), not the reverse direction (source files → catalog entries) and not catalog-row → file-existence for unreferenced rows. The TRD requires this to be an in-pipeline abort, not a separate manual check.
- **Severity**: medium
- **Suggested action**: Wire `catalog_drift.scan_drift()` into `deploy_alias_v2` (or into `v2_catalog_gate.validate_v2_compose()`) so the two-way drift check runs as part of every compose and aborts on drift per TRD §4.5. The separate `drift-check` subcommand can remain as an operator diagnostic. Alternatively, update TRD §4.5 to reflect the actual split (forward gate in pipeline; two-way drift check as operator subcommand).

---

### Finding 6

- **TRD section**: §4.5.1 — Project-scoped Claude-skills installer (lines 576-613)
- **Verdict**: IN PROGRESS (do NOT flag as gap)
- **Evidence**: TRD itself marks this as "Gap — not yet shipped." The manifest lists PRD-D Sub-skills as Claude Skills (#10781) as `status:planned`, hard-gated on E6 ship. The catalog at `docs/sub-skill-catalog.md:68-77` describes this as "Target state — real Claude skills." Folds #10362.
- **Severity**: N/A (tracked in-progress work)
- **Suggested action**: None — this is actively tracked. The manifest entry at line 10 covers it.

---

### Finding 7

- **TRD section**: §5.5 — `discussion-protocol.md` → `discussion.md` rename (line in retirement notes)
- **Verdict**: GAP (sub-component of #10360)
- **Evidence**: TRD §5.5 retirement note states: "`discussion` and `issue-filing` stay as `common/` sub-skills; per-role overrides collapse... **Rename**: the existing `discussion-protocol.md` filename simplifies to `discussion.md`." The file on disk is still `references/sub-skills/common/discussion-protocol.md` (confirmed via glob). No `references/sub-skills/common/discussion.md` exists. The per-role override files (`references/sub-skills/roles/{pm,verifier,dm}/discussion-protocol.md` and `references/sub-skills/roles/{pm,verifier,dm}/issue-filing.md`) also still exist. The catalog at line 117 uses the target name `discussion` but notes the source file hasn't been renamed. #10360 is referenced throughout the catalog and TRD as the tracking issue, but #10360 does NOT appear in the manifest as shipped, in-progress, or held.
- **Severity**: medium
- **Suggested action**: Either (a) file #10360 as an explicit in-progress or held item in the manifest with a gate (e.g., "gated on E6"), or (b) if #10360 has been deprioritized, update the TRD retirement notes to reflect the current timeline. The accumulation of ~10+ files that the TRD says "should be deleted" without any tracking in the manifest is a process gap.

---

### Finding 8

- **TRD section**: §5.5 — Retired sub-skills still on disk (status-line, file-conventions, agent-boundaries, prohibitions)
- **Verdict**: GAP
- **Evidence**: TRD §5.5 contains multiple retirement notes asserting these files should be deleted, all tracked under #10360:
  - `status-line.md` — "delete all 4 status-line.md files" — 4 files still on disk (`common/status-line.md`, `roles/pm/status-line.md`, `roles/verifier/status-line.md`, `roles/dm/status-line.md`)
  - `file-conventions.md` — "drop file-conventions.md entirely" — 5 files still on disk (common + 4 per-role)
  - `agent-boundaries.md` — "Delete common/agent-boundaries.md" — 1 file still on disk
  - `prohibitions.md` — "delete the 4 prohibitions.md files" — 4 files still on disk (common + pm/verifier/dm overrides)
  
  Total: ~14 files the TRD says should be deleted that still exist. The manifest does not list #10360. The catalog reflects target architecture but acknowledges "Source files remain on disk until #10360 implements the migration."
- **Severity**: medium
- **Suggested action**: Add #10360 to the manifest as either in-progress (if actively being worked) or held (with an explicit gate, e.g., "gated on E6 + E7"). Without manifest tracking, these files are invisible to the audit process and will persist indefinitely despite the TRD declaring them retired.

---

### Finding 9

- **TRD section**: §9 — Code-review checklist sub-skill (`compose-output-review.md`) (lines 1485-1496)
- **Verdict**: GAP
- **Evidence**: TRD §9 specifies a new sub-skill: "`references/sub-skills/common/compose-output-review.md`. Composed into every `worker` agent's CLAUDE.md as a sub-procedure invoked during code review." The TRD §12 closure plan lists this as sub-PR M: "Code-review checklist sub-skill (deliverable b)." The file does not exist on disk (glob returned no matches). The catalog at `docs/sub-skill-catalog.md:144` says: "`compose-output-review` — implementation pending." The manifest does not list this as shipped, in-progress, or held. PRD-B, PRD-C, PRD-D, and PRD-E are all accounted for — this deliverable falls through the cracks between PRDs.
- **Severity**: low
- **Suggested action**: Either file this as a task under an existing or new PRD, or explicitly deprecate it from the TRD if the code-review checklist is adequately covered by the existing `l4-curation` and DS-audit patterns. Add to manifest as held or in-progress.

---

### Finding 10

- **TRD section**: §10.2 L1-L3 cleanup priority 3 — "Eliminate duplicate H2 sections" (line 1521)
- **Verdict**: GAP
- **Evidence**: TRD §10.2 step 3 says: "Eliminate duplicate H2 sections (the L3/L4 collisions documented in `RESEARCH-9968.md` §2). For each, pick a single authoring location; the other layer references it." This cleanup is listed in the migration plan but the manifest does not reference it as shipped, in-progress, or held. The PRD-A through PRD-E family covers the compose pipeline, L4, catalog, freshness, and cutover — but the "eliminate duplicate H2 sections" work (which is about resolving content collisions between L3 variant files and L4 project files) is not covered by any shipped PRD story.
- **Severity**: low
- **Suggested action**: Either file a task for this cleanup (possibly as part of #10360 or a follow-up), or confirm that the v2 link stage's L4 op processor effectively resolves these collisions at compose time (making the separate cleanup less urgent). Update manifest accordingly.

---

### Finding 11

- **TRD section**: §12 Closure plan vs actual shipped work (lines 1611-1636)
- **Verdict**: STALE
- **Evidence**: TRD §12 lists 14 sub-PRs (A-N) as a future implementation epic with dependencies. The actual implementation shipped under a different story-numbering scheme: PRD-A (A1-A6, A2a-A2f), PRD-B (B1-B9), PRD-C (C1-C10), PRD-D (D1-D5, D7-D8), PRD-E (E1-E7). The closure plan's numbering (A=frontmatter, B=parse/sort, C=L4 ops, etc.) doesn't map to the shipped PRD story numbers. Several items listed as future work in §12 are actually shipped (e.g., B "compose.py: parse frontmatter; sort by (slot, ordinal); emit six-section output" shipped as PRD-A A2d/A2f). The closure plan is effectively a historical artifact — it describes the work as it was planned, not as it was executed.
- **Severity**: low
- **Suggested action**: Replace §12 with a "Shipped work" summary referencing the actual PRD-A through PRD-E story families, or remove it entirely and rely on the manifest as the single source of truth for implementation status.

---

### Finding 12

- **TRD section**: §12 item N — "Memory → L4 backfill tool + migration" (line 1635)
- **Verdict**: STALE
- **Evidence**: TRD §12 item N lists: "Memory → L4 backfill tool + migration | pm (tool) + skill (review) | C, D". The `.squidsquad/project/{pm,worker,dm}.md` files contain extensive L4 content (200+ lines each with Identity, Soul, Instructions, Project Context sections) that appears to have been authored directly, not migrated via a tool. The `migrate_memory_to_l4.py` tool referenced in §10.4 does not exist on disk. The PM's memory feedback files (30+ files referenced in §10.4) may have been manually consolidated into the current L4 files. The migration tool and the backfill described in §10.4 appear to be obsolete — the L4 files are already populated.
- **Severity**: low
- **Suggested action**: If the memory → L4 migration was done manually, update §10.4 and §12 item N to reflect that the migration is complete (or was bypassed). Remove the `migrate_memory_to_l4.py` reference if the tool was never built.

---

### Finding 13

- **TRD section**: §13 Glossary — "Composed output" definition (line 1691)
- **Verdict**: DRIFT
- **Evidence**: TRD §13 glossary defines "Composed output" as: "The generated `.squidsquad/<alias>/CLAUDE.md` file — one per running agent instance (alias-keyed, not role-class-keyed)." This is correct for v2. However, earlier in the same glossary, the "L1 / L2 / L3 / L4" entry references a different path pattern. And the SOUL.md shorthand description references the old role-keyed path. The glossary correctly reflects the alias-keyed model, but the rest of the TRD uses mixed terminology. Additionally, the current shipped v1 outputs land at `.squidsquad/<role>/CLAUDE.md` (e.g., `.squidsquad/pm/CLAUDE.md`), and the v2 outputs land at `.squidsquad/<alias>/CLAUDE.v2.md` via the `--v2` flag. The v2 path with `.v2.md` suffix is a transitional artifact of the §9a coexistence rule — the TRD describes the target state without the `.v2.md` suffix, but that suffix won't be removed until E6 ships.
- **Severity**: low
- **Suggested action**: No immediate action — the `.v2.md` suffix is a known transitional artifact documented in the E6 cutover plan. After E6 ships, the outputs will match the TRD's described paths.

---

### Finding 14

- **TRD section**: §4.5 step 1 — Reference extraction grammar (lines 517-521)
- **Verdict**: CONFIRMED
- **Evidence**: TRD §4.5 step 1 says compose extracts `→ run sub-skill: <name>` references. The v2_catalog_gate.py at line 44-46 implements the regex: `r"→\s+run\s+sub-skill:\s+([a-z][a-z0-9/_-]*)"`. The L1 base instructions.md at `references/roles/instructions.md` uses this exact grammar (e.g., line 17: `→ run sub-skill: boot-bootstrap`). The regex allows slashes for role-scoped catalog names like `roles/dm/events/pr-merge-wait`. All shipped code matches the TRD spec.
- **Severity**: N/A (confirmed)
- **Suggested action**: None.

---

### Finding 15

- **TRD section**: §6.5 — includes-v2.yml for all four base roles (lines 1277-1280)
- **Verdict**: CONFIRMED
- **Evidence**: TRD §6.5 says every role-class has exactly one mode-agnostic manifest. Confirmed: `references/roles/pm/includes-v2.yml`, `references/roles/worker/includes-v2.yml`, `references/roles/verifier/includes-v2.yml`, `references/roles/dm/includes-v2.yml` all exist. The compose.py `_load_manifest_v2` function (line 339) reads these files. The D5 story (#10676) is shipped per manifest.
- **Severity**: N/A (confirmed)
- **Suggested action**: None.

---

### Finding 16

- **TRD section**: §4.6 — Assemble pass wired unconditionally (lines 596-660)
- **Verdict**: CONFIRMED
- **Evidence**: TRD §4.6 requires the assemble pass to run unconditionally after link, with caching, conflict detection, preservation checks, and triple atomic emit. All confirmed shipped:
  - `assemble_pass.py` (B1, #10444): per-slot dispatch, verbatim slots for project-context and vault
  - `assemble_adapter.py` + `assemble_cache.py` (B6): caching by SHA256(linked_body || slot || model || prompt_version)
  - `conflict_detector.py` + `conflict_resolver.py` (B4/B5, #10445): higher-L-wins conflict resolution
  - `atomic_emit.py` (B7, #10447): triple atomic write (CLAUDE.v2.md + CLAUDE.linked.v2.md + CLAUDE.conflicts.v2.md)
  - `assemble_verifier.py` (B2/B3): preservation checks (sub-skill ref set equality, step ID set equality, length floor, code-block parity)
  - B9 (#10763) wired the pipeline into `deploy_alias_v2` at compose.py lines 1705-1753
  - Cache wired via `assemble_adapter.make_b6_cache_adapter` at line 1720
  - Model locked to `sonnet` at line 1727
- **Severity**: N/A (confirmed)
- **Suggested action**: None.

---

### Finding 17

- **TRD section**: §8.1–§8.3 — Source-output sync (three-layer defence) (lines 1556-1631)
- **Verdict**: CONFIRMED
- **Evidence**: All three layers shipped:
  - §8.1 Layer 1 (boot-time check): `compose_freshness.py` (E1, #10680) — SHA256 over source tree, compared against `last_compose_checksum` in `.harness-state.json`, runs `compose.py deploy-all` on drift before spawning agents
  - §8.2 Layer 2 (L4-write trigger): `l4_file_watcher.py` (E3, #10682) — file-watch on `.squidsquad/project/`, recomposes affected aliases, emits `restart-required` event
  - §8.3 Layer 3 (operator check): `squidsquad_cli.py check` (E4) — read-only diagnostic at lines 480-584
  - E2 (checksum storage in harness-state.json) and E5 (additional wiring) also shipped per manifest
- **Severity**: N/A (confirmed)
- **Suggested action**: None.

---

### Finding 18

- **TRD section**: §7 — Runtime L4 writes (decision tree, safety gates, audit trail) (lines 1416-1542)
- **Verdict**: CONFIRMED
- **Evidence**: All PRD-C stories (C1-C10) shipped per manifest:
  - `l4-curation.md` sub-skill exists at `references/sub-skills/common/l4-curation.md` (C1, #10650)
  - `l4_audit_gate.py` — DeepSeek audit gate (C3)
  - `l4_mini_cq.py` — mini-CQ human confirmation (C4)
  - `l4_compose_dryrun.py` — compose --check dry-run (C5, wired at compose.py line 2143)
  - `l4_write_commit.py` — L4 file write + git commit (C6)
  - `l4_conflict_preempt.py` — conflict pre-emption at authoring time (C7)
  - `l4_recompose_recovery.py` — recompose failure recovery (C8)
  - `l4_removal.py` — L4 entry removal (C9 counter-op mechanism in l4_op_processor.py line 59-60)
  - The three-gate sequence (DS audit → mini-CQ → compose dry-run) from §7.4/§7.6 is implemented
- **Severity**: N/A (confirmed)
- **Suggested action**: None.

---

### Finding 19

- **TRD section**: §3.3 Per-slot op constraints — Vault L1-exclusive enforcement (lines 363-380)
- **Verdict**: CONFIRMED
- **Evidence**: TRD §3.3 says: "L4 files MUST NOT contain a `## Vault` H2 section." The link_stage_validator.py (R2 rule at line 10-11, 112) rejects L2/L3 source files with `slot: vault` frontmatter. The L1 vault source lives at `references/roles/vault.md` with `slot: vault, ordinal: 10` frontmatter ✓. No L4 file in `.squidsquad/project/` contains a `## Vault` H2 (grep confirmed zero matches). The vault slot is correctly L1-exclusive in both spec and implementation.
- **Severity**: N/A (confirmed)
- **Suggested action**: None.

---

### Finding 20

- **TRD section**: §11.2 G2 — Role-class filter `roles:` frontmatter wildcards (lines 1591-1593)
- **Verdict**: CONFIRMED (deferred per TRD)
- **Evidence**: TRD §11.2 G2 is marked as an open question: "For v2, only literal role-class names are supported; wildcards/classes are deferred." The shipped `source_frontmatter.py` and `v2_link_stage.py` implement the `roles:` filter with literal role-class names only. This matches the TRD's stated deferral.
- **Severity**: N/A (confirmed, intentionally deferred)
- **Suggested action**: None — the TRD itself says this is deferred. Close G2 or leave open for a future iteration.

---

### Finding 21

- **TRD section**: §5.5 — Retired sub-skills listed in `## Project Context` section (retirement notes)
- **Verdict**: STALE (inconsistent retirement status)
- **Evidence**: The TRD §5.5 contains 5 large retirement note blocks for `status-line`, `file-conventions`, `agent-boundaries`, `prohibitions`, and `discussion`/`issue-filing` per-role overrides. Each says "Tracked in #10360." However:
  - The catalog at `docs/sub-skill-catalog.md` reflects the post-retirement target architecture (rows removed, renamed)
  - The source files still exist on disk
  - The includes-v2.yml manifests still reference the old names (e.g., `common/file-conventions`, `common/status-line`, `common/prohibitions`, `common/agent-boundaries`, `roles/pm/discussion-protocol`)
  - The v1 includes.yml manifests also still reference them
  - #10360 is not in the manifest

  This creates a three-way inconsistency: the TRD says these are retired, the catalog says they're retired, but the compose manifests still include them and the files still exist. The retirement is "declared but not executed."
- **Severity**: medium
- **Suggested action**: Add #10360 to the manifest with an explicit gate (e.g., "gated on E6 + E7"). Until #10360 ships, the retirement notes in §5.5 should carry a clearer "NOT YET EXECUTED" caveat to avoid reader confusion about whether the files are actually deleted.