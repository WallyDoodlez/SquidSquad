I've traced all the code paths. Here is my finding:

### Finding 1

- **File**: references/scripts/config.py
- **Line**: 1012–1015 (`dump_all`) and 183–190 (`_parse_all`)
- **Severity**: warning
- **Issue**: `dump_all()` / `_parse_all()` bypasses the ship-counter storage redirect, returning the config.md value for `shipped-since-bump` instead of the authoritative `.ship-counter` value. After migration (once `.ship-counter` exists and diverges from the stale config.md field), `config.py dump` will report a wrong counter value — or omit `shipped-since-bump` entirely if config.md's legacy field has been cleaned up by a 3-way merge.
- **Evidence**: 
  - `get_field("shipped-since-bump")` (line 241–246) correctly redirects to `_read_ship_counter()` → `.ship-counter` file with migration fallback.
  - `_parse_all(text)` (line 183–190) iterates `FIELD_MAP` and calls `_parse_field(text, section, field_name)` directly on the raw config.md text — it never consults `_read_ship_counter()` or `_FIELD_DEFAULTS`.
  - `dump_all()` (line 1012–1015) delegates to `_parse_all(_read_config())` — only config.md, never `.ship-counter`.
  - A caller that runs `config.py get shipped-since-bump` gets the authoritative `.ship-counter` value; `config.py dump` returns whatever stale (or absent) value remains in config.md. These two answers can silently diverge.
  - The test file `test_12823_ship_counter_split.py` does not cover `dump_all` / `_parse_all` at all.
- **Suggested fix**: In `_parse_all`, after building the result from config.md text, overlay the ship-counter value from `_read_ship_counter()` (with the `_FIELD_DEFAULTS` fallback) so the dump output is consistent with `get_field`:

```python
def _parse_all(text):
    result = {}
    for short_name, (section, field_name) in FIELD_MAP.items():
        val = _parse_field(text, section, field_name)
        if val is not None:
            result[short_name] = val
    # #12823: ship counter is stored externally; overlay the authoritative value.
    sc = _read_ship_counter()
    if sc is not None:
        result["shipped-since-bump"] = sc
    elif "shipped-since-bump" not in result:
        result["shipped-since-bump"] = _FIELD_DEFAULTS.get("shipped-since-bump", "0")
    return result
```

**Additional verification results (no issues found)**:

- **(a) Migration correctness**: The read path checks `.ship-counter` first, falls back to `config.md`'s `Auto Versioning > Shipped Since Last Bump` field. The first `set_field` write atomically creates `.ship-counter` with the correct value. No data loss or corruption in the read-fallback → first-write sequence. The stale config.md field is left for normal 3-way merge (it's now ignored). The #9772 self-heal in `_reconcile_ship_counter` uses `get_field`/`set_field`, so it participates in the redirect correctly.
- **(b) Commit + merge=ours protection**: `.squidsquad/.ship-counter` is staged by `commit_state` (prefix match `.squidsquad/`, line ~870) and by `commit_role_scoped` (explicit allowlist entry, line 744). The `.gitattributes` test (line 92–103) verifies `.ship-counter merge=ours` is present and `config.md merge=ours` is removed.
- **(c) get_field side-effect freedom**: `get_field("shipped-since-bump")` only reads — it calls `_read_ship_counter()` which reads files, never writes. The migration write only happens in `set_field` → `_write_ship_counter`.
- **(d) No other bypass found**: All production consumers (`cycle_pre._config_get`, `cycle_post` reset, `_reconcile_ship_counter`) route through `config.py get/set`. The grep for `Shipped Since Last Bump` across all `.py` files confirms no other code parses the field directly from config.md.
- **(e) Fresh install**: Neither file exists → `_read_ship_counter()` returns `None` → `get_field` returns `_FIELD_DEFAULTS["shipped-since-bump"]` = `"0"`. Correct.