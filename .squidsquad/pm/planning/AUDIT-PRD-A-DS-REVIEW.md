Now I have a thorough understanding of the codebase. Let me compile my findings.

---

### Finding 1

- **File**: `.squidsquad/config.md`
- **Line**: 14-19
- **Severity**: error
- **Issue**: The `## Aliases` section uses the legacy bullet format (`- **skill**: skill`) instead of the 3-column markdown table format (`| alias | role-class | L3 domain |`) that `parse_aliases_registry()` requires. Running any `--v2` command (`deploy <alias> --v2` or `deploy-all --v2`) on this install will fail with `AliasesRegistryError("`## Aliases` section is present but contains no table")`.
- **Evidence**: 
  - Config.md line 14-19: `## Aliases` contains only bullet entries `- **skill**: skill`, `- **pm**: pm`, etc. — no markdown table.
  - `config.py` line 337-433: `parse_aliases_registry()` expects `| alias | role-class | L3 domain |` table per COMPOSE-ARCHITECTURE §3.0; raises `AliasesRegistryError` if no table is found (line 369-374).
  - PRD §6 lists the `## Aliases` registry as "already shipped via installer" — but the live config.md has NOT been migrated to the table format.
  - `compose.py` lines 1597-1606: `deploy_alias_v2` calls `parse_aliases_registry()` and will exit with code 1 for this install.
  - `compose.py` lines 2186-2192: `deploy-all --v2` likewise calls `parse_aliases_registry()` and will fail.
- **Suggested fix**: Either (a) add a migration path or fallback in `parse_aliases_registry` to read the legacy bullet format during the §9a coexistence window, or (b) add a pre-`--v2` migration step that rewrites the `## Aliases` section into table format. The PRD §9a says "v2 code lives side-by-side with v1" — if the registry parser only reads the v2 table format, there must be a migration step to convert the v1 bullets to the v2 table before any `--v2` command can work.

---

### Finding 2

- **File**: `tests/test_compose_a2f_10492.py`
- **Line**: 60
- **Severity**: warning
- **Issue**: The `_stage_minimal_install` helper writes a config.md table header with `| Alias | Role class | L3 domain |` (using a space in `Role class`), but `config.py`'s `parse_aliases_registry` expects the hyphenated form `role-class`. The header comparison at `config.py` line 377 lowercases both sides, yielding `"role class" != "role-class"` — so this fixture would fail if it actually invoked the parser. The test currently passes only because it passes a pre-built `registry` dict to `deploy_alias_v2`, bypassing `parse_aliases_registry` entirely (see `compose.py` lines 1597-1599).
- **Evidence**:
  - `test_compose_a2f_10492.py` line 60: `f"| Alias | Role class | L3 domain |\n"` — note the space in `Role class`.
  - `config.py` line 302: `_ALIASES_HEADER_COLUMNS = ("alias", "role-class", "L3 domain")` — note the hyphen in `role-class`.
  - `config.py` line 377: `tuple(h.lower() for h in header) != tuple(c.lower() for c in _ALIASES_HEADER_COLUMNS)` — `"role class" != "role-class"` even after lowercasing.
  - The correct form (`role-class`, with hyphen) is used in `CANONICAL_TABLE` at `test_config_aliases_registry_10385.py` line 51, confirming it's the expected format.
- **Suggested fix**: Change `Role class` to `role-class` in `_stage_minimal_install` at `test_compose_a2f_10492.py` line 60. Consider also writing a test that exercises the end-to-end path (fixture config.md → `parse_aliases_registry` → `deploy_alias_v2`) to catch this class of mismatch.