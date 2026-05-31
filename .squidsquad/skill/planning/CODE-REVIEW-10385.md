After thorough review of all three changed files against the acceptance criteria and the COMPOSE-ARCHITECTURE §3.0 spec, I find the implementation to be correct, complete, and well-tested. Here's my detailed analysis:

---

### What was checked

1. **AC: Returns `{alias: (role_class, l3_domain)}` with em-dash → None**
   - `parse_aliases_registry()` at line ~310-311 correctly builds `registry[alias] = (role_class, l3_domain)`
   - Line ~308: `l3_domain = None if l3_cell == ALIASES_L3_NONE_SENTINEL else (l3_cell or None)` — em-dash U+2014 maps to `None`; any other value passes through verbatim
   - Test `test_em_dash_l3_becomes_none` and `test_non_dash_l3_preserved_verbatim` confirm both paths

2. **AC: Validates 3-column shape**
   - Header validation at line ~287-294 checks `len(header) != 3` AND column-name equality (case-insensitive)
   - Data row validation at line ~306-310 checks `len(cells) != 3` for every row

3. **AC: role-class in `{pm, worker, verifier, dm}`**
   - `ALIASES_ROLE_CLASSES = frozenset({"pm", "worker", "verifier", "dm"})` at line ~267 — immutable, correct set
   - Validation at line ~302-306 with clear error message listing valid values

4. **AC: Rejects duplicates**
   - Line ~311: `if alias in registry` check before insertion
   - Error message names the alias and data row number

5. **AC: Rejects malformed rows**
   - Empty alias: line ~298-301
   - Empty role-class: line ~301-304
   - Unknown role-class: line ~304-306
   - Wrong column count: line ~306-310

6. **AC: Rejects missing section**
   - Line ~280-283: `_ALIASES_HEADING not in sections` check
   - Also rejects empty section (present but no table) at line ~290-294

7. **AC: Pure additive, no existing callers touched**
   - New constants, new exception class, new helper functions (`_split_table_row`, `_is_table_separator`), new public function (`parse_aliases_registry`) — all additive
   - Existing `_parse_field_in_text` and `get_alias` are unchanged
   - Legacy bullet parser in `_parse_field_in_text` remains the path for `alias-skill`, `alias-pm`, etc. in `FIELD_MAP`

### Edge cases examined

| Edge case | How it's handled | Tested? |
|---|---|---|
| L3 cell is empty string `""` | `l3_cell or None` → `None`; treated identically to em-dash (reasonable — empty = no domain) | Not explicitly (acceptable — not an AC requirement) |
| L3 cell is whitespace-only `"   "` | `cell.strip()` in `_split_table_row` normalizes to `""` → `None` | Not explicitly |
| L3 cell with hyphen-minus `"-"` | Preserved as `"-"` (strict U+2014 sentinel check per code comment) | Not explicitly (by design — code comment acknowledges this) |
| Extra `\|` in section prose | `_split_table_row` treats any line with `\|` as a row candidate, then column-count validation rejects | Covered by column-count tests |
| Missing config.md on disk | `_read_config()` → `sys.exit(1)` (consistent with entire config.py pattern) | N/A (existing infrastructure behavior) |
| Separator row with `:---:` colons | Regex `^\s*:?-+:?\s*$` correctly matches standard markdown separator variants | Not explicitly (minor — valid markdown) |
| Trailing whitespace in cells | `cell.strip()` normalizes all cells | Covered implicitly by canonical table test |

### No philosophy violations found

- **Prose over scripts**: The function is a parser script with good docstrings; no prose-is-code confusion
- **Mutable global state**: `ALIASES_ROLE_CLASSES` is `frozenset`; `ALIASES_L3_NONE_SENTINEL` is `str` — both immutable
- **Over-validation**: Validation is targeted at structural correctness (column count, allowed role-classes, uniqueness, non-empty required fields). L3 domain values are intentionally NOT allow-list-validated (per docstring), correctly deferring to the caller (compose.py in A6)

---

NO_FINDINGS