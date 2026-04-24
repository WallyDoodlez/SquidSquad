# FEAT-PM-2361 Research — TC coverage gate (mechanical check: TEST-PLAN vs QA-RESULTS)

## Summary
Researched the repo for existing “coverage gate” mechanisms around test plans and QA results, and where a “pending-ship” block could be enforced. The codebase already has (a) a deterministic QA framework that rejects “Deferred” as a valid result and (b) a status lifecycle with a `status:pending-ship` transition controlled by `references/scripts/tracker.py`, but there is currently **no mechanical script** that compares `*-TEST-PLAN.md` vs `*-QA-RESULTS.md` and fails closed on missing/invalid TC results.

Recommendation: add a new repo script `references/scripts/tc_coverage.py` and wire it into the existing “pending-ship” transition path (most likely inside `references/scripts/tracker.py transition ... pending-test -> pending-ship`) so that shipping cannot proceed unless coverage is 100% and all results are valid (PASS/FAIL/BLOCKED only). Primary risks are (1) inconsistent TC formatting across historical markdown files and (2) multiple QA results revisions (`-R2`, `-R3`) requiring deterministic selection rules.

## Vault Context
- **BRIEFING.md priorities**: none directly for this task (active priorities listed are #2353, #2350, #2189, #1772) — but BRIEFING explicitly states “Never ship with failed test cases” (see `.squidsquad/vault/BRIEFING.md:24`).
- **Related decisions**: none found in vault for `decision-deterministic-testing.md` (file not present under `.squidsquad/vault/decisions/`; vault grep returned no matches).
- **Related patterns**: Deterministic QA verification framework is enforced by tests (see `tests/test_deterministic_qa_framework.py:1-85`), including explicit rejection of “Deferred” as a valid result (`tests/test_deterministic_qa_framework.py:54-58`).
- **Human preferences**: “Never ship with failed test cases” (`.squidsquad/vault/BRIEFING.md:24`) and preference for direct/mechanical checks over indirect state (`.squidsquad/vault/areas/human-profile.md:33-34`).
- **Related learnings**: none located in vault for “#1291 deterministic testing” (vault grep for `1291` returned no matches). Note: there *is* a `FEAT-PM-1291-TEST-PLAN.md` and `FEAT-PM-1291-QA-RESULTS.md` in planning folders (see Impact Analysis).

## Impact Analysis
- **Files touched**:
  - `references/scripts/tc_coverage.py` (new) — implement parsing + coverage computation + exit codes.
  - `references/scripts/tracker.py` — add a gate before allowing `status:pending-test -> status:pending-ship` (transition is defined at `references/scripts/tracker.py:131-134` and authority at `:186-193`).
  - `tests/` (new unit tests) — add tests for tc_coverage parsing and tracker integration (pattern: existing deterministic QA framework tests in `tests/test_deterministic_qa_framework.py`).
  - Potentially documentation/templates if you want to standardize TC markers, but this repo already has a test-plan template with deterministic categories (`tests/test_deterministic_qa_framework.py:13-45` references `references/prompts/test-plan.md.j2`).
- **Behavior changes**:
  - Transition to `status:pending-ship` becomes **fail-closed** if:
    - Any TC in TEST-PLAN is missing from QA-RESULTS, or
    - Any QA-RESULTS entry is marked `not-applicable` or `deferred` (explicitly invalid per task), or
    - Coverage < 100%.
  - QA-RESULTS with only partial verification will block shipping even if a human “hand-waves” N/A.
- **Dependencies**:
  - Python runtime (repo already uses Python scripts under `references/scripts/*.py`).
  - Markdown parsing will likely be regex-based (no existing markdown parser dependency found in `references/scripts/` via grep).
  - GitHub issue lifecycle enforcement is centralized in `references/scripts/tracker.py` (status labels and transitions).

## Side Effects
- **Risk 1**: Historical/variant markdown formats cause false negatives (script can’t find TCs) — Severity: M — Mitigation: implement tolerant regexes (e.g., accept `TC-01`, `TC-1`, `TC 01`) and add a `--debug` mode that prints unmatched lines + counts; add unit tests using real fixture snippets from existing `*-TEST-PLAN.md` / `*-QA-RESULTS.md` files.
- **Risk 2**: Multiple QA results revisions (`*-QA-RESULTS-R2.md`, `-R3.md`) lead to gating against the wrong file — Severity: M — Mitigation: deterministic selection rule (prefer highest `-R{n}` if present; else base file). Repo contains examples: `FEAT-SKILL-442-QA-RESULTS-R2.md` and `FEAT-SKILL-005-QA-RESULTS-R3.md` (see glob results).
- **Risk 3**: Blocking `pending-ship` may disrupt existing flows where QA results are stored outside expected directories — Severity: L/M — Mitigation: allow explicit CLI args `--test-plan path --qa-results path` and have tracker pass explicit paths when known; otherwise search in conventional planning directories.

## Edge Cases
- **TC numbering gaps / retired TCs**: Some plans may intentionally obsolete a TC (example pattern exists in tests: “TC-78 obsolete” is documented in `tests/test_feat328_coverage.py:257-274`). Handling: require QA-RESULTS to explicitly mark retired TCs as PASS with note, or introduce an explicit “RETIRED” marker in both docs (but task request says reject not-applicable/deferred; doesn’t mention retired—needs decision).
- **Duplicate TC IDs** in TEST-PLAN or QA-RESULTS: treat as error (ambiguous) and fail closed.
- **QA-RESULTS contains extra TCs** not in TEST-PLAN: warn or error; recommend error to keep deterministic mapping.
- **BLOCKED results**: deterministic QA framework already treats BLOCKED as a gate that prevents shipping (see `tests/test_deterministic_qa_framework.py:60-65`). tc_coverage should count BLOCKED as “accounted for” but still fail the gate (coverage may be 100% but ship must be blocked).

## Integration Risks
- **Risk**: Where to enforce the gate in lifecycle tooling — tracker is the single source of truth for transitions (`references/scripts/tracker.py:2-31`), and `pending-test -> pending-ship` is a key edge (`:131-134`). If enforcement is added elsewhere (e.g., DM shipping step), it may be bypassed by direct transition calls. Mitigation: enforce in `tracker.py transition` path for the specific edge(s), and ensure `--force` does *not* bypass coverage unless explicitly intended (human preference suggests it should not).

## Upgrade & Migration
- **New config values**: none required (recommended default behavior: auto-discover matching TEST-PLAN/QA-RESULTS in planning dirs; optional CLI overrides).
- **New files**:
  - `references/scripts/tc_coverage.py`
  - New tests, e.g. `tests/test_tc_coverage.py` (name TBD)
- **Template changes**: none required for initial implementation (existing template enforcement already exists via `tests/test_deterministic_qa_framework.py`), but may be desirable later to standardize QA-RESULTS formatting.
- **Upgrade steps**: N/A — no state migration required; but teams must ensure QA-RESULTS uses valid result tokens (PASS/FAIL/BLOCKED) and does not use not-applicable/deferred.
- **Graceful degradation**: If users don’t upgrade scripts, they can still manually transition via older tooling; but in-repo tooling should fail closed once updated. (If this repo is distributed, versioning/release notes should call out the new gate.)

## Open Questions
- **Q1**: What is the canonical TC syntax across all TEST-PLAN/QA-RESULTS files (e.g., `TC-01` vs `TC-1`, headings vs tables)? — **Why**: parser strictness determines whether the gate blocks valid work or misses missing TCs.
- **Q2**: Should `--force` in `tracker.py transition` bypass tc_coverage? — **Why**: allowing bypass undermines “never ship with failed/missing TCs”; disallowing bypass may block emergency interventions.
- **Q3**: How to map an issue/feature to the correct TEST-PLAN/QA-RESULTS pair during `pending-test -> pending-ship`? — **Why**: tracker operates on GitHub issue numbers; docs are stored as markdown files with various naming conventions (e.g., `FEAT-PM-1291-...`, `FEAT-SKILL-...`, `ISSUE-...`).

## Recommendation
Feasible with caveats. The repo already centralizes lifecycle transitions in `references/scripts/tracker.py` and already has deterministic QA constraints tested in `tests/test_deterministic_qa_framework.py`. Implement `references/scripts/tc_coverage.py` and enforce it specifically on the `pending-test -> pending-ship` transition (defined in `references/scripts/tracker.py:131-134`, authority at `:186-193`). Biggest caveat is robust TC parsing across existing markdown variants and deterministic selection among multiple QA-RESULTS revisions (`-R2`, `-R3`).