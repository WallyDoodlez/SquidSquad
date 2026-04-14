# FEAT-SKILL-005 QA Results -- Round 3

**Date**: 2026-04-13
**Scope**: Verify TC-7 and TC-9 fixes only + unit tests

---

## TC-7: Role Validation Bypass -- PASS

**Fix claimed**: Removed dev-template fallback from `_validate_role()`.

**Code review** (`references/scripts/add_role.py` lines 69-79):
- `_validate_role()` now checks only two conditions: (1) role in `_get_configured_agents()`, (2) role has a template dir at `references/roles/<role>/CLAUDE.md`.
- No fallback. Unknown roles are correctly rejected with `return False`.

**Functional test**:
- `python references/scripts/add_role.py goblin` -> `ERROR: Role 'goblin' not found in config.md or references/roles/` with EXIT:1

**Note**: The original QA plan suggested testing with "wizard", but "wizard" is listed in `.squidsquad/config.md` line 9 (`Dev Agents: designer, dev, qa, skill, wizard`), so it passes validation legitimately. Tested with "goblin" instead.

**Verdict: PASS**

---

## TC-9: Duplicate Registration Check -- PASS

**Fix claimed**: Added duplicate check against `_parse_local_config()` before cloning; errors unless `--force`.

**Code review** (`references/scripts/add_role.py` lines 153-161):
- Before any cloning, checks `_parse_local_config()` for existing role entry.
- If found and `--force` not set, prints error to stderr and returns 1.
- `--force` bypasses the check correctly.

**Functional test**:
- `python references/scripts/add_role.py skill` -> `ERROR: Role 'skill' is already registered at D:\Dev\Dev\SquidSquad-2` with EXIT:1
- "skill" exists in `.squidsquad/.local-config`, correctly detected.

**Verdict: PASS**

---

## Unit Tests -- FAIL (1 of 14)

```
13 passed, 1 failed
```

**Failure**: `TestDryRun::test_dry_run_makes_no_changes`
- **Root cause**: The TC-9 duplicate check runs before the dry-run path, so the test needs to mock `_parse_local_config` to return `{}`. This mock exists in the working tree (uncommitted change to `tests/test_add_role.py`) but is NOT committed.
- The uncommitted diff adds `@patch("add_role._parse_local_config", return_value={})` and updates the function signature. This fix is correct but needs to be committed.

**Verdict: FAIL -- uncommitted test fix**

---

## Other Changes Check

```
git log --oneline -5 -- references/scripts/add_role.py
```
- `e6465f2` pm: filed #875 -- boot_remote.py duplicate agent spawn bug (high priority)
- `4d67d10` skill: #5 QA rework: dry-run, lock file, 11 unit tests, role validation, .active-role ordering
- `5e13f84` skill: #5 add_role.py: clone, configure, sync .local-config, optional boot

Commit `e6465f2` touches add_role.py but is labeled as a pm-filed bug for boot_remote.py. No unexpected changes to add_role.py beyond the TC-7/TC-9 fixes in `4d67d10`.

---

## Summary

| Item | Result |
|------|--------|
| TC-7 (role validation bypass) | **PASS** |
| TC-9 (duplicate registration) | **PASS** |
| Unit tests (14 total) | **FAIL** -- 1 failure, uncommitted test fix |

**Action required**: Commit the test fix in `tests/test_add_role.py` (adds `_parse_local_config` mock to `TestDryRun`). The fix is already in the working tree but not staged/committed.
