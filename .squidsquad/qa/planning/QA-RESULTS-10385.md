# QA-RESULTS-10385 — PRD-A / Story A5: ## Aliases registry parser

**Verifier**: QA-lead, cycle 471, branch `squidsquad/task/10385` @ a9216b1d.

## Summary
- **TC-1**: PASS
- **TC-2**: PASS
- **TC-3**: PASS
- **TC-4**: PASS
- **TC-5**: PASS
- **Dev unit tests**: 19/19 PASS (`tests/test_config_aliases_registry_10385.py`, no mocks)
- **Canonical suite**: `python tests/run_tests.py` — **52 passed, 2 skipped, 0 failed** on this branch
- **External code review**: dev ran model_router code-review — NO_FINDINGS

## Live-system probe verbatim (TC-1, TC-2, TC-3, TC-5)

```
=== AC1: valid 3-col table ===
  -> {'pm': ('pm', None), 'skill': ('worker', 'skill'), 'qa': ('verifier', None), 'dm': ('dm', None), 'ios-dev': ('worker', 'ios')}
  AC1 PASS

=== AC2: role-class allowlist ===
  ALIASES_ROLE_CLASSES = ['dm', 'pm', 'verifier', 'worker']
  AC2 PASS

=== AC3: diagnostics ===
  [missing section] OK   -> config.md is missing the required `## Aliases` section …
  [empty section]   OK   -> `## Aliases` section is present but contains no table …
  [wrong col count] OK   -> `## Aliases` header row must be exactly …
  [wrong col names] OK   -> `## Aliases` header row must be exactly …
  [unknown role]    OK   -> `## Aliases` data row 1 (`pm`) has unknown role-class `wizard` …
  [dup alias]       OK   -> `## Aliases` has duplicate alias `pm` (data row 2).
  [header only]     OK   -> `## Aliases` table has a header but zero data rows. …
  AC3 PASS (all 7 malformed inputs raised AliasesRegistryError)

=== AC5 sanity: AliasesRegistryError is ValueError ===
  AC5 PASS
```

## TC-5 inline-parse audit
`grep -rn "## Aliases" references/scripts/*.py` returns only two non-test references in `config.py`:
- L20: docstring for `_parse_sections`
- L445: docstring for the legacy `get_alias` reader (bullet format, not table)
Neither parses the table; `parse_aliases_registry` is the only table parser. v1-coexistence pattern intact.

## Notable behavior observation (NOT a defect)
Calling `parse_aliases_registry()` with no argument against the **current live** `.squidsquad/config.md` raises `AliasesRegistryError("section is present but contains no table")` — the live file still uses the legacy `- **alias**: value` bullet format. This is correct: AC-5 explicitly says the table format is the new schema and compose.py opt-in is A6's responsibility. No caller invokes the new parser yet, so this exception path is not exercised in production today.

## Verdict
All 5 ACs verified PASS. No HUMAN-REQUIRED gates. Recommending pending-test → pending-ship.
