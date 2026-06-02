I've completed a thorough review of both changed files and the test suite. Here's my analysis:

**Files examined:**
- `references/scripts/v2_catalog_gate.py` (full module)
- `references/scripts/compose.py` (lines 1673–1696, plus surrounding `deploy_alias_v2` and `main()` dispatch)
- `tests/test_v2_catalog_gate_d3.py` (all tests)
- `references/scripts/catalog_parser.py` (`parse_catalog` return type — returns `{name: source_path}` dict)

**What I checked:**

1. **Regex correctness** (`_REF_RE`): The name character class `[a-z][a-z0-9/_-]*` is byte-for-byte identical to catalog_parser's `_NAME_CELL_RE`. Slash-bearing names, hyphens, underscores all match consistently. The `→` Unicode arrow matches what v2 link stage emits.

2. **Resolution logic** (`validate_v2_compose`): `catalog.get(name)` returns `None` for missing entries → unresolved. Non-`None` paths are checked via `(repo_root / source_path).is_file()` → missing-file if gone. Both branches deduplicate correctly (`seen_unresolved` set of names; `seen_missing` set of `(name, source_path)` tuples).

3. **Atomic-write contract**: Gate runs at lines 1678–1696, AFTER `emit_v2_linked` succeeds (line 1663) but BEFORE `output_path.write_text()` (line 1703). On failure, `sys.exit(1)` is called with zero artifacts on disk.

4. **AC5 — v1 untouched**: Only `deploy_alias_v2` imports `v2_catalog_gate` (confirmed via grep). Neither `deploy_role`, `compose_role`, nor `_resolve_includes` reference it. The v1 dispatch in `main()` does not trigger it.

5. **AC4 — all issues reported**: The `validate_v2_compose` loop processes all references. `GateResult.format()` renders both `unresolved` and `missing-file` sections in one report. Tests confirm multi-issue reporting.

6. **Test coverage**: Tests cover regex shape (plain name, multiple, slash-bearing, unrelated arrows, duplicate extraction), clean compose, single unresolved, multiple unresolved, dedup collapse, missing-file, mixed issues, `CatalogGateError` shape, and the static AC5 assertion that only `deploy_alias_v2` references the gate module.

7. **`deploy-all --v2` integration**: The `SystemExit` raised by `sys.exit(1)` in the gate is caught by the loop at line ~1750, so deploy-all correctly collects failures across all aliases without short-circuiting.

8. **Edge cases**: Empty text → no references → clean. Catalog parse errors bubble through `except Exception` and abort with a diagnostic. Missing catalog file raises `CatalogParseError` which is caught. `full.is_file()` correctly returns `False` for directories and symlinks to directories.

No correctness defects, regressions, or philosophy violations found.

NO_FINDINGS