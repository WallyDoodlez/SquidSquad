Now I have a complete picture. Let me compile all findings.

---

### Finding 1

- **File**: `references/scripts/compose.py`
- **Line**: 1569 (end of `deploy_alias_v2`), and throughout `main()`
- **Severity**: error
- **Issue**: The assemble pass is never wired into the compose pipeline. `atomic_emit.assemble_and_emit` is never imported or called from `compose.py`. `deploy_alias_v2` (line 1569) writes `CLAUDE.linked.v2.md` and stops — it never runs assemble afterward. The `deploy_role` path has no v2 assemble hook either.
- **Evidence**: SC1 states *"The assemble pass runs unconditionally after the link stage on every `compose.py deploy <alias>` and `deploy-all`"*. Grep confirms zero imports of `atomic_emit`, `assemble_pass`, or `assemble_and_emit` from `compose.py`. The full B1-B7 pipeline exists as standalone modules but is dead code with no caller in the compose flow.
- **Suggested fix**: In `deploy_alias_v2`, after `emit_v2_linked` succeeds, call `assemble_and_emit` with the linked composite and the alias's output dir. Wire up the real `assemble_cache.cache_lookup`/`cache_store` as the injection seams (with an adapter mapping `(slot, linked_body)` → `cache_key()` → real cache I/O). Gate this behind the `--v2` flag per §9a.

### Finding 2

- **File**: `references/scripts/atomic_emit.py`
- **Line**: 389–394
- **Severity**: error
- **Issue**: The atomic emit writes to `CLAUDE.md`, `CLAUDE.linked.md`, `CLAUDE.conflicts.md` — the canonical v1 paths. This directly violates PRD-B §9a coexistence, which states outputs MUST go to v2 paths (`CLAUDE.v2.md`, `CLAUDE.linked.v2.md`, `CLAUDE.conflicts.v2.md`).
- **Evidence**: §9a says *"Output goes to a v2 path (e.g. `.squidsquad/<alias>/CLAUDE.v2.md` + sibling `CLAUDE.linked.v2.md` + `CLAUDE.conflicts.v2.md`) — NOT to the v1 `CLAUDE.md`."* and *"No PRD-B PR is allowed to: 1. Modify the v1 output path or its bytes 2. Break the v1 compose pipeline".* Writing to `CLAUDE.md` would overwrite the v1 runtime contract, breaking both rules simultaneously.
- **Suggested fix**: Change the target filenames in `_atomic_write_triple` (lines 389–391) to `CLAUDE.v2.md`, `CLAUDE.linked.v2.md`, `CLAUDE.conflicts.v2.md`. The caller (`compose.py`) should pass the v2 filenames, or the triple should be parameterized.

### Finding 3

- **File**: `references/scripts/model_router.py`
- **Line**: 119–150 (`get_model_for_task`)
- **Severity**: error
- **Issue**: The assemble model is read from config (`assemble-model` key), not hardcoded as `sonnet`. PRD-B SC10 states *"Model: `sonnet` (compose-time constant; not config) at temperature ≤ 0.3"*. Additionally, there is no temperature cap enforced anywhere — the word "temperature" does not appear in `model_router.py`.
- **Evidence**: SC10 says model is a *"compose-time constant; not config"*. The `key_map` at line 137–145 has no `"assemble"` entry, so the task type falls through to `f"{task_type}-model"` = `"assemble-model"`, resolved from `config.md` routing. If `config.md` has no `assemble-model` entry, it falls through to `"default-model"` or `"claude"`. A grep for "temperature" in `model_router.py` returns zero matches.
- **Suggested fix**: Add `"assemble": "sonnet"` to the `CLAUDE_LOCKED_TASKS` set or add a hardcoded early-return in `get_model_for_task` for `task_type == "assemble"` returning `"sonnet"`. Add a temperature parameter (`max_tokens` or `temperature`) ≤ 0.3 in the provider adapter call for the assemble task type.

### Finding 4

- **File**: `references/scripts/assemble_verifier.py`
- **Line**: 66–85 (`verify_preservation`)
- **Severity**: warning
- **Issue**: SC3 hard preservation guarantees include *"All file paths preserved verbatim"* and *"All fenced code blocks and bash/python invocations preserved verbatim (count + content)"*. The verifier checks sub-skill refs (multiset), step IDs (multiset), fenced code block count (±10% parity), and inline backtick count (±10% parity). But there is **no file-path preservation check** and **no fenced-code-block content-preservation check**.
- **Evidence**: SC3 lists four preservation items: sub-skill refs, step IDs, fenced code blocks + bash/python invocations (count + content), file paths. The verifier only covers #1 (sub-skill), #2 (step IDs), and #3 count-only (not content). Item #3 content ("preserved verbatim") and item #4 (file paths) are not checked. The `check_code_block_parity` function counts fence pairs and inline backticks but never extracts or compares the actual code block bodies.
- **Suggested fix**: Add `verify_fenced_block_content(linked, assembled)` that extracts all fenced blocks from both texts and asserts multiset equality of their (lang_tag, body) tuples. Add `verify_file_paths(linked, assembled)` that uses a regex for file paths (e.g. paths matching `[\w/.-]+\.[a-z]{1,6}` in prose) and checks multiset equality.

### Finding 5

- **File**: `references/scripts/atomic_emit.py`
- **Line**: 116–117, 134–135, 224
- **Severity**: warning
- **Issue**: The cache injection seams (`cache_lookup_fn`, `cache_store_fn`) have signatures incompatible with the real `assemble_cache` module, and `assemble_cache` is never imported. This means B6's cache layer cannot be connected to B7's pipeline without a missing adapter.
- **Evidence**: The seams expect `cache_lookup_fn(slot, linked_slot_body) -> str | None` and `cache_store_fn(slot, linked_slot_body, assembled_llm_output)`. The real API is `cache_lookup(alias, key, *, slot_name=None)` and `cache_store(alias, key, assembled_body)`, where `key = cache_key(linked_body, slot_name, slot_purpose, model_id, prompt_version)`. No code in `atomic_emit.py` computes `cache_key()` or passes `slot_purpose`, `model_id`, or `prompt_version` into the cache layer. The `assemble_cache` module is never imported by `atomic_emit.py` (nor any non-test file except its own tests).
- **Suggested fix**: Create an adapter function (or integrate directly) that: (a) computes `cache_key(linked_body, slot_name, slot_purpose, model_id, prompt_version)` inside the `assemble_and_emit` call, (b) wraps `assemble_cache.cache_lookup(alias, key, slot_name=slot)` and `assemble_cache.cache_store(alias, key, llm_output)` into the seam signatures, and (c) passes `alias`, `model_id`, and `prompt_version` (hash of `assemble.md.j2`) as new parameters to `assemble_and_emit`.

### Finding 6

- **File**: `references/scripts/atomic_emit.py`
- **Line**: 389–394 (`_atomic_write_triple`)
- **Severity**: warning
- **Issue**: The `targets` dict in `_atomic_write_triple` uses hardcoded filenames `CLAUDE.md`, `CLAUDE.linked.md`, `CLAUDE.conflicts.md` with no v2 prefix and no parameterization. This makes it impossible for callers to write to different filenames (e.g., the required v2 names) without modifying this function.
- **Evidence**: The filenames are string literals at lines 389–391 with no function parameter to override them. The `assemble_and_emit` function signature at line 103 takes `output_dir` but no filename prefix/suffix parameter. Even if the v2 path issue (Finding 2) were fixed by changing the literals, the function should accept configurable target names for testability and future flexibility.
- **Suggested fix**: Add a `filename_suffix` parameter to `assemble_and_emit` (default `".v2.md"` per §9a, or empty for the eventual switch PR). Construct target filenames as `f"CLAUDE{filename_suffix}"`, `f"CLAUDE.linked{filename_suffix}"`, `f"CLAUDE.conflicts{filename_suffix}"`.

### Finding 7

- **File**: `references/scripts/assemble_pass.py`
- **Line**: 78–83
- **Severity**: warning
- **Issue**: The `context` string passed to `model_router.route` contains only sub-skill and step-ID preservation directives but omits explicit mention of file-path preservation and fenced-code-block content preservation. While the full template (`assemble.md.j2`) covers these, the `context` variable is injected as `{{ context }}` in the template, meaning the LLM receives a redundant but potentially weaker signal. More critically, the context string says *"while preserving every sub-skill and step:cycle/<id> reference verbatim"* but does NOT mention code blocks or file paths at all, which could weaken the LLM's attention to those preservation requirements.
- **Evidence**: Lines 78–83 read: `"Rewrite the LINKED body for the \`{slot_name}\` slot into a single coherent voice while preserving every sub-skill and step:cycle/<id> reference verbatim. Higher-layer prose wins on contradiction..."`. File paths and code-block preservation are not mentioned. The template's {{ context }} placeholder carries this text, so the LLM sees this abbreviated instruction alongside the fuller template rules.
- **Suggested fix**: Extend the context string to include *"preserve all fenced code blocks verbatim (content + count), all file paths, and every sub-skill and step:cycle/<id> reference"* to match the full set of SC3 guarantees.