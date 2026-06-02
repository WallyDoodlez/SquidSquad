After a thorough review of `_load_manifest_v2`, `_load_manifest_v2_from_file`, the v2 manifest files, and the test module, here are my findings:

---

### Finding 1

- **File**: `references/scripts/compose.py`
- **Line**: ~785–800 (the `else` block in `_load_manifest_v2`)
- **Severity**: warning
- **Issue**: The legacy fallback block (dev‑alias + `_BASE_ALIAS_6274` lookup) is **nested inside the `else` branch** of `_load_manifest_v2`, not at the top level after the `if resolved: / else:` structure. In v1's `_load_manifest`, that same fallback block sits *after* the `if/else` so it fires for both variant and non‑variant paths. In v2 it fires **only** for the non‑variant path.

- **Evidence**:  
  - v1 code (lines ~618–633 in the file): the `if manifest_path is None:` block with the legacy `"dev" in identities` and `_BASE_ALIAS_6274` checks is at the **same indentation level** as the preceding `if/else`, so it is reachable from both branches.  
  - v2 code: those same checks are indented inside `else:`, meaning they can never execute when `_resolve_variant(role_name)` returns a tuple (variant role).  
  - The comment inside the v2 `else` block even says *"same alias fallback v1 applies"*, which is misleading — v1 applies it in both paths.

- **Suggested fix**: Move the legacy‑fallback block out of the `else` so it sits at the same level as `if manifest_path is None: return None`, matching v1's structure. For the variant path, the existing `manifest_path = _resolve_v2_path(ROLES_DIR / base)` fallback is probably sufficient, but the alias fallback should still be available for defence‑in‑depth parity with v1.

---

### Finding 2

- **File**: `tests/test_manifest_v2_d5.py`
- **Line**: 87–103 (class `TestV2IsUnion`)
- **Severity**: warning
- **Issue**: The AC states that *"events is a strict subset of polling in all 4 roles so v2 == polling"*. The test `test_v2_contains_union_of_v1` only asserts that v2 is a **superset** of the v1 union (`union - v2 == set()`). There is **no assertion** that v2 is a subset of polling (i.e. that v2 contains no extra entries beyond what polling declares). An accidental extra entry in `includes‑v2.yml` would pass all existing tests undiscovered — `test_v2_does_not_introduce_unknown_entries` only checks file existence, not manifest membership.

- **Evidence**:  
  - Task context line 1–2: *"events is strict subset of polling in all 4 roles so v2 == polling"*.  
  - The set‑difference check on line 93–95 is one‑sided: `missing = union - v2`. The complementary check `extra = v2 - v1_polling` is never computed.

- **Suggested fix**: Add a second assertion: `extra = v2 - v1_polling; assert extra == set()`. This verifies the invariant *v2 == polling* directly.

---

### Finding 3

- **File**: `tests/test_manifest_v2_d5.py`
- **Line**: 107–118 (`test_variant_inherits_base_v2_manifest`)
- **Severity**: warning
- **Issue**: The test reads `ROLES_DIR / "worker" / "skill" / "includes.yml"` with a bare `Path.read_text()` call. If that variant directory or file does not exist (e.g. a future rename of `skill`), the test raises `FileNotFoundError` rather than a clean `AssertionError` or `pytest.skip`. This makes the test fragile to repo‑layout changes and harder to diagnose.

- **Evidence**:  
  - Line 111: `(ROLES_DIR / "worker" / "skill" / "includes.yml").read_text(encoding="utf-8")` — no `exists()` guard.  
  - The other tests in the file use the `_load_yaml_list` helper which has the same issue, but those target base‑role manifests that are expected to always exist. Variant directories are more likely to be renamed/deleted.

- **Suggested fix**: Guard with `if not variant_yml.is_file(): pytest.skip(...)` or use a try/except that produces a clear skip message.

---

### Finding 4

- **File**: `references/scripts/compose.py`
- **Line**: 776–780 (in `_load_manifest_v2`)
- **Severity**: error
- **Issue**: When `_resolve_variant(role_name)` returns a tuple but the variant directory has **no `includes.yml`**, the code sets `manifest_path = _resolve_v2_path(ROLES_DIR / base)` and falls through to the bottom. If that also returns `None`, the function returns `None` **without ever entering the legacy fallback block** (because it is nested inside `else` — see Finding 1). In v1 the same scenario would try `_resolve_manifest_path(ROLES_DIR / "dev")` and the `_BASE_ALIAS_6274` alias fallback. This means a legacy variant whose base role directory exists but has no `includes‑v2.yml` (e.g. a pre‑rename `dev/skill/` variant where `dev/` was not yet given an `includes‑v2.yml`) would silently fail in v2 while v1 would succeed via the dev fallback.

- **Evidence**:  
  - Lines 771–779: the `if resolved:` branch either returns early (`if variant_manifest.exists()`) or sets `manifest_path`. The `else` branch contains the legacy‑fallback code.  
  - Lines 799–802: after the `if/else`, the only remaining check is `if manifest_path is None: return None`.  
  - Comparing v1 lines ~603–633: the legacy fallback block runs for **both** branches because it is at the top level after `if/else`.

- **Suggested fix**: Same as Finding 1 — move the legacy‑fallback block out of `else`. This is the same root cause but called out separately because the concrete failure mode (variant + missing v2 base manifest → silent `None`) is a correctness concern, not just a style issue.

---

### Finding 5

- **File**: `tests/test_manifest_v2_d5.py`
- **Line**: 61–81 (class `TestV1Untouched`)
- **Severity**: warning
- **Issue**: The tests `test_polling_manifest_unchanged` and `test_event_driven_manifest_unchanged` call `compose._load_manifest(role, "polling")` and `compose._load_manifest(role, "event-driven")` respectively, and compare the result against the raw YAML on disk. This is a **good regression test**, but it only exercises the loader — it does **not** verify that `compose_role` (the full v1 compose pipeline) still produces byte‑identical output. The class `TestV1ByteEquivalence` below it only checks **idempotence** (`compose_role` twice produces the same string), not equivalence to a pre‑D5 baseline.

- **Evidence**:  
  - Lines 85–93: `a = compose.compose_role(role); b = compose.compose_role(role); assert a == b` — this proves determinism, not that D5 didn't perturb v1 output.  
  - The test docstring itself acknowledges this: *"the real protection is the §9a CI gate that snapshots the deploy output, which runs separately"*. Relying solely on an external CI gate for a critical AC (AC3: v1 unchanged) is fragile.

- **Suggested fix**: Either: (a) capture a golden‑file snapshot of `compose_role(role)` for each base role and assert byte‑equality, or (b) add a comment explicitly stating that the §9a CI gate is the sole enforcer and this test is only a smoke check. Option (a) is stronger and matches the test class name.