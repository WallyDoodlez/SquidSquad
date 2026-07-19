# TEST-PLAN-13709 (bundled with #13710, shared branch/root cause)

Derived from the issue body's Observation/Location/Suggested-fix.

## ACs
- AC1: `_PATH_RE` extension whitelist includes `j2`; a spec naming a `.j2` fragment is no longer silently dropped from `spec_fragment_paths()`.
- AC2 (process): the fix lands via the project's mandated PR Flow (this install has PR Flow = yes; `git-commit.md` Step 5.3 requires a PR at pending-test).

## Test cases
| TC | Maps to | Method |
|----|---------|--------|
| TC1 | AC1 | `python -m pytest tests/test_comprehension_staleness_13709_13710.py -v` + spot-read the regex diff. |
| TC2 | AC2 | `gh pr list --search "squidsquad/task/13710" --state all` — confirm a PR exists for the branch. |
