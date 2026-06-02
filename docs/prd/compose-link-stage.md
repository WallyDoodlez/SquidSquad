# PRD A — Compose Link Stage

> **Status**: PRD draft, 2026-05-30. Derived from TRD [[COMPOSE-ARCHITECTURE]] §1–§6 (link stage). Part of the COMPOSE-ARCH PRD slice family: A (this) / B (assemble) / C (L4 + l4-curation) / D (catalog + wake-mode) / E (harness-owned freshness).
>
> **Scope:** the deterministic linking of L1–L4 source fragments into a single `.squidsquad/<alias>/CLAUDE.md` per agent instance. Excludes the LLM-driven assemble pass (PRD B), runtime L4 writes (PRD C), sub-skill catalog enforcement (PRD D), and harness-owned freshness (PRD E).

---

## 1. Goal

Operators of any SquidSquad install can run a single command (`compose.py deploy <alias>` or `compose.py deploy-all`) and get a **byte-stable, reviewable, single-file CLAUDE.md per agent instance** assembled deterministically from layered sources. Without the link stage, agents have no instruction artifact to boot against; with it, the rest of SquidSquad's compose pipeline (assemble, L4 ops, sub-skill resolution, freshness checks) becomes possible.

## 2. User-facing outcomes

| Persona | Outcome |
|---|---|
| **Operator running a fresh install** | `.squidsquad/<alias>/CLAUDE.md` is created for every alias in the team preset; agents boot against these files with no manual editing required. |
| **Operator running `compose.py deploy-all` after a source change** | Every alias's `CLAUDE.md` is regenerated; the same inputs produce the same outputs across runs (deterministic). |
| **Reviewer reading a PR that touches `references/sub-skills/`** | Can diff the regenerated `CLAUDE.md` against the pre-change version and see exactly what changed in the agent's instruction set. |
| **Developer authoring a new L2/L3 source fragment** | Knows where the fragment lands in the composed output (which `(slot, ordinal)` position) by inspecting frontmatter; no surprise reorderings. |
| **Developer authoring an L4 overlay** | Knows the per-slot legal ops (append / insert-before / insert-after / replace) and what L4 cannot do (e.g., touch the Vault slot). |

## 3. Success criteria

The link stage is "done" for PRD-A purposes when ALL of the following hold:

1. `compose.py deploy <alias>` produces `.squidsquad/<alias>/CLAUDE.md` from the alias's resolved (role-class, L3 domain) sources + the role-class L4 file. The alias-to-role-class resolution reads `.squidsquad/config.md` `## Aliases`.
2. `compose.py deploy-all` iterates the `## Aliases` registry and runs `deploy` per entry.
3. The composed output contains exactly the six canonical H2 slots in canonical order: `## Identity`, `## Responsibility`, `## Soul`, `## Instructions`, `## Project Context`, `## Vault`.
4. Within each slot, content is ordered by `(slot, ordinal)` from frontmatter — stable sort, gaps allowed.
5. L4 ops (append / insert-before step-id / insert-after step-id / replace step-id / replace whole-slot) apply deterministically per the §3.3 per-slot constraint table; invalid L4 ops abort compose with a clear diagnostic before any write.
6. Validation rules block invalid composition before any write:
   - L4 file with `## Vault` H2 → abort
   - L2/L3 source file with `slot: vault` frontmatter → abort
   - L1-L3 source file with `slot: project-context` frontmatter → abort
   - L4 `### append` block under `## Instructions` with no `→ run sub-skill: <name>` reference → abort
   - L4 op references a non-existent step ID → abort
   - Whole-slot `replace` mixed with other ops in the **same slot** → abort (per-slot scope, NOT per-file; a whole-slot `replace` on `## Responsibility` does NOT forbid `### append` blocks under `## Instructions` in the same file)
   - Two `### replace step:cycle/<id>` H3 blocks targeting the same step ID → abort (per TRD §4.2 step 3)
7. The composed output is byte-stable across re-runs given unchanged inputs (no timestamps, no random ordering, no in-memory pointer-derived strings).
8. The composed output preserves sub-skill references as `→ run sub-skill: <name>` text — sub-skill bodies are NOT inlined (the catalog-gate piece of this is PRD D's scope; this PRD only requires that references survive verbatim).

## 4. Non-goals

- LLM-driven assemble pass for prose coherence — that's PRD B.
- Runtime L4 writes (the `l4-curation` sub-skill) — that's PRD C.
- Sub-skill catalog enforcement (rejecting references to non-existent sub-skills) — that's PRD D.
- Boot-time freshness checks, auto-recompose on source change — that's PRD E.
- Conflict-resolution prose (when L1-L3 layers contradict each other) — explicitly the assemble pass's job (PRD B); link stage just emits the layered composite as-is.
- New L4 op types beyond the five locked in §3.3 — out of scope for this PRD.

## 5. Architectural anchors

These are the TRD sections this PRD draws on; no architectural decisions in this PRD — only delivery shaping.

- **TRD §1** — Path-keying terminology (alias-keyed output, role-class-keyed L4, role-class-typed L1-L3 sources).
- **TRD §3** — Authoring principles: L1-L4 layering, DRY + sub-skill catalog, six-slot grammar.
- **TRD §3.3** — Per-slot op constraints (the validation table this PRD implements).
- **TRD §4.1–§4.5** — Link-stage pipeline: walk → parse → filter → manifest-load → sort → L1-L3 base → L4 ops → validate → emit.
- **TRD §5** — Composed CLAUDE.md grammar: six canonical slots.
- **TRD §6.1–§6.4** — Step ID grammar (BNF) and flat numbering rule.

## 6. Dependencies

| Dependency | From | Why |
|---|---|---|
| `.squidsquad/config.md` `## Aliases` registry | [[COMPOSE-ARCHITECTURE]] §3.0 + [[INSTALLER-ARCH]] §4.8 step 3 (already shipped via installer) | Compose resolves alias → role-class via this registry. Required for `deploy <alias>`. |
| L1-L3 source tree under `references/sub-skills/` + `references/roles/` | [[COMPOSE-ARCHITECTURE]] §3.1 (already shipped) | The content compose reads. |
| L4 source tree at `.squidsquad/project/<role-class>.md` (optional per role-class) | [[COMPOSE-ARCHITECTURE]] §3.3 + [[INSTALLER-ARCH]] §4.8 step 4 (already shipped via installer) | If absent, L4 step is a no-op; if present, ops apply per §3.3. |
| Python 3.12+ + PyYAML | runtime environment | Frontmatter parsing. |

No new dependencies introduced by PRD A — the link stage already exists in `references/scripts/compose.py`.

## 7. Story breakdown (proposed)

Stories within this PRD. Each story = one deliverable PR or coherent commit set.

| # | Story | TRD anchor | Effort |
|---|---|---|---|
| **A1** | Verify current `compose.py` matches the §4.1–§4.5 link-stage spec; document any drift in the rev log; close gaps that are pure-implementation (no spec change) | §4.1–§4.5 | S |
| **A2** | Implement / verify all 6 validation rules listed in success criteria §3 above (Vault-rejection, project-context-rejection, append-with-sub-skill-ref, step-id resolution, mixed-op rejection) — code + tests for each | §3.3 | M |
| **A3** | Byte-stability tests: golden-file test suite that re-runs `deploy-all` against a fixture install and diffs against committed expected output | success-criterion 7 | S |
| **A4** | `compose.py deploy-all --check` mode: runs in-memory composition and exits 0/1 on diff against on-disk output (foundation for PRD E's freshness checks) | new | S |
| **A5** | `## Aliases` parser: read `config.md`'s registry table, return `{alias: (role_class, l3_domain)}` dict; abort with clear error on malformed table | TRD §3.0 schema | S |
| **A6** | Update existing `compose.py` CLI to accept alias (not role-class) and resolve via A5's parser; preserve `<role>` parameter name for code-compat per #10358 | TRD §1 path-keying | S |

Effort scale: S = 1–2 days, M = 3–5 days, L = 1+ week.

## 8. Open questions for this PRD

| # | Question | Resolution path |
|---|---|---|
| Q-A1 | Does `compose.py` today match the link-stage spec, or has it drifted? | Story A1 — audit current code vs §4.1–§4.5; report deltas. |
| Q-A2 | What's the golden-file fixture layout for A3's byte-stability tests? | Decide in A3 — likely under `tests/compose-fixtures/` with one fixture per role-class. |
| Q-A3 | How does `deploy-all --check` report drift — exit code only, or also a structured diff? | Decide in A4 — recommend exit code + stderr diff for CI-friendliness (consumed by PRD E's harness boot-check). |

## 9. Out of scope — explicit list

For clarity, the following items belong to other PRDs and should NOT slip into PRD A:

- LLM coherence rewrite of the linked body (PRD B / TRD §4.6)
- Conflict report format (PRD B / TRD §4.6)
- `l4-curation` sub-skill authoring (PRD C / TRD §7)
- Runtime L4 write flow + three-gate model (PRD C / TRD §7.2-§7.4)
- Sub-skill catalog gate (rejecting references to non-existent sub-skills) (PRD D / TRD §4.5)
- Wake-mode selection (boot probe, mode-agnostic manifest) (PRD D / TRD §6.5)
- Boot-time freshness check (PRD E / TRD §8.1)
- L4-write trigger for auto-recompose (PRD E / TRD §8.2)
- Operator `squidsquad_cli.py check` (PRD E / TRD §8.3)

## 9a. Coexistence with v1 — no broken installs during the transition

**Family-wide constraint** (applies to all PRDs A–E): the existing v1 `.squidsquad/<alias>/CLAUDE.md` MUST remain the runtime contract until the family-wide **v2 switch PR** ships at the end of the slice family. No PRD-A story-PR is allowed to:

1. Modify the v1 output path (`.squidsquad/<alias>/CLAUDE.md`) or its bytes
2. Break the v1 compose pipeline — existing `compose.py deploy <role>` must keep producing byte-identical v1 output as code lands
3. Land v2 link-stage code on the **default** path. v2 is opt-in (`compose.py deploy --v2 <alias>` or equivalent flag) until the switch PR

**Mechanism (family-wide)**:
- **v2 code lives side-by-side with v1.** New functions or a new module (e.g. `compose_v2.py`) sit next to `compose.py`. The switch is done by changing one default.
- **v2 outputs write to v2 paths.** PRD-A writes `.squidsquad/<alias>/CLAUDE.linked.v2.md` (the bare linked composite, since assemble is PRD-B). The final assembled CLAUDE.md lives at `.squidsquad/<alias>/CLAUDE.v2.md` once PRD-B B7 lands. The exact path convention is locked in PRD-A story A5 / A6 ahead of any v2-output writes.
- **CI regression on v1.** Every PR that touches `compose.py` must regenerate the v1 outputs and confirm byte-identical to pre-PR (a git-diff check against this repo's `.squidsquad/*/CLAUDE.md`). Catches accidental v1 regressions inside refactors.
- **Loop mode is the natural fallback during the switch.** Per [[AGENT-RUNTIME]] §8.3 the agent's boot probe selects wake mode per session; if event-mode integration goes intermittent during the switch window, agents naturally degrade to loop mode without operator action. No new mechanism needed.

**PRD-A-specific application**:
- A1 (audit) — read-only; no v1 risk.
- A2 (validation rules) — when implemented against v2 link stage; v2 path only.
- A3 (byte-stability tests) — runs against v2 outputs (`CLAUDE.linked.v2.md`) AND continues to verify v1 outputs unchanged (the dual-track regression check above).
- A4 (`deploy-all --check`) — operates on v1 paths initially (PRD-E's freshness consumer). A4.5 ships `--check --staged-l4` (staged-content R1-R7 validation for L4 writes), not the originally-planned `--check --v2` v2 drift check. A v2 drift check (in-memory v2 compose diff against on-disk `CLAUDE.linked.v2.md`) is NOT delivered by any landed PRD-A story; if needed it would be a follow-on under PRD-E or a new slice (see #10756 for triage trail).
- A5 (`## Aliases` parser) — additive new module; no v1 path touched. Existing v1 `Workers:` reading stays in place until the switch.
- A6 (CLI accepts alias) — adds `--v2` flag to opt into the new alias-keyed entrypoint; v1 `<role>`-keyed path remains the default.

**The v2 switch PR** (last in the family, after A/B/C/D/E story-PRs all land):

1. Renames v2 output paths to v1's canonical paths (`CLAUDE.v2.md` → `CLAUDE.md`).
2. Removes v1 compose code paths (`_assemble_claude`, the old `_resolve_includes`, multi-file L4 routing, manifest split).
3. Removes the `--v2` opt-in flag from CLI.
4. Updates this family's "Status" headers to `shipped`.

Operators with running installs see no behavior change until they pull the switch PR. Loop-mode fallback during the switch is automatic via the existing boot probe.

## 10. Acceptance

This PRD is "done" when:

- All 6 stories (A1–A6) have shipped or been explicitly deferred (with rationale + target PRD).
- The 8 success criteria above are demonstrably met (byte-stability tests pass; validation rules are exercised in CI).
- A reviewer can read this PRD top-to-bottom and identify what the link stage does, what it does NOT do, and where the boundaries to PRDs B-E sit.

## 11. References

- TRD: [[COMPOSE-ARCHITECTURE]] (canonical spec)
- Sibling architecture: [[AGENT-RUNTIME]], [[HARNESS-ARCH]], [[INSTALLER-ARCH]], [[VAULT-ARCH]]
- Companion PRDs (forthcoming): [[compose-assemble-stage]] (B), [[compose-l4-customization]] (C), [[compose-catalog-and-wake-mode]] (D), [[compose-freshness]] (E)
- Memory rules: [[project_trd_prd_delivery_model]], [[project_compose_freshness_harness_owned]]
