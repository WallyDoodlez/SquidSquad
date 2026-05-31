# PRD D — Sub-Skill Catalog Gate + Wake-Mode Handling

> **Status**: PRD draft, 2026-05-31. Derived from TRD [[COMPOSE-ARCHITECTURE]] §4.5 (sub-skill reference resolution + catalog gate) + §6.5 (wake-mode handling — one manifest, boot-probe selection). Part of the COMPOSE-ARCH PRD slice family: A (link) / B (assemble) / C (L4 customization) / D (this) / E (compose freshness).
>
> **Scope:** two coupled v1→v2 pivots that share a TRD chapter:
> 1. **Sub-skill catalog gate** — composed `CLAUDE.md` emits `→ run sub-skill: <name>` references instead of inlining sub-skill bodies; the catalog (`docs/sub-skill-catalog.md`) is the authoritative gate; agents resolve references at runtime
> 2. **Wake-mode unification** — one mode-agnostic manifest (`includes.yml`) per role-class; the `event-driven:` config field is retired; wake mode is selected at agent boot via harness probe ([[AGENT-RUNTIME]] §8.3)
>
> Excludes link-stage mechanics (PRD A), the LLM assemble pass (PRD B), runtime L4 writes (PRD C), and harness-owned freshness (PRD E).

---

## 1. Goal

Today's `compose.py` makes two architectural choices that the TRD retires:

1. **Inline sub-skill bodies** — every sub-skill referenced in `includes.yml` is read at compose time and its full body is concatenated into the output `CLAUDE.md`. Result: each agent boots with hundreds of KB of inlined procedures, and every change to any sub-skill source forces a fresh compose for every role-class.
2. **Wake-mode-split manifest** — `includes.yml` for polling, `includes-events.yml` for event-driven; `compose.py` picks the manifest based on a `config.md` field. Result: every install carries duplicate manifests, mode change requires recompose + restart ceremony, and event/loop divergence is invisible until runtime.

PRD-D delivers v2's reference-and-catalog model (small CLAUDE.md, runtime resolution, single source of truth for each sub-skill) plus the mode-agnostic manifest (one file per role-class, wake-mode probe at boot per [[AGENT-RUNTIME]] §8.3, no operator ceremony to flip modes).

## 2. User-facing outcomes

| Persona | Outcome |
|---|---|
| **Runtime agent reading its `CLAUDE.md`** | Instructions slot shows `→ run sub-skill: <name>` references; bodies live in `references/sub-skills/<name>.md` (or future `.claude/skills/<name>/SKILL.md` per #10362). Agent reads the source at the point it executes the step, not at boot. |
| **Developer authoring a new sub-skill** | Adds the file under `references/sub-skills/` AND adds a catalog row in `docs/sub-skill-catalog.md`. Compose's drift check enforces both sides — orphan file (no catalog entry) or orphan catalog row (no file) aborts compose. |
| **Operator changing `Iteration Interval` or any other config field** | No more `event-driven:` to set — wake mode is decided by the agent's own boot probe each session. To change modes, stop the harness (forces loop mode on next boot) or start it (event mode on next boot). |
| **Operator pulling a SquidSquad upgrade** | One manifest per role-class to maintain; no duplicate `includes-events.yml` to keep in sync. |
| **Reviewer of a sub-skill source change** | A change in `references/sub-skills/<name>.md` no longer requires regenerating every agent's CLAUDE.md — agents pick up the change at runtime on their next cycle. (Recompose is still triggered for L1-L3 changes per PRD-E, but the regenerated CLAUDE.md is bytes-stable except where the reference list itself changed.) |

## 3. Success criteria

PRD-D is "done" when ALL of the following hold:

1. **Composed `CLAUDE.md` emits sub-skill references, not bodies.** Every entry that v1 would have inlined as a `<!-- sub-skill: foo -->` block now appears in the `instructions` slot as `→ run sub-skill: foo` (grammar locked in TRD §6.2).
2. **Catalog is the authoritative gate.** Every `→ run sub-skill: <name>` in the composed output has a matching row in `docs/sub-skill-catalog.md`. Compose aborts on any unresolved reference.
3. **Catalog row source-path well-formedness.** Every catalog row's `source-path` value is a syntactically valid relative path rooted at `references/sub-skills/`, with no path traversal segments. Malformed row → abort with diagnostic naming the row. (Catalog `source-path` is always the *authored* source location; `.claude/skills/` is an install artifact materialized per #10362 and is NEVER referenced by a catalog row — see TRD §4.5.1.)
4. **Catalog drift check.** Compose emits a complete drift report listing (a) catalog rows whose recorded source file is missing on disk and (b) source files under `references/sub-skills/` that have no catalog row. Then aborts (drift = abort, not warn-and-continue). This subsumes the on-disk existence check for catalog rows.
5. **Runtime resolution path.** An agent encountering `→ run sub-skill: <name>` in its `CLAUDE.md` resolves it by reading the catalog-recorded source file and treating its content as the procedure to execute. Today's mechanism is "read the file"; future mechanism (per #10362) is "invoke via Skill tool"; the reference grammar in `CLAUDE.md` is unchanged across that future shift.
6. **One manifest per role-class.** After the v2 switch PR (E6), `references/roles/<role>/includes.yml` is the only manifest and `includes-events.yml` no longer exists. During the transition (D5 through E5), a new unified `includes-v2.yml` coexists alongside the existing `includes.yml` and `includes-events.yml`; v2 compose reads `includes-v2.yml`; v1 compose continues reading its existing manifests untouched.
7. **Wake-mode selection is runtime-only.** `compose.py` no longer reads `event-driven:` from `config.md`. The composed `CLAUDE.md` is identical regardless of which wake mode the agent will eventually use; mode is selected by the agent's boot probe ([[AGENT-RUNTIME]] §8.3).
8. **`config.md` no longer has an `event-driven:` field.** Installer (PRD-A scope edge, see §6 dependencies) and `config.py` reject any read of that field — either ignored silently (preferred) or returns a deprecation warning + default.
9. **Sub-skill catalog parser** (`docs/sub-skill-catalog.md` reader) is implemented and used by compose's reference-resolution step.
10. **Composed `CLAUDE.md` size shrinks substantially.** Concrete success metric: post-D, an average v2 composed `CLAUDE.md` is at most 30% the byte size of its v1 counterpart (most content moves to lazily-read sub-skill files). Exact threshold finalized in story D2's reference-emission implementation, verified by PRD-A's golden-file test suite (A3).

## 4. Non-goals

- Link-stage mechanics (slot grammar, L4 ops, validation rules R1–R6) — [[compose-link-stage]] (PRD A).
- LLM assemble pass — [[compose-assemble-stage]] (PRD B).
- Runtime L4 write flow / `l4-curation` sub-skill — [[compose-l4-customization]] (PRD C).
- Harness boot-time freshness check, L4-write file-watch, operator `squidsquad_cli.py check` — PRD E.
- The project-scoped Claude-skills installer (#10362) that would materialize each catalog entry as a real `.claude/skills/<name>/SKILL.md`. PRD-D ships against the **current** runtime resolution (agent reads `references/sub-skills/<...>/<name>.md` directly); the installer is a deferred follow-up that does not affect PRD-D's compose-side contract.
- Migrating any existing `references/sub-skills/` source files to the future `.claude/skills/` layout — defer to #10362.

## 5. Architectural anchors

- **TRD §4.5** — Sub-skill reference resolution. The catalog-gated structure (catalog first, then source-path existence) is enforced sequentially: no "union of sources" allowed.
- **TRD §4.5.1** — Project-scoped Claude-skills installer gap (deferred, #10362). PRD-D acknowledges and ships against current resolution.
- **TRD §6.2** — Sub-skill reference grammar (`→ run sub-skill: <name>` text token).
- **TRD §6.5** — Wake-mode handling: one mode-agnostic manifest per role-class; boot-time selection; no compose-time manifest gate.
- **TRD §3.0 + §6.5** — Architectural retirement of the `event-driven:` config flag (config.md description of mode-agnostic compose + wake-mode handling section).
- **[[AGENT-RUNTIME]] §8.3** — Boot decision tree (probe + bind), the consumer side of the mode-agnostic compose contract.

## 6. Dependencies

| Dependency | From | Why |
|---|---|---|
| PRD-A: six-slot output emitter | [[compose-link-stage]] | The reference emission for sub-skills happens inside the `instructions` slot; needs the slot grammar in place |
| PRD-A: frontmatter parser | [[compose-link-stage]] | Sub-skill source files carry frontmatter (`slot:`, `ordinal:`); the catalog parser may also consume metadata from their frontmatter |
| `docs/sub-skill-catalog.md` exists and is human-curated | Existing | The catalog is the authoritative gate; its row schema is the contract D1 parses |
| Agents can read source files at runtime | [[AGENT-RUNTIME]] | Current behavior — agents already use Read tool for files; no new capability needed. Future #10362 work changes this to Skill-tool invocation; PRD-D's compose contract is invariant to that change |
| `config.py` accepts removal of the `event-driven:` field without breaking other consumers | Existing | D6 audits `config.py` and any caller still reading the field (executed in the E6 switch-PR window per §9a) |

## 7. Story breakdown (proposed)

| # | Story | TRD anchor | Effort | Notes |
|---|---|---|---|---|
| **D1** | Catalog parser — read `docs/sub-skill-catalog.md`, return `{name: source_path}` dict; abort on malformed row | §4.5 + §6.2 | M | First, foundational — D2–D4 all consume it |
| **D2** | Switch v2 link-stage instructions-slot emission from inline bodies to `→ run sub-skill: <name>` references | §4.5 + §6.2 | L | Biggest pivot; gated on PRD-A's six-slot emitter |
| **D3** | Catalog gate in v2 compose — every emitted reference resolves via D1's parser; abort on unresolved name | §4.5 step 2/3 | M | Couples with D2 |
| **D4** | Catalog drift check — for every catalog row, source file exists; for every `references/sub-skills/*.md`, catalog row exists. Full drift report then abort | §4.5 step 4 | M | Independent of D2/D3; can land in parallel |
| **D5** | Unify manifest **(two-step, additive only in D5 — actual deletion is in E6)**: introduce `references/roles/<role>/includes-v2.yml` alongside the existing `includes.yml` / `includes-events.yml`. v2 compose reads the v2 manifest; v1 compose continues reading its existing manifests untouched. v2's `_load_manifest_v2` takes no `wake_mode` argument; v1's `_load_manifest` is preserved. **Deletion of `includes-events.yml` and rename of `includes-v2.yml` → `includes.yml` happens in E6 switch PR.** | §6.5 | M | Mechanical but careful — D5 must NOT touch existing files in any way that v1 compose can observe |
| **D6** | Remove `event-driven:` from `config.md` schema; update `config.py` to reject the field (or silently ignore). Installer wizard (out of band) also drops the question. **Executes in the E6 switch-PR window per §9a — not before.** | §3.0 + §6.5 | S | Last step — most other agents already aren't reading it |
| **D7** | Comprehension test — fresh agent given a v2-composed CLAUDE.md must correctly identify how to execute `→ run sub-skill: foo` (read the catalog-recorded source file) | `feedback_comprehension_tests_required` | M | Standard for any change to agent instruction surface |
| **D8** | Sub-skill catalog row schema validation — every row has `name`, `source-path`, `description`, plus any other locked columns | §4.5 (catalog as authoritative gate) | S | D1 reads rows; D8 enforces schema; can fold into D1 if cheap |

Effort scale: S = 1–2 days, M = 3–5 days, L = 1+ week.

**Recommended pickup order** (lowest risk first, respects dependencies):

1. **D1** (parser — pure read; no compose changes yet)
2. **D8** (catalog schema validation — pure check; can fold into D1)
3. **D4** (drift check — pure read across two trees)
4. **D5** (manifest unification — mechanical, isolatable from D2/D3)
5. **D2** (reference emission — gated on PRD-A slot grammar)
6. **D3** (catalog gate at compose time — gated on D2)
7. **D7** (comprehension tests — after D2/D3 stabilize)
8. **D6** (config cleanup — last; most invasive to surrounding tooling)

## 8. Open questions for this PRD

| # | Question | Resolution path |
|---|---|---|
| Q-D1 | Catalog row schema — what columns are required? At minimum `name` + `source-path`; should we also lock `description`, `role-scope` (which role-classes may reference this), `slot` (which slot the reference may appear in)? | Decide in D1 / D8 — recommend minimum `name`, `source-path`, `description`; defer `role-scope` and `slot` enforcement to a follow-up PRD if needed |
| Q-D2 | Does the v2 composed CLAUDE.md inline ANY sub-skill content (e.g., a short bootstrap step), or are ALL sub-skills referenced? | Decide in D2 — recommend a hard rule: zero inlined sub-skill bodies in v2. The Boot block currently inlined as the first instruction of CLAUDE.md is a candidate to extract into its own sub-skill |
| Q-D3 | If a sub-skill is referenced but has zero call sites in any role's `includes.yml`, is it dead code? | Decide in D4 — recommend dead-code report (warn, not abort). Useful but not blocking |
| Q-D4 | `includes-events.yml` removal — when and how? | Locked: two-step per §9a — D5 introduces `includes-v2.yml` alongside existing files (no deletion); E6 switch PR deletes `includes-events.yml` and renames `includes-v2.yml` → `includes.yml` atomically. No symlink legacy. |
| Q-D5 | Should D7's comprehension test be a full CQ spec (per `feedback_comprehension_tests_required`) or can the verifier author it from the AC list? | Decide in D7 — per [[feedback_test_workflow_separation]], PM defines the AC + the comprehension AC; QA writes the CQ spec at verification time. So: AC in PRD-D, CQ spec produced by QA |

## 9. Out of scope — explicit list

For traceability, these belong to other PRDs / future work:

- Link-stage slot grammar + ordinal sorting ([[compose-link-stage]] / TRD §3.1)
- L4 H3 op processor ([[compose-link-stage]] / TRD §3.3)
- Validation rules R1–R6 ([[compose-link-stage]] / TRD §3.3 success criterion 6)
- Assemble pass conflict report ([[compose-assemble-stage]] / TRD §4.6)
- `l4-curation` sub-skill and runtime L4 writes ([[compose-l4-customization]] / TRD §7)
- Harness boot-time freshness check, L4-write file-watch, operator `squidsquad_cli.py check` (PRD-E / TRD §8)
- Project-scoped Claude-skills installer (#10362) — defers to a follow-up that does NOT change PRD-D's compose-side contract

## 9a. Coexistence with v1 — no broken installs during the transition

**Family-wide constraint** (applies to all PRDs A–E): the existing v1 `.squidsquad/<alias>/CLAUDE.md` MUST remain the runtime contract until the family-wide **v2 switch PR** ships. No PRD-D PR is allowed to:

1. Modify the v1 output path (`.squidsquad/<alias>/CLAUDE.md`) or its bytes
2. Break the v1 compose pipeline — existing `compose.py deploy <role>` must keep producing byte-identical v1 output as v2 code lands
3. Switch ANY runtime resolution from inline-body to reference until the switch PR ships

**PRD-D-specific application** (this is where v1 vs v2 diverges most sharply — careful):

- **D1, D4, D8** (catalog parser, drift check, schema validation) — pure read-only modules; can land at any time without touching v1.
- **D2, D3** (reference emission + gate) — these change the SHAPE of v2 compose output. Implement against the v2 output path (`CLAUDE.linked.v2.md` → `CLAUDE.v2.md`). v1 inline-body emission stays untouched in the v1 code path. Two compose pipelines coexist; the default points at v1.
- **D5** (manifest unification) — risky because it touches the same files v1 reads. Two-step approach:
  1. First commit: introduce a NEW unified manifest `includes-v2.yml` alongside the existing `includes.yml` / `includes-events.yml`. v2 compose reads the v2 manifest; v1 compose continues reading its existing manifests untouched.
  2. Switch PR (later, family-wide): rename `includes-v2.yml` to `includes.yml`, delete `includes-events.yml`, in one atomic change.
- **D6** (drop `event-driven:` from `config.md`) — this is a switch-PR-only change. Until the switch, the field stays in `config.md` even though v2 compose doesn't read it (v1 still reads it via `_get_wake_mode`, per A1 audit).
- **D7** (comprehension test) — tests the v2 composed output, not v1.

**The size-shrink metric (criterion 10) applies to the v2 output**, not v1. v1 byte size stays constant during the transition.

**CI regression guard**: every D-story PR must regenerate v1 `compose.py deploy-all` output and confirm byte-identical to pre-PR. The v2 path is observed via a separate test run that asserts the v2 output meets D2/D3/D4 contracts.

Loop-mode fallback during the switch is automatic per [[AGENT-RUNTIME]] §8.3 boot probe — no new mechanism needed.

## 10. Acceptance

This PRD is "done" when:

- All 8 stories (D1–D8) have shipped or been explicitly deferred (with rationale + target).
- The 10 success criteria above are demonstrably met against v2 compose output (v1 untouched).
- A composed v2 CLAUDE.md for at least one role-class shows the size-shrink (≥70% reduction vs v1) and runs successfully through PRD-A's link stage + PRD-B's assemble stage end-to-end.
- A fresh agent given a v2 CLAUDE.md correctly identifies how to execute a `→ run sub-skill: foo` reference (per D7).
- `references/roles/<role>/includes-events.yml` files no longer exist (D5 cleanup; per the coexistence plan, this happens in the switch PR, not in D5 itself).
- `event-driven:` field is absent from `config.md` after the switch PR (per D6).

## 11. References

- TRD: [[COMPOSE-ARCHITECTURE]] (canonical spec — §3.0 + §4.5 + §4.5.1 + §6.2 + §6.5)
- Sibling architecture: [[AGENT-RUNTIME]] (§8.3 boot probe, the consumer side of mode-agnostic compose)
- Companion PRDs: [[compose-link-stage]] (A — slot grammar), [[compose-assemble-stage]] (B — assemble pass), [[compose-l4-customization]] (C — L4 write path), [[compose-freshness]] (E, forthcoming)
- Memory rules: [[project_event_mode_default]], [[project_compose_freshness_harness_owned]], [[project_assemble_unconditional]], [[project_trd_prd_delivery_model]]
- Existing follow-up: [#10362](https://github.com/WallyDoodlez/SquidSquad/issues/10362) — project-scoped Claude-skills installer (out-of-scope; PRD-D ships against current resolution)
