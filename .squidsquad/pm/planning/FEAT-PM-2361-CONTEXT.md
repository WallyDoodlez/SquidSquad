# FEAT-PM-2361 Context — TC Coverage Gate

## Scope

A mechanical gate that prevents shipping when QA-RESULTS.md doesn't cover all TCs in TEST-PLAN.md. Pure markdown parser — does not run tests, language-agnostic. Enforced at `pending-test → pending-ship` transition in tracker.py.

## Locked Decisions (human decided)

- **Tolerant regex parser**: Accept TC-01, TC-1, TC 01, ### TC-1:, table rows. Normalize all variants to canonical TC-N internally. Include --debug flag for diagnostics. No migration of existing files required.
- **Auto-discover by convention**: Search `.squidsquad/[role]/planning/` for `*-[NUMBER]-TEST-PLAN.md` and `*-[NUMBER]-QA-RESULTS*.md`. Pick highest -RN revision for multiple results. Fall back to explicit `--test-plan` and `--qa-results` CLI args if auto-discovery fails or is ambiguous.
- **No --force bypass**: `--force` in tracker.py overrides role-authority only, never skips TC coverage gate. To ship without coverage in a true emergency, human must manually `gh issue close` outside normal workflow. Aligns with "never ship with failed TCs" preference.

## Dev Discretion (dev agent can choose)

- Exact regex patterns for tolerant matching
- Internal normalization format (e.g., zero-padded vs not)
- --debug output format
- Error message wording

## Side Effect Mitigations (required)

- **False positives**: The tolerant parser must not match TC references in prose (e.g., "see TC-1 for details" in a paragraph, vs "### TC-1: Title"). Only match TC markers in heading/table-row position.
- **Multiple planning dirs**: When both `.squidsquad/pm/planning/` and `.squidsquad/[role]/planning/` have matching files, prefer the PM planning dir (PM owns test plans).
- **No TEST-PLAN exists**: If no TEST-PLAN.md matches the issue number, skip the gate entirely (manual verification tasks). Do not block on missing plan.
- **BLOCKED results**: Count as "accounted for" in coverage (TC is present in results) but still block pending-ship (BLOCKED = cannot ship).

## Upgrade Path (required)

- **New files**: `references/scripts/tc_coverage.py`, `tests/test_tc_coverage.py`
- **Modified files**: `references/scripts/tracker.py` (add gate at pending-test → pending-ship transition)
- **Upgrade steps**: N/A — no state migration. Existing QA-RESULTS files using "not applicable"/"deferred" will fail the gate on future transitions, which is the intended behavior.
- **Graceful degradation**: If tc_coverage.py is missing (old install), tracker.py should not crash — skip the gate with a warning.

## Out of Scope

- Running actual tests (that's QA's job)
- Linting TEST-PLAN format at creation time (future enhancement)
- Migrating existing QA-RESULTS files to remove "not applicable" entries
