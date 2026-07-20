I have conducted a thorough review of all changed files. After tracing through data flows, edge cases, and test assertions, I found the code to be quite robust. Below are the genuine defects identified.

---

### Finding 1

- **File**: `references/scripts/vault_check.py`
- **Line**: 38
- **Severity**: warning
- **Issue**: `PARAG_DIRS` module-level constant is dead code — it is documented as the fallback taxonomy but never referenced by any function. The `_load_schema` function uses its own inline hardcoded dict (lines 65-74) for the third-level fallback instead.
- **Evidence**: A grep for `PARAG_DIRS` across the file shows it is defined on line 38 but never appears in any function body, condition, or return statement. The `_load_schema` function (lines 53-75) builds its fallback via an inline dict literal at lines 65-74, completely independent of `PARAG_DIRS`. A maintainer reading the module docstring and the `PARAG_DIRS` comment at line 35 would expect the hardcoded fallback to use this constant, but it does not.
- **Suggested fix**: Either delete `PARAG_DIRS` (if the inline dict in `_load_schema` is canonical) or update `_load_schema`'s hardcoded fallback to derive its folder list from `PARAG_DIRS` so the two don't drift apart. The inline dict already carries the authoritative shape; `PARAG_DIRS` is redundant.

---

### Finding 2

- **File**: `references/scripts/vault_check.py`
- **Line**: 65-74 (hardcoded fallback dict in `_load_schema`)
- **Severity**: warning
- **Issue**: The hardcoded third-level fallback in `_load_schema` omits the `system` type that exists in `vault-schema-default.json` (the second-level seed fallback). This means `check-structure`'s requirements silently change depending on whether the seed file is accessible: with the seed, `systems/` is a required directory; without it (extreme degradation), `systems/` is not required.
- **Evidence**: `vault-schema-default.json` line 12 declares `"system": { "folder": "systems", "traversal": "free", "weight": 0.8, "hub": true }`. The hardcoded fallback at lines 65-74 lists 7 types (project through archive) with no `system` entry. The seed file path at line 62 (`REPO_ROOT / "references" / "vault-schema-default.json"`) is a committed file that should always exist, so this inconsistency is latent — but a build/packaging error that loses the references directory would silently change validation behavior.
- **Suggested fix**: Add `"system": {"folder": "systems", "traversal": "free", "hub": True}` to the hardcoded fallback dict so all three tiers of the degradation chain agree. Alternatively, document that the hardcoded fallback intentionally represents the pre-#13858 v1 shape and that `system` is a P2 addition only available when the seed file is reachable.

---

### Finding 3

- **File**: `references/scripts/vault_entity.py`
- **Lines**: 58-63
- **Severity**: error
- **Issue**: `create_note` does not validate that `slug` is a non-empty string. An empty slug with a type that has no prefix produces a file named `.md` (a dotfile), and with a prefixed type produces e.g. `decision-.md`. More critically, `slug` values containing path separators or `..` components are not sanitized, allowing the created file to land outside the type's registered folder within the vault tree.
- **Evidence**: Lines 58-63:
  ```python
  prefix = reg.get("prefix") or ""
  name = slug if not prefix or slug.startswith(prefix) else prefix + slug
  dest_dir = vd / reg["folder"]
  dest = dest_dir / f"{name}.md"
  ```
  If `slug = ""` and the type has no prefix, `name = ""` and `dest` resolves to `<folder>/.md`. If `slug = "../../../escape"`, `dest` resolves outside the intended folder (e.g., `<vault>/escape.md` instead of `<vault>/<folder>/decision-../../../escape.md` which Path normalizes). This is an internal tool invoked by the wizard/installer, so the blast radius is limited, but the function provides no input validation.
- **Suggested fix**: Add a slug validation guard at the top of `create_note`:
  ```python
  if not slug or not re.match(r'^[A-Za-z0-9][A-Za-z0-9._-]*$', slug):
      raise ValueError(f"invalid slug: {slug!r}")
  ```
  This rejects empty strings and path-traversal sequences before they reach `Path` construction.

---

### Finding 4

- **File**: `tests/test_vault_check_13858.py`
- **Lines**: 163-167
- **Severity**: warning
- **Issue**: `test_absent_schema_falls_back_to_seed_profile` uses a disjunctive assertion (`"system" in views["hub_types"] or "project" in views["hub_types"]`) that would pass even if the `system` type is missing from the seed-derived schema. The test name and docstring claim to verify that `system` is present in the seed profile, but the assertion does not enforce this — it only verifies that *some* hub type exists.
- **Evidence**: Lines 163-167:
  ```python
  def test_absent_schema_falls_back_to_seed_profile(self, scratch_vault):
      views = vault_check._schema_views(vault_check._load_schema())
      assert "galaxy" in views["folders"]
      assert "system" in views["hub_types"] or "project" in views["hub_types"]
  ```
  The docstring says "systems/ present, galaxy budgeted, hub types declared." However, the assertion `"system" in views["hub_types"] or "project" in views["hub_types"]` is satisfied by `"project" in views["hub_types"]` alone — it never fails if `system` is absent. This makes the test weaker than advertised. The `or` clause appears designed to accommodate the third-level hardcoded fallback path (which has `project` but not `system`), but the test name implies it's testing the seed-path behavior specifically.
- **Suggested fix**: Split into two tests or tighten the assertion. If the intent is to test the seed fallback specifically, assert `"system" in views["hub_types"]` unconditionally (the seed file is committed and always present in test runs). If the intent is to test the degradation chain, rename the test and add a separate test that directly validates the seed contains `system`.

---

### Finding 5

- **File**: `references/skills/vault-search/scripts/lib/consumption.mjs`
- **Line**: 291-295 (approximate — `tieBreakScore` function's `typeWeight` call)
- **Severity**: warning
- **Issue**: `tieBreakScore` passes `fields.folder` as the second argument to `typeWeight`, but when a note resides in a multi-type folder (e.g., `galaxy/` hosts `decision`, `pattern`, and `learning` types), the `folderDefaultWeight` for that folder is the *first-registered* type's weight (1.0 from `decision`). A note with a missing or unregistered `type:` in `galaxy/` therefore gets weight 1.0 — which is correct per the spec — but the `deriveSchema` comment says "first-registered type's weight" and the resolution order is documented. This is not a logic bug, but it means that if someone reorders the types in their custom schema, the folder default weight for a multi-type folder silently changes.
- **Evidence**: In `deriveSchema` (consumption.mjs lines 88-100):
  ```javascript
  if (!(t.folder in folderDefaultWeight) && Number.isFinite(t.weight)) {
      folderDefaultWeight[t.folder] = t.weight;
  }
  ```
  For `DEFAULT_CONFIG`, `galaxy` first appears under `decision` (weight 1.0). For a custom schema where `learning` (weight 0.5) is listed before `decision`, the galaxy default weight would be 0.5. This ordering dependency is implicit and undocumented in the schema file format.
- **Suggested fix**: Either document that type registration order determines folder-default weight (the current behavior), or make the folder default weight an explicit field in the schema (e.g., `"folderDefaultWeight"` at the top level). The latter would be more robust but is a design change, not a bugfix.

---

**Summary**: The implementation is solid. The issues found are: one dead-code constant, one fallback inconsistency between schema tiers, one missing input validation in `create_note`, one test with a weaker assertion than its name implies, and one implicit ordering dependency in folder-default weights. None of these block the P2 delivery.