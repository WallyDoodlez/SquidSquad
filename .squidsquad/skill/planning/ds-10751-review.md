Now I have all the information I need. Let me trace through the key logic one final time to confirm my finding.

---

After thorough review of all five changed files, I found one genuine issue:

### Finding 1

- **File**: `references/scripts/config.py`
- **Line**: 379–383
- **Severity**: warning
- **Issue**: The `else` branch in `_parse_aliases_bullet_form` uses `continue` to skip unrecognized bullet values, **silently dropping them** when mixed with recognized bullets. Both the docstring (lines 352–354) and the inline comment (lines 379–382) claim the function returns `{}` / "falls through to the needs table format diagnostic" so the operator can fix the offending bullet — but that only happens when *all* bullets are unrecognized. A single recognized bullet makes `registry` truthy, and any unrecognized siblings are silently discarded with no diagnostic whatsoever.
- **Evidence**:
  - **Docstring** (lines 352–354): *"Any other `<value>` -> bullet form does not recognize it; `_parse_aliases_bullet_form` returns `{}` so the caller raises its normal 'needs table format' diagnostic."*
  - **Inline comment** (lines 379–382): *"Unrecognized value -> caller falls through to the 'needs table format' diagnostic so the operator can fix the offending bullet **rather than silently dropping it**."* (emphasis mine)
  - **Actual code** (line 383): `continue` — which advances to the next iteration. If any prior bullet was recognized, `registry` is non-empty, the function returns it, and the unrecognized entry vanishes without a trace.

  Concrete example — this input:
  ```
  - **pm**: pm
  - **skill**: skil
  ```
  …produces `{"pm": ("pm", None)}`. The `skill` alias is silently absent from the registry. No error, no warning. The operator has no signal that `skil` (a typo for `skill`) was ignored.

  The existing test `test_unrecognized_value_falls_through_to_table_diagnostic` only covers the case where the **only** bullet is unrecognized — it doesn't exercise the mixed recognized+unrecognized path.

- **Suggested fix**: Either (a) make the code match the documented intent — raise `AliasesRegistryError` on any unrecognized bullet value (not just when all are unrecognized), or (b) update the docstring and comment to accurately describe the permissive "skip unrecognized, keep recognized" behavior. Option (a) is safer because it prevents silent data loss from typos; it also matches what the docstring and comment already claim.

---

NO_FINDINGS for the remaining scope:
- The **#6274 shim** (`_BULLET_LEGACY_ROLE_CLASS_SHIM`) is correctly mirrored from `compose._BASE_ALIAS_6274` (mapping `qa→verifier`, `dev→worker`) and correctly applied in both the bullet-form fallback (line 374) and the table-form path (line 502).
- The **bullet-form fallback** in `parse_aliases_registry` (lines 444–459) correctly delegates to `_parse_aliases_bullet_form` when no table rows are detected, preventing v2 deploys from aborting on live config.md.
- The **W1 column-header fix** — `_ALIASES_HEADER_COLUMNS = ("alias", "role-class", "L3 domain")` uses the canonical lowercase-hyphen form; the comparison at line 462–463 uses `.lower()` on both sides; the test fixture at line 80 of `test_compose_a2f_10492.py` now writes the matching header.
- The **W4 R3 guard** at line 126 of `link_stage_validator.py` explicitly checks `src.layer in ("L1", "L2", "L3")`, symmetric with R2's `src.layer in ("L2", "L3")`, and the test `test_r3_l4_source_with_project_context_slot_does_not_trigger` confirms L4 sources pass through.
- The **catalog fixture** (`_stage_minimal_catalog` in `test_compose_a6_v2.py` and inline in `_stage_minimal_install` in `test_compose_a2f_10492.py`) is correctly wired into the 4 previously-broken A6 tests plus the new A2f tests.
- All other test coverage is correct and comprehensive for the stated acceptance criteria.