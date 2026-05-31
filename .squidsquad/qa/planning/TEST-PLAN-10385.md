# TEST-PLAN-10385 — PRD-A / Story A5: ## Aliases registry parser

**Source**: GitHub issue #10385 Acceptance Criteria.
**Derived without reading the diff.**

## Test Cases

### TC-1 (covers AC-1): valid 3-col table returns Dict[str, Tuple[str, Optional[str]]]
- **Precondition**: in-memory config.md text containing a canonical `## Aliases` table with 5 rows mixing all 4 role-classes and both em-dash and non-dash L3 values.
- **Steps**: import `config.parse_aliases_registry`, pass the text, inspect the returned dict.
- **Expected**: returns the exact mapping `{alias: (role_class, l3_domain)}`; em-dash cells become `None`, non-dash cells preserved verbatim.
- **Verification command**: live probe in cycle 471 commit; assertion-based, returned `{'pm':('pm',None),'skill':('worker','skill'),'qa':('verifier',None),'dm':('dm',None),'ios-dev':('worker','ios')}` — match.

### TC-2 (covers AC-2): role-class allowlist enforced
- **Precondition**: `config.ALIASES_ROLE_CLASSES` is the exported module constant.
- **Steps**: import constant, compare to spec.
- **Expected**: `frozenset({pm, worker, verifier, dm})`.
- **Verification command**: live probe — `assert config.ALIASES_ROLE_CLASSES == frozenset({'pm','worker','verifier','dm'})` — match.

### TC-3 (covers AC-3): explicit diagnostics on all 7 malformed shapes
- **Precondition**: text fixtures for each malformed shape (missing section, empty section, wrong col count, wrong col names, unknown role-class, duplicate alias, header-only).
- **Steps**: call `parse_aliases_registry(text)` for each; capture exception type and message.
- **Expected**: every shape raises `AliasesRegistryError(ValueError)` with a diagnostic message that names the failure mode and the row/column at fault.
- **Verification command**: live probe — all 7 raised with informative messages (see commit output).

### TC-4 (covers AC-4): unit tests cover all 6 AC-required cases + boundaries
- **Precondition**: `tests/test_config_aliases_registry_10385.py` exists.
- **Steps**: `python -m pytest tests/test_config_aliases_registry_10385.py -v`.
- **Expected**: 19/19 pass; coverage maps to all 6 AC-listed cases (valid, missing-section, malformed-row, unknown-role, duplicate-alias, em-dash-L3) plus declared boundary cases.
- **Verification command**: live execution — 19 passed in 0.08s.

### TC-5 (covers AC-5): no existing callers parse the table inline
- **Precondition**: A1 audit issue #10384 closed confirming no prior parser.
- **Steps**: read dev's PR description claim that legacy `_parse_field_in_text` consumes the bullet format and is untouched per v1-coexistence; spot-check by greping for inline `## Aliases` parsing outside the new function.
- **Expected**: only `parse_aliases_registry()` parses the table; bullet-format reader (`_parse_field_in_text`) remains for the legacy `alias-*` FIELD_MAP rows; compose.py opt-in is A6 (out of scope).
- **Verification command**: `grep -n "## Aliases" references/scripts/*.py` and `grep -n "parse_aliases_registry" references/` — only the new function and its tests reference the table.

## Coverage matrix
- AC-1 → TC-1, TC-4
- AC-2 → TC-2, TC-4
- AC-3 → TC-3, TC-4
- AC-4 → TC-4
- AC-5 → TC-5

Every AC appears in this matrix.

## Comprehension Questions

Not required — this task changes Python code only, no LLM-consumed instructions touched.
