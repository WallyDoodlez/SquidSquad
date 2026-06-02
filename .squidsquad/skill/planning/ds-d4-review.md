After thorough review of the three changed files, I've identified several issues. Let me present them in priority order.

---

### Finding 1

- **File**: `references/scripts/catalog_drift.py`
- **Line**: `_collect_manifest_references` function, the `for role_dir in roles_dir.iterdir():` loop (approximately line 208-210)
- **Severity**: warning
- **Issue**: The dead-code scan only iterates top-level directories under `references/roles/` using `iterdir()`. Nested variant directories (e.g., `roles/worker/skill/`) are never visited, so any sub-skill referenced **only** by a variant's `additional_includes` (or a variant's own `includes`) will be falsely reported as a dead-code candidate. Additionally, even if nested directories were visited, the function only reads the `includes` key — it does not recognise the `base_role` + `additional_includes` variant schema that `compose.py._load_manifest` handles.
- **Evidence**: `iterdir()` yields only immediate children; `roles/worker/skill/` is two levels deep and will not be yielded. Compose.py explicitly resolves variants via `_resolve_variant` → `ROLES_DIR / base / variant`, and those variant directories carry their own `includes.yml` files with the variant schema. The test helper `_make_fixture` only creates top-level manifests — no test covers nested variants.
- **Suggested fix**: Either (a) walk the roles tree recursively (e.g., `roles_dir.rglob("*.yml")` filtered by `_MANIFEST_FILENAMES`) and extract referenced names from **both** `includes` and `additional_includes` keys, or (b) call `_load_manifest` / `_resolve_variant` for every known role identity to gather the resolved include list. Option (b) would guarantee the same reference set compose.py uses, but imports a heavier dependency. Option (a) is simpler: `rglob` + read both keys.

---

### Finding 2

- **File**: `references/scripts/catalog_drift.py`
- **Line**: `except _yaml.YAMLError: continue` in `_collect_manifest_references` (approximately line 228)
- **Severity**: warning
- **Issue**: YAML parse errors in individual manifest files are silently swallowed with no diagnostic. If a manifest file is corrupted, all of its includes are silently omitted from the reference set, which can cause false-positive dead-code warnings. The user has no indication that a manifest was skipped or why.
- **Evidence**: The docstring says "YAML import failure is fatal" but parse errors are not. Compose.py's equivalent (`_load_manifest`) prints a `WARNING` to stderr on parse failure before returning `None`. The drift check should be at least as transparent.
- **Suggested fix**: Print a warning to stderr before the `continue`, e.g.:
  ```python
  except _yaml.YAMLError:
      print(f"WARNING: drift-check skipping unparseable manifest: {mpath}", file=sys.stderr)
      continue
  ```

---

### Finding 3

- **File**: `tests/test_catalog_drift_d4.py`
- **Line**: Function signature of `_make_fixture` — the `dead_code_extra` parameter (approximately line 23)
- **Severity**: warning (minor)
- **Issue**: The `dead_code_extra` parameter is accepted in the function signature but is never referenced anywhere in the function body. This is dead code in the test helper.
- **Evidence**: A search of the function body confirms `dead_code_extra` is never read or used. No caller passes it either (all call-sites omit it, relying on the default `()`).
- **Suggested fix**: Remove the parameter, or implement its intended purpose (if it was meant to add extra catalog rows that should be flagged as dead-code for testing).

---

### Finding 4

- **File**: `references/scripts/catalog_drift.py`
- **Line**: `if md_path.name in _NON_SUB_SKILL_BASENAMES: continue` inside `scan_drift` (approximately line 156)
- **Severity**: warning (minor)
- **Issue**: The check uses `md_path.name` (basename only) to exclude files, which means files named `manifest.md`, `README.md`, or `index.md` are excluded **anywhere** in the sub-skills tree, not only at the root. The docstring says "`manifest.md` at the top of `references/sub-skills/`" — the code excludes it in nested directories too, which could theoretically hide a real orphan source file.
- **Evidence**: `md_path.name` returns just the filename; `md_path.parent` is not compared to `sub_skills_root`. A file at `references/sub-skills/common/manifest.md` would be silently excluded.
- **Suggested fix**: Either restrict the exclusion to files directly in `sub_skills_root` (compare `md_path.parent == sub_skills_root`), or update the docstring to explicitly state the broader exclusion applies everywhere. The practical risk is negligible (nobody puts a real sub-skill in a file named `manifest.md`), so a doc fix may be sufficient.

---

### Finding 5

- **File**: `references/scripts/catalog_drift.py`
- **Line**: `_collect_manifest_references` basename logic (approximately line 235-237)
- **Severity**: warning (minor)
- **Issue**: The basename-based matching can produce **false negatives** in dead-code detection. If catalog entry `X` is genuinely unreferenced, but some **unrelated** manifest include like `some/other/X` happens to have the same basename, the catalog entry `X` will match the basename and won't be flagged. The inverse is also possible: a slash-bearing catalog entry like `deep/path/X` won't match a manifest include of just `X` (no slash → no basename extraction), yielding a **false positive**.
- **Evidence**: For manifest include `some/other/X`, the code adds both `some/other/X` and `X`. Catalog entry `X` then matches. But `some/other/X` may be a completely different file unrelated to catalog entry `X`. Similarly, manifest include `X` (no slash) adds only `X`; catalog entry `deep/path/X` is the string `deep/path/X` and does not match `X`.
- **Suggested fix**: A more precise approach: for each catalog name, check whether the **exact** name is in referenced, **or** (if the catalog name contains a slash) whether its basename is in referenced. This avoids the asymmetric false-positive case. The false-negative case (basename collision) is inherent to basename heuristics; consider logging when a basename match is the only reason a catalog entry escapes dead-code, so operators can audit.

---

**Overall assessment**: The core two-way orphan scan (directions 1 and 2) is correct and well-tested. The dead-code scan (direction 3) has genuine gaps — it doesn't walk nested variant directories and doesn't handle the `base_role` + `additional_includes` manifest schema, which can cause false-positive dead-code warnings. The other findings are lower severity (missing warnings, minor test dead code, and heuristic imprecision).