# PRD-A Story A1 — Compose.py vs Link-Stage Spec Drift Report

**Audit date**: 2026-05-31
**Spec**: `docs/COMPOSE-ARCHITECTURE.md` §3 (authoring principles), §4.1–§4.5 (link-stage pipeline), §5 (composed-output structure), §6.1–§6.4 (step-ID grammar)
**Code**: `references/scripts/compose.py` (1623 LOC, head `684b5629`)
**Audited by**: PM (per `feedback_pm_docs_only` — doc/spec review = PM)

---

## Headline

The current `compose.py` implements a **v1 model**: flat 3-layer concatenation with multi-file L4, inlined sub-skill bodies, wake-mode-split manifest, no slot grammar, no L4 ops, no validation gates, no `## Aliases` resolution. The TRD describes the **v2 target model**: six-slot grammar with `(slot, ordinal)` ordering, single-file L4 with H3 ops, **reference-only** sub-skill emission, mode-agnostic manifest, 6 hard validation rules, link+assemble two-stage pipeline.

**The drift is structural, not incremental.** PRD-A's claim that "the link stage already exists in `references/scripts/compose.py`" (PRD-A §6) is **wrong** — only a 3-layer concatenation skeleton exists; nearly every other §4.1–§4.5 contract is unimplemented.

---

## Drift Inventory (gap → classification)

Classification: `pure-impl` = code work, no spec change needed | `spec-gap` = needs PM/architect decision | `out-of-scope` = belongs to PRD B/C/D/E

### §3.0 — Compose inputs (config + L1–L4)

| # | Spec requirement | Code today | Classification |
|---|---|---|---|
| 1 | `## Aliases` registry parser in `config.md` | **Not implemented.** Code uses `Workers:` list directly via `_active_roles_for_roster`; no alias→role-class table parse | pure-impl (PRD-A story A5) |
| 2 | Alias-keyed output paths (`.squidsquad/<alias>/CLAUDE.md`) | Partial. `deploy_role` accepts `output_name` parameter that approximates alias-keying, but `compose_role` reads from `role_name` (treated as role-class id) | pure-impl (PRD-A story A6) |
| 3 | No `event-driven:` field | **Code still reads it** via `_get_wake_mode` (compose.py:55); wake-mode-split manifest still loaded via `_load_manifest` | pure-impl (PRD-D scope) |

### §3.1 / §3.2 — Slot + ordinal contract

| # | Spec requirement | Code today | Classification |
|---|---|---|---|
| 4 | Source files carry frontmatter `slot:` + `ordinal:` | **Not present** in current L1-L3 source files; no parser in code | pure-impl (PRD-A story A2 + a separate frontmatter migration, possibly Phase B of A2) |
| 5 | Sort merged content by `(slot_index, ordinal)` | **Not implemented.** Code emits files in directory/manifest order | pure-impl (PRD-A A2) |
| 6 | Six canonical slots: `identity / responsibility / soul / instructions / project-context / vault` | **Not implemented.** Code concatenates whole CLAUDE.md files (instructions.md from each layer) and appends sub-skills as separate `<!-- sub-skill: ... -->` blocks | pure-impl (PRD-A A2) |

### §3.3 — L4 operations (creative overlay)

| # | Spec requirement | Code today | Classification |
|---|---|---|---|
| 7 | **One L4 file per role-class** at `.squidsquad/project/<role-class>.md` | **Multi-file pattern still in use.** `_assemble_claude` iterates `.squidsquad/project/*.md`, applies prefix-based routing (`shared-`, `<role>-`, unprefixed). This is the **deprecated** legacy model per §3.3. | pure-impl (PRD-A A2 + L4 migration task — net-new) |
| 8 | L4 content organized by H2 slot sections (`## Identity`, etc.) | **Not parsed.** L4 files treated as opaque content append. | pure-impl (PRD-A A2) |
| 9 | L4 ops: `replace` / `insert-before` / `insert-after` / `append` (H3 blocks under slot H2) | **No op processor exists.** L4 content is appended verbatim as a sub-skill block. | pure-impl (PRD-A A2) |
| 10 | L4 op validation (target step-id resolution, mixed-op rejection, vault rejection, etc.) | **Not implemented.** | pure-impl (PRD-A A2) |

### §4.1 — Link: literal L1-L3 merge

| # | Spec requirement | Code today | Classification |
|---|---|---|---|
| 11 | Per-slot walk with frontmatter parse | **Not present.** `_assemble_claude` reads whole `instructions.md` per layer | pure-impl (PRD-A A2) |
| 12 | Sub-skill catalog gate (every reference resolves to a real sub-skill) | Partial. `_load_manifest` validates `includes` paths exist on disk; but the catalog/manifest model itself differs | partial pure-impl (PRD-A A2 narrow check) + (PRD-D full catalog) |

### §4.2 — Link: creative L4 application

| # | Spec requirement | Code today | Classification |
|---|---|---|---|
| 13 | Per-slot op stack application (later op layers on earlier) | **Not implemented.** L4 is flat content append; no op ordering, no per-slot op stack. | pure-impl (PRD-A A2) |

### §4.3 — Link: multi-domain L4

| # | Spec requirement | Code today | Classification |
|---|---|---|---|
| 14 | Multiple instances of the same role-class share one L4 file | **Implicit today** because every worker reads `.squidsquad/project/worker-*.md` — but the unification under `worker.md` H2 slots is not in code. | pure-impl (PRD-A A2) |

### §4.4 — End-to-end pipeline

| # | Spec requirement | Code today | Classification |
|---|---|---|---|
| 15 | Link stage → assemble stage → atomic emit | Partial. `compose_role` does link; `agent_compose` does an opportunistic LLM polish; output is single `CLAUDE.md`. No `CLAUDE.linked.md` or `CLAUDE.conflicts.md` sibling. | partial — link is in scope for PRD-A; assemble is PRD-B |
| 16 | Deterministic given `(role-class, source-tree-hash, L4-tree-hash)` | Partial. Current concatenation is deterministic, but inputs (multi-file L4, manifest split) differ from spec, so the **shape** isn't deterministic-by-construction in the v2 sense. | pure-impl (PRD-A A3 byte-stability tests) |

### §4.5 — Link: sub-skill reference resolution

| # | Spec requirement | Code today | Classification |
|---|---|---|---|
| 17 | Compose emits `→ run sub-skill: <name>` **references**, NOT bodies | **Code inlines sub-skill bodies** via `_resolve_includes_with_manifest` (compose.py:298). This is the entire opposite of spec intent. | pure-impl + spec-gap (large) — see Open Question Q-A1.1 below |
| 18 | Reference grammar matches §6.2 (verbatim text token) | **Not emitted.** Today's output has inlined bodies, not references. | pure-impl (PRD-A A2 / PRD-D) |

### §5 — Composed-output structure (six canonical H2 slots)

| # | Spec requirement | Code today | Classification |
|---|---|---|---|
| 19 | Output has exactly six H2 sections in canonical order | **Not enforced.** Current output is L1 → L2 → L3 → variant → L4 sub-skills, each preserving its own internal H2/H3 structure as-is | pure-impl (PRD-A A2) |

### §6.1–§6.4 — Step-ID grammar

| # | Spec requirement | Code today | Classification |
|---|---|---|---|
| 20 | Step IDs follow `step:cycle/<id>` BNF | Partial — step IDs already exist in source content but no formal parser/validator. | pure-impl (PRD-A A2 R5) |
| 21 | Flat numbering grammar for Instructions slot | **Not enforced.** Current Instructions content has nested numbering from L1/L2/L3 procedural sections. | pure-impl (PRD-A A2 + content migration — net-new) |

### Validation gates (PRD-A success criterion 6)

| # | Rule | Code today |
|---|---|---|
| R1 | L4 file with `## Vault` → abort | **Not implemented** |
| R2 | L2/L3 source with `slot: vault` → abort | **Not implemented** (no frontmatter parser at all) |
| R3 | L1-L3 source with `slot: project-context` → abort | **Not implemented** |
| R4 | L4 `### append` under `## Instructions` without sub-skill ref → abort | **Not implemented** |
| R5 | L4 op references non-existent step ID → abort | **Not implemented** |
| R6 | Whole-slot `replace` mixed with other ops → abort | **Not implemented** |

All six are pure-impl for PRD-A story A2; **none currently exist**.

---

## Out-of-scope items observed (not PRD-A's problem)

These belong to PRDs B–E; mentioning for traceability so they aren't accidentally rolled into A2/A5/A6:

- **Assemble pass (§4.6)** — `agent_compose` is a partial v0 (LLM polish + basic preservation check) but doesn't implement the full pass (cache, length floor, per-slot scoping, hard preservation, abort-on-failure, `CLAUDE.conflicts.md`). → **PRD B**
- **`l4-curation` sub-skill / runtime L4 writes (§7)** — entirely absent in code. → **PRD C**
- **Sub-skill catalog enforcement (§4.5 full)** — partial via `_load_manifest`'s exists-check; full catalog model not in place. → **PRD D**
- **Wake-mode probe-based selection (§6.5)** — `_get_wake_mode` still reads `config.md`'s `event-driven:` field; the boot-probe model means compose should be mode-agnostic. → **PRD D**
- **Harness boot-time freshness check (§8.1) / L4-write trigger (§8.2) / operator `squidsquad_cli.py check` (§8.3)** — entirely absent. → **PRD E** + harness work

---

## Implications for PRD-A's A2–A6 task scopes (#10385–#10389)

Given the drift, the existing PRD-A task bodies underspecified the work:

### A5 (`## Aliases` parser) — #10385

✅ **Scope holds.** Parser is new code; spec is clear. **No change needed.**

### A6 (CLI accepts alias) — #10386

⚠️ **Scope grows slightly.** Needs to:
- Replace `_active_roles_for_roster`'s `Workers:` reading with `## Aliases` registry (via A5)
- Make `compose_role` accept `(alias, role_class, l3_domain)` instead of bare `role_name`
- Preserve compose source vs output paths distinction

But this is still a tractable refactor. **No structural reshape needed.**

### A3 (byte-stability tests) — #10387

⚠️ **Scope holds, but premature.** Golden-file tests against the **current** output have low value — that output isn't the v2 contract. Better order: A2 ships v2 link stage → A3 builds goldens against v2.

**Recommendation**: hold A3 until A2 has at least the slot-grammar piece working.

### A2 (6 validation rules) — #10389

🚨 **Scope is dramatically larger than the original task body implied.** "Validation rules" assumes the rules sit on top of an existing v2 link stage. **They don't.** A2 effectively needs to deliver:

- (a) **Frontmatter parser** for slot+ordinal on L1-L3 sources (+ migration to add frontmatter to existing sources — may file as its own task)
- (b) **L4 H2-slot parser + H3 op grammar** for the single-file L4 model
- (c) **L4 op processor** (replace / insert-before / insert-after / append)
- (d) **Six-slot output emitter** (replaces current flat concat)
- (e) **Sub-skill reference emitter** — switch from inline body to `→ run sub-skill: <name>` (this is the BIG one — every agent's CLAUDE.md will change shape; PRD-D's catalog work is the consumer side)
- (f) The 6 validation rules R1-R6

This is at least 4–6 PRs of work, not one. **A2 must be re-scoped into smaller stories.**

### A4 (`--check` mode) — #10388

⚠️ **Scope holds, but premature.** `--check` is "in-memory compose, diff against on-disk" — meaningful only after v2 link stage is the actual on-disk output. Hold until A2 stabilizes.

---

## Open questions for PM/architect (Q-A1.x)

### Q-A1.1 — Reference-only sub-skill emission (item #17): when?

The biggest spec/code gap is: today compose **inlines** sub-skill bodies; spec says emit `→ run sub-skill: <name>` references and let the runtime resolve. This is a runtime-shaping change as much as a compose change:

- The agent at runtime needs to know what `→ run sub-skill: foo` means. Today the body is inlined; the agent reads procedure verbatim. With references, the agent must resolve `foo` at the point of execution (read `references/sub-skills/foo.md` at the point the cycle step references it).
- This implies sub-skill files are read at agent runtime, not just at compose time. That's a substantial agent-side change.

**Recommendation**: defer the inline→reference switch to PRD-D's catalog work (it's already in scope there per §4.5 catalog gate). PRD-A A2 should NOT attempt this switch. Update PRD-A scope to clarify.

### Q-A1.2 — L4 migration (item #7)

The existing `.squidsquad/project/` directory contains multi-file legacy L4 content (e.g., `shared-instructions.md`, `pm-instructions.md`, etc. across this repo's own install). Switching to single-file-per-role-class requires a one-shot migration. Should A2 include the migration, or is that a separate task?

**Recommendation**: separate task. PM files a migration story (let's call it A2.5) that runs once: consolidates existing multi-file L4 content into the four `<role-class>.md` files with H2 slots. Skill executes; PM reviews the resulting L4 files.

### Q-A1.3 — Source frontmatter migration (item #4)

Adding `slot:` and `ordinal:` frontmatter to ~50+ existing L1-L3 source files is mechanical but tedious. Same question: A2-bundled or separate?

**Recommendation**: separate. Same reasoning as Q-A1.2.

### Q-A1.4 — Mode-agnostic manifest (item #3)

The `includes-events.yml` / `includes.yml` split is still active in `_load_manifest`. The TRD (§6.5) says one mode-agnostic manifest. This is technically PRD-D's scope (wake-mode), but A6's CLI work touches the same code paths. Should A6 absorb the manifest unification?

**Recommendation**: leave to PRD-D. A6 should not touch `_load_manifest`'s wake-mode branching; PRD-D refactors it.

---

## Recommended next moves

1. **Update PRD-A** with this drift report's findings. Specifically:
   - Correct §6 ("No new dependencies introduced") — substantial new code is required.
   - Re-scope A2 as a parent story; file 3–5 sub-stories under it (frontmatter parse, six-slot emitter, L4 H3 op processor, validation gates, etc.).
   - File A2.5 (L4 migration) and A2.6 (L1-L3 frontmatter migration) as separate tasks.
   - Mark A3 and A4 as **depends-on-A2** (don't start until A2 has slot grammar working).
2. **Get human direction on Q-A1.1** (reference-only sub-skill emission) — this is the single biggest architectural pivot in the v1→v2 transition.
3. **Hold #10385–#10389 at status:pending** until PM updates the bodies. Skill should not pick them up against the current (now-known-stale) bodies.

---

## References

- TRD: [[COMPOSE-ARCHITECTURE]] §3 + §4.1–§4.5 + §5 + §6.1–§6.4
- PRD: [[compose-link-stage]]
- Code: `references/scripts/compose.py` head `684b5629`
- Related: [[project_compose_freshness_harness_owned]] (the harness needs the new compose for its boot-time check to be meaningful), [[project_assemble_unconditional]] (PRD-B context)
