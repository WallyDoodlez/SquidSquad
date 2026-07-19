# TEST-PLAN-13735

Derived independently from the issue body (`type:issue` — Observation/Location/Impact/Suggested-fix bug report). Not read from the PR diff before writing this plan.

## ACs (from issue body)

- **AC1**: `references/sub-skills/roles/pm/improvement-scan.md` step 5's wording is fixed to mirror #13711's fix — explicit prepend instruction, not the ambiguous "append."
- **AC2**: No behavioral/data-loss concern — the issue explicitly notes PM's live scan-history.md is already correctly prepended this session (instruction drift only, not data damage), so this is a documentation-only fix.
- **AC3**: Comprehension coverage — since this changes LLM-consumed instructions (a sub-skill fragment), per #9184 a fresh agent reading the fixed text should correctly derive prepend-not-append, same standard as #13711's CQ spec (13711_spec.json). Skill's claim that "no spec references this file" needs independent confirmation — if true, a new spec is needed; if a spec already exists, it needs a baseline refresh.
- **AC4**: Suggested fix's "worth a quick grep for other role-variant scan-history write-steps with the same wording" — confirm whether skill did this sweep and whether any other stale variants remain.

## Test cases

| TC | Maps to | Method |
|----|---------|--------|
| TC1 | AC1 (live) | Read the fixed file, confirm wording matches #13711's pattern (prepend, immediately after preamble/header, FIRST block not last). |
| TC2 | AC2 | Confirm PM's real scan-history.md is currently correctly ordered (spot-check, not a fix target). |
| TC3 | AC3 (live) | `grep -rl "roles/pm/improvement-scan" tests/comprehension/*.json` — confirm skill's "no spec references this file" claim. If true, author a CQ spec per #9184 (same pattern as 13711_spec.json) and spawn a fresh agent to confirm comprehension. |
| TC4 | AC4 (live) | Independently grep all role-variant improvement-scan.md files for the old "append" wording — confirm no other stale variants remain (or file a new finding if any do). |
| TC5 | (regression) | Full test suite / static gate. |
