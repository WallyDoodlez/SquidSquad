# TEST-PLAN-13739

Derived independently from the issue body (`type:issue` — Observation/Context/Impact/Suggested-fix, my own filed finding). Not read from the PR diff before writing this plan.

## ACs (from issue body)

- **AC1**: `verification-templates.md`'s documented QA-RESULTS flow is updated to reflect actual practice — live direct verification (not necessarily a formal pytest file per TC), AC-Walk table as primary content, TC-Results table for machine-parseable coverage.
- **AC2**: TC result-status rules (PASS/FAIL/HUMAN-REQUIRED; no Deferred/Skipped; HUMAN-REQUIRED gate) are preserved — these are substantive, correctness-critical rules, not part of the stale mechanism being replaced.
- **AC3**: No functional/behavioral regression — this is a documentation-accuracy fix only, doesn't change what verifier actually does, just what the doc says.
- **AC4**: Comprehension coverage (#9184, LLM-consumed instruction change) — a fresh agent reading the updated section should correctly derive the actual QA-RESULTS format (AC-Walk + TC-Results, not a per-TC pytest file).

## Test cases

| TC | Maps to | Method |
|----|---------|--------|
| TC1 | AC1 (live) | Read the updated `verification-templates.md` section, confirm it now describes live-direct-verification + AC-Walk + TC-Results, not the old subagent/pytest-file flow. |
| TC2 | AC2 (live) | Confirm the PASS/FAIL/HUMAN-REQUIRED rules and the "Deferred/Skipped are NOT valid" rule and the HUMAN-REQUIRED gate text are present, byte-identical or materially unchanged from before. |
| TC3 | AC3 | Confirm diff scope is doc-only (`references/sub-skills/roles/verifier/verification-templates.md`), no code files touched. |
| TC4 | AC4 (live) | Spawn a fresh agent given ONLY the updated file, ask it to describe the QA-RESULTS format it should produce — confirm it correctly derives AC-Walk + TC-Results, not a pytest-file-per-TC approach. |
| TC5 | (regression) | Full test suite / static gate; confirm 1428_spec.json's baseline refresh (mentioned in skill's comment) is correct — same standard as this session's earlier verifications of that spec. |
