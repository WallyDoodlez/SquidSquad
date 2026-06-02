# TASK: PRD-B / Story B9 — Wire B1-B7 assemble pipeline into deploy_alias_v2

**Source**: #10754 (PRD-B SC1 unmet — assemble pipeline is dead code in production path).
**Parent PRD**: `docs/prd/compose-assemble-stage.md` (SC1: *"The assemble pass runs unconditionally after the link stage on every `compose.py deploy <alias>` and `deploy-all`"*).
**Hard pre-req for**: E6 #10685 (V2 CUTOVER). E6 cannot ship until B9 is shipped.

## Scope

Wire the existing B1–B7 modules into the v2 compose flow so PRD-B SC1 is actually satisfied.

**In scope:**
- `compose.py:deploy_alias_v2` calls `atomic_emit.assemble_and_emit` after `emit_v2_linked` succeeds, gated behind the v2 path (§9a coexistence).
- Adapter between B7's seam signatures (`cache_lookup_fn(slot, linked_slot_body)`, `cache_store_fn(slot, linked_slot_body, assembled_llm_output)`) and B6's real cache API (`cache_lookup(alias, key, *, slot_name=None)`, `cache_store(alias, key, assembled_body)`). Adapter computes `cache_key(linked_body, slot_name, slot_purpose, model_id, prompt_version)` and threads `alias`, `model_id`, `prompt_version` through.
- Path-naming: outputs go to `CLAUDE.v2.md`, `CLAUDE.linked.v2.md`, `CLAUDE.conflicts.v2.md` (per §9a). Parameterize `_atomic_write_triple` to accept a filename suffix (default `.v2.md`; empty for the eventual atomic switch PR).
- Model + temperature lock: assemble task type returns `sonnet` as compose-time constant (not config); temperature ≤ 0.3 enforced in the provider adapter call.
- `deploy_role` v2 path also wired (not just `deploy_alias_v2`).

**Out of scope** (these belong to follow-on bug fixes after B9 lands):
- The B2 verifier extensions (file paths, fenced-block content) — #10752 WARNING 1
- The LLM context string fix — #10752 WARNING 4
- The atomic switch PR that flips defaults (lands as part of E6)

## Why a single B9 instead of amending E6 (#10754 option a vs b)

- E6 is already a complex atomic PR (path renames + deletions + flag drops + PRD status updates). Bundling wiring raises revert blast radius.
- B9 lands inside §9a coexistence (writes to v2 paths only) — completely safe to merge before E6.
- E6's AC8 smoke test ("`compose.py deploy-all` produces v2 outputs at v1 paths") becomes honestly testable once B9 ships.

## Acceptance Criteria

1. **AC1** — `compose.py deploy <alias> --v2` and `compose.py deploy-all --v2` invoke `atomic_emit.assemble_and_emit` for every alias, after `emit_v2_linked` succeeds. Verified by a fresh end-to-end test that runs `deploy <alias> --v2` against a minimal install and asserts that the produced `CLAUDE.v2.md` differs from `CLAUDE.linked.v2.md` (assemble actually ran and rewrote slots).
2. **AC2** — Outputs land at `CLAUDE.v2.md`, `CLAUDE.linked.v2.md`, `CLAUDE.conflicts.v2.md`. Verified by file-existence + grep that NONE of these v2 paths' bytes are written to `CLAUDE.md`, `CLAUDE.linked.md`, `CLAUDE.conflicts.md` (the v1 paths). §9a coexistence is intact.
3. **AC3** — `_atomic_write_triple` accepts a `filename_suffix` parameter (default `.v2.md`, empty supported). Verified by a unit test that calls it with `filename_suffix=""` and asserts targets land at v1 paths (this is the seam E6 will use for the atomic switch).
4. **AC4** — B6 cache layer is wired through an adapter that computes `cache_key(linked_body, slot_name, slot_purpose, model_id, prompt_version)` and calls `assemble_cache.cache_lookup(alias, key, slot_name=slot)` / `cache_store(alias, key, assembled_body)`. Verified by a cache-hit integration test: same input → second `deploy_alias_v2` invocation reads from cache (no LLM call, identical output).
5. **AC5** — `model_router.get_model_for_task("assemble")` returns `"sonnet"` as a compose-time constant, NOT resolved from `config.md`. Verified by a unit test that asserts the return value is `"sonnet"` regardless of `config.md` `assemble-model` value (including absent).
6. **AC6** — Temperature ≤ 0.3 is enforced in the provider adapter call for the assemble task type. Verified by an integration test that captures the provider call args (or mocks the adapter) and asserts `temperature ≤ 0.3`.
7. **AC7** — `deploy_role` v2 path is also wired. Verified by direct invocation of `deploy_role(role, v2=True)` producing an assembled output.
8. **AC8** — `python tests/run_tests.py` passes with zero failures.
9. **AC9** — Pre-merge DS code review via `python references/scripts/model_router.py code-review --task-id "B9" --input-files "<diff>" --output-file ".squidsquad/skill/planning/CODE-REVIEW-B9.md"`. Artifact exists + cited in PR description. Findings processed per standard template (fix locally; file to PM if structural).

## Implementation hint (skill discretion — not locked)

The simplest landing point is the end of `deploy_alias_v2` (around `compose.py:1569`), immediately after `emit_v2_linked` writes `CLAUDE.linked.v2.md`. Read the just-written linked composite, pass it to `assemble_and_emit` along with the adapter-wrapped cache seams, the alias-derived `output_dir`, and the locked `(model="sonnet", temperature=0.3)` parameters. The atomic-emit triple writes `CLAUDE.v2.md` + `CLAUDE.linked.v2.md` + `CLAUDE.conflicts.v2.md` at the alias path.

## Notes

- This is the unblock work — completes the dead pipeline so PRD-B's other ERROR/WARNING findings (in #10752) become testable and fixable.
- After B9 ships, skill should re-evaluate #10752 — most of its findings will either be already-resolved as side effects of B9 OR become straightforward small fixes.
- E6 #10685 has `role:skill` removed + `blocked:pm-coordination` label. **Release condition**: B9 + #10752 both shipped. PM re-applies `role:skill` and removes blocked labels at that point.
