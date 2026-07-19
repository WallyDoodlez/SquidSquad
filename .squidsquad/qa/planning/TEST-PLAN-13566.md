# TEST-PLAN-13566

Derived independently from `CONTEXT-13566.md` (authoritative scope) + issue body ACs.

## ACs (from issue body + CONTEXT-13566.md Upgrade Path)

- **AC1**: `scan_index.py` rebuild enforces the retention cap (~100 newest entries); archive file carries the remainder, findable not deleted.
- **AC2**: Fallback instruction (`improvement-scan.md`) reads bounded content (~50 newest entries, correctly from the START of the file per the prepend convention); CQ scenario covers a fresh agent hitting the fallback on an oversized file.
- **AC3**: Unit test — rebuild over an oversized fixture produces capped history + archive.
- **Upgrade Path (required)**: one-time prune of existing oversized files across all four roles happens via the new code path, not a separate manual migration step — "existing installs self-heal on next rebuild."

## Test cases

| TC | Maps to | Method |
|----|---------|--------|
| TC1 | AC1 (live) | Backed up skill's real `.squidsquad/skill/scan-history.md` (153,820B, the file cited in the issue), ran the real unmocked `python references/scripts/scan_index.py rebuild`, inspected the result, reverted. |
| TC2 | AC2 (wording) | Read the diff to `improvement-scan.md`; confirm it correctly says "first ~50 blocks" (start of file), not "last ~50" or "tail" — entries are prepended newest-first, so a naive tail-read would be backwards. |
| TC3 | AC2 (CQ) | Search the branch diff and `tests/comprehension/` for a new spec covering this scenario. |
| TC4 | AC3 | `python -m pytest tests/test_scan_index.py -v`. |
| TC5 | Upgrade Path (live) | Repo-wide grep for every caller of `scan_index.py rebuild` (direct Python call and CLI subprocess invocation) across `references/scripts/*.py`, `references/sub-skills/**`, and the composed `skill/CLAUDE.md`, to determine whether `rebuild` — and therefore the new pruning logic — is ever invoked without a human manually typing the command. |

## Coverage matrix
- AC1 → TC1
- AC2 → TC2, TC3
- AC3 → TC4
- Upgrade Path → TC5
