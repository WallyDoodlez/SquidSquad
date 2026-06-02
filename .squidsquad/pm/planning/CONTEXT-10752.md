# BUG: PRD-B (compose assemble stage) — DS audit findings

**Source**: DeepSeek code review of landed PRD-B stories (B1–B8) vs spec.
**PRD spec**: `docs/prd/compose-assemble-stage.md`
**Audit doc**: `.squidsquad/pm/planning/AUDIT-PRD-B-DS-REVIEW.md`
**Verdict**: **FAIL** — 3 ERRORS + 4 WARNINGS. PRD-B is structurally dead in the production path.

## ERROR 1 — Assemble pass never wired into compose pipeline (B1, B7 — dead code)

- **File**: `references/scripts/compose.py:1569` (end of `deploy_alias_v2`); throughout `main()`
- **Severity**: error
- **Issue**: `atomic_emit.assemble_and_emit` is never imported or called from `compose.py`. `deploy_alias_v2` writes `CLAUDE.linked.v2.md` and stops — it never runs assemble afterward. `deploy_role` has no v2 assemble hook. The full B1–B7 pipeline exists as standalone modules but is dead code with no caller in the compose flow.
- **Evidence**: SC1 = *"The assemble pass runs unconditionally after the link stage on every `compose.py deploy <alias>` and `deploy-all`"*. Grep confirms zero imports of `atomic_emit`, `assemble_pass`, or `assemble_and_emit` from `compose.py`.
- **Stories implicated**: B1 (#10444), B7 (#10447), and effectively all of B1–B7 (cumulatively never invoked)
- **Suggested fix**: in `deploy_alias_v2`, after `emit_v2_linked` succeeds, call `assemble_and_emit` with the linked composite and the alias's output dir. Wire up the real `assemble_cache.cache_lookup` / `cache_store` as the injection seams (with an adapter mapping `(slot, linked_body) → cache_key() → real cache I/O`). Gate behind the `--v2` flag per §9a.

## ERROR 2 — atomic_emit writes to v1 paths, violating §9a coexistence (B7)

- **File**: `references/scripts/atomic_emit.py:389-394`
- **Severity**: error
- **Issue**: `_atomic_write_triple` writes to `CLAUDE.md`, `CLAUDE.linked.md`, `CLAUDE.conflicts.md` — the **canonical v1 paths**. PRD-B §9a requires v2 paths: `CLAUDE.v2.md`, `CLAUDE.linked.v2.md`, `CLAUDE.conflicts.v2.md`. Writing to `CLAUDE.md` would overwrite the v1 runtime contract, breaking both *"No PRD-B PR shall modify v1 output path or its bytes"* and *"No PRD-B PR shall break the v1 compose pipeline"*.
- **Stories implicated**: B7 (#10447)
- **Suggested fix**: change the target filenames in `_atomic_write_triple` (lines 389-391) to `CLAUDE.v2.md`, `CLAUDE.linked.v2.md`, `CLAUDE.conflicts.v2.md`. Caller should pass v2 filenames OR the triple should be parameterized (see WARNING 3 below).

## ERROR 3 — Assemble model not locked to sonnet; no temperature cap (B1)

- **File**: `references/scripts/model_router.py:119-150` (`get_model_for_task`)
- **Severity**: error
- **Issue**: Assemble model is read from config (`assemble-model` key), not hardcoded as `sonnet`. SC10 = *"Model: `sonnet` (compose-time constant; not config) at temperature ≤ 0.3"*. The `key_map` has no `"assemble"` entry, so the task type falls through to `"assemble-model"` resolved from `config.md` routing. If `config.md` has no `assemble-model` entry, it falls further through to `"default-model"` or `"claude"`. Additionally, "temperature" does not appear anywhere in `model_router.py`.
- **Stories implicated**: B1 (#10444)
- **Suggested fix**: add `"assemble": "sonnet"` to `CLAUDE_LOCKED_TASKS` OR add a hardcoded early-return in `get_model_for_task` for `task_type == "assemble"` returning `"sonnet"`. Add `temperature ≤ 0.3` in the provider adapter call for the assemble task type.

## WARNING 1 — Preservation verifier incomplete (B2 — SC3 partially satisfied)

- **File**: `references/scripts/assemble_verifier.py:66-85` (`verify_preservation`)
- **Severity**: warning
- **Issue**: SC3 lists FOUR preservation items (sub-skill refs, step IDs, fenced code blocks + bash/python invocations content, file paths). The verifier covers only sub-skill (#1), step IDs (#2), and fenced-block count (±10% parity, not content) (#3 count-only). **Item #3 content** ("preserved verbatim") and **item #4 (file paths)** are not checked. `check_code_block_parity` counts fence pairs but never compares actual code-block bodies.
- **Stories implicated**: B2 (#10441)
- **Suggested fix**: add `verify_fenced_block_content(linked, assembled)` that extracts all fenced blocks from both texts and asserts multiset equality of `(lang_tag, body)` tuples. Add `verify_file_paths(linked, assembled)` using a regex for file paths (e.g. `[\w/.-]+\.[a-z]{1,6}` in prose) and checks multiset equality.

## WARNING 2 — B6 cache layer signature mismatch with B7 (no adapter)

- **File**: `references/scripts/atomic_emit.py:116-117, 134-135, 224`
- **Severity**: warning
- **Issue**: Cache injection seams (`cache_lookup_fn`, `cache_store_fn`) have signatures incompatible with the real `assemble_cache` module, and `assemble_cache` is never imported. B6's cache layer cannot be connected to B7's pipeline without an adapter.
- **Detail**: Seams expect `cache_lookup_fn(slot, linked_slot_body) -> str | None` / `cache_store_fn(slot, linked_slot_body, assembled_llm_output)`. Real API is `cache_lookup(alias, key, *, slot_name=None)` / `cache_store(alias, key, assembled_body)`, where `key = cache_key(linked_body, slot_name, slot_purpose, model_id, prompt_version)`. No code in `atomic_emit.py` computes `cache_key()` or passes `slot_purpose`/`model_id`/`prompt_version` to the cache layer.
- **Stories implicated**: B6 (#10443), B7 (#10447)
- **Suggested fix**: create an adapter that (a) computes `cache_key(linked_body, slot_name, slot_purpose, model_id, prompt_version)` inside `assemble_and_emit`, (b) wraps `assemble_cache.cache_lookup(alias, key, slot_name=slot)` and `assemble_cache.cache_store(alias, key, llm_output)` into the seam signatures, (c) passes `alias`, `model_id`, `prompt_version` (hash of `assemble.md.j2`) as new parameters to `assemble_and_emit`.

## WARNING 3 — `_atomic_write_triple` hardcoded filenames, no parameterization

- **File**: `references/scripts/atomic_emit.py:389-394`
- **Severity**: warning
- **Issue**: Target filenames are string literals at lines 389-391 with no function parameter to override. `assemble_and_emit` signature takes `output_dir` but no filename prefix/suffix parameter. Even if ERROR 2 is fixed by changing the literals, the function should accept configurable target names for testability and future flexibility (e.g., the eventual atomic switch PR).
- **Stories implicated**: B7 (#10447)
- **Suggested fix**: add `filename_suffix` parameter to `assemble_and_emit` (default `".v2.md"` per §9a; empty for atomic switch PR). Construct target filenames as `f"CLAUDE{filename_suffix}"`, `f"CLAUDE.linked{filename_suffix}"`, `f"CLAUDE.conflicts{filename_suffix}"`.

## WARNING 4 — LLM context string omits preservation directives

- **File**: `references/scripts/assemble_pass.py:78-83`
- **Severity**: warning
- **Issue**: The `context` string passed to `model_router.route` mentions only sub-skill and step-ID preservation, omitting file-path and fenced-code-block content preservation. The template's `{{ context }}` placeholder carries this text — the LLM sees this abbreviated instruction alongside the fuller template rules. Could weaken attention to all SC3 guarantees.
- **Stories implicated**: B1 (#10444)
- **Suggested fix**: extend the context string to read *"preserve all fenced code blocks verbatim (content + count), all file paths, and every sub-skill and step:cycle/<id> reference"* to match the full SC3 set.

## Recommended fix order

1. **ERROR 1** first — wires the entire pipeline together. Until this lands, all of B1–B7 are unreachable code, and ERRORS 2 and 3 are moot.
2. **ERROR 2** second — must be coupled with ERROR 1 to keep §9a coexistence intact (writing to v1 paths the moment the pipeline goes live would corrupt every existing install).
3. **ERROR 3** third — once the pipeline is wired and writing to the right place, lock the model + temperature so output is deterministic.
4. **WARNING 1** (B2 preservation) — strengthens correctness checks before the cutover.
5. **WARNING 2** (B6 cache adapter) — required for cache to actually work; needed for SC9 (cache hit rate).
6. **WARNING 3** (parameterize filenames) — paired with the eventual atomic switch PR.
7. **WARNING 4** (LLM context) — quality polish on the prompt.

## Notes

- **PRD-B is the most critical of the three audits.** All 3 errors must be fixed before E6 (V2 CUTOVER #10685) can ship — otherwise cutover exposes the dead pipeline (zero assemble) and would silently overwrite v1 outputs.
- Stories B4 (conflict detection) and B5 (higher-L-wins resolver) have no direct errors flagged by DS — they appear sound but are also unreachable until ERROR 1 is fixed.
- DS evidence is in `AUDIT-PRD-B-DS-REVIEW.md`.
