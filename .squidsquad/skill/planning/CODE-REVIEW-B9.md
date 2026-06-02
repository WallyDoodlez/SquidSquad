Now I have all the information needed for a thorough review. Let me compile my findings.

---

### Finding 1

- **File**: `references/scripts/compose.py`
- **Line**: 2210
- **Severity**: warning
- **Issue**: The `deploy` v2 success message prints the stale constant `_V2_LINKED_FILENAME` (`"CLAUDE.linked.v2.md"`) as a static label, but `deploy_alias_v2` now returns `CLAUDE.v2.md` (the assembled artifact), not `CLAUDE.linked.v2.md`. The label and the actual path (shown via `output.relative_to(REPO_ROOT)`) are inconsistent.

- **Evidence**:  
  - `deploy_alias_v2` (line 1751-1753) returns `triple_paths[0]`, which for the default `filename_suffix=".v2.md"` is the path to `CLAUDE.v2.md`.  
  - The print at line 2210 uses `_V2_LINKED_FILENAME` = `"CLAUDE.linked.v2.md"` (defined at line 1547) as the human-readable label.  
  - Before B9, `deploy_alias_v2` returned the linked composite path, so the label matched the returned file. Now they diverge — the operator sees e.g.:  
    `Deployed pm (v2) CLAUDE.linked.v2.md (NNN lines) -> .squidsquad\pm\CLAUDE.v2.md`  
  - The line count is also from `CLAUDE.v2.md` (the assembled artifact), not the linked composite, making the label doubly misleading.  
  - The `deploy-all --v2` path (line 2271) does NOT have this problem — it uses `output.relative_to(REPO_ROOT)` directly with no static label.

- **Suggested fix**: Replace `_V2_LINKED_FILENAME` with `output.name` (the actual basename of the returned path), or drop the static label entirely since the `->` path already shows the filename unambiguously. For example:  
  ```python
  print(f"Deployed {role_name} (v2) {output.name} ({lines} lines) -> {output.relative_to(REPO_ROOT)}")
  ```

---

### NO further findings

I reviewed all five focus areas in detail:

**(a) Cache key composition + adapter contract**: The adapter `_key_for` (`assemble_adapter.py` lines 49-57) calls `cache_key(linked_slot_body, slot, slot_purpose, model_id, prompt_version)` — matching the B6 signature `cache_key(linked_body, slot_name, slot_purpose, model_id, prompt_version)` (`assemble_cache.py` line 35) in exact positional order. All five fields are hashed with the `0x1F` separator. The `DEFAULT_SLOT_PURPOSES` map is correctly wired into the adapter's `slot_purposes.get(slot, "")` lookup, and the B7→B6 seam signatures (`cache_lookup_fn(slot, linked_slot_body)` → `cache_lookup(alias, key, slot_name=slot)`, `cache_store_fn(slot, linked_slot_body, assembled_body)` → `cache_store(alias, key, assembled_body)`) match correctly. Tests in `test_assemble_wired_b9.py` prove per-slot key independence, model_id invalidation, and prompt_version invalidation.

**(b) Return-value semantic change**: `deploy_alias_v2` now returns `CLAUDE.v2.md` (the assembled runtime artifact) per AC — verified at line 1751-1753. The only callers are in `main()` (`deploy` and `deploy-all`), and they only use the return value to read line counts and display paths. Aside from the misleading label in Finding 1, no caller is broken.

**(c) §9a coexistence**: `filename_suffix` defaults to `".v2.md"` (`atomic_emit.py` line 196), producing `CLAUDE.v2.md` / `CLAUDE.linked.v2.md` / `CLAUDE.conflicts.v2.md`. The empty-string branch (lines 208-211) is explicit (`if filename_suffix == ""`) and maps to v1 canonical names. Tests prove `filename_suffix=""` writes only v1 names, `filename_suffix=".v2.md"` writes only v2 names, and the two never cross-contaminate.

**(d) Failure isolation**: All assemble verification failures (`PreservationFail`, `FloorParityFail`, `PrecedenceViolation`, `CacheCorruption`) raise before `_atomic_write_triple` is called, so zero disk artifacts are produced. `_atomic_write_triple` itself writes `.tmp` files first, cleaning them all up on any write failure before renaming. The `deploy_alias_v2` catch-all at line 1744-1748 prints the diagnostic and exits 1 — the output directory is untouched on failure.

**(e) Error semantics**: All `AssembleError` subclasses (`LinkStageFail`, `LLMError`, `PreservationFail`, `FloorParityFail`, `CacheCorruption`, `ConflictReportWriteFail`, `PrecedenceViolation`) carry descriptive messages and all warrant exit 1 with no differentiated recovery. The broad `except Exception` in `deploy_alias_v2` also correctly lets `SystemExit` and `KeyboardInterrupt` propagate. No special-casing is needed.