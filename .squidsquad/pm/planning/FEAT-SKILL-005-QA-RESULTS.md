# FEAT-SKILL-005 QA Results -- Add Agent Role Command

**Date**: 2026-04-13
**Tested by**: QA verification agent
**Artifacts**: FEAT-SKILL-005-TEST-PLAN.md
**Unit test suite**: 11/11 passed (test_add_role.py)

---

## Previously-Failed QA Items (5 gaps from prior review)

### Gap 1: --dry-run flag
- **Result**: PASS
- **Notes**: `--dry-run` prints planned actions ([dry-run] prefix), exits 0, creates no directories, modifies no files. Verified via `python references/scripts/add_role.py skill --dry-run`.
- **Verified at**: 2026-04-13 11:04

### Gap 2: Lock file concurrency protection via .add-role.lock
- **Result**: PASS
- **Notes**: `_acquire_lock()` uses exclusive file creation (`open("x")`), correctly fails on second call. `_release_lock()` cleans up. Lock is always released in `finally` block (line 261). Unit test `TestLockFile::test_acquire_and_release` passes. Lock file path: `.squidsquad/.add-role.lock`.
- **Verified at**: 2026-04-13 11:04

### Gap 3: 11 unit tests in test_add_role.py
- **Result**: PASS
- **Notes**: All 11 tests pass: 3 role validation tests, 2 parse tests, 1 write test, 1 dry-run test, 1 lock file test, 3 register-existing tests. Tests use mocking appropriately (no real git operations). Run via `python -m pytest tests/test_add_role.py -v`.
- **Verified at**: 2026-04-13 11:04

### Gap 4: Role validation against config.md + references/roles/
- **Result**: FAIL
- **Notes**: `_validate_role()` at line 73 has a logic bug: `has_template` checks `(roles_dir / role / "CLAUDE.md").exists() or (roles_dir / "dev" / "CLAUDE.md").exists()`. Since `references/roles/dev/CLAUDE.md` always exists, the `or` clause makes `has_template` always True for ANY role name, including nonexistent ones like "wizard". Running `python references/scripts/add_role.py wizard` succeeds (exit 0) and creates a full clone instead of rejecting the invalid role. The unit test `test_unknown_role_no_template` passes only because it patches `REPO_ROOT` to `/nonexistent`, bypassing the real filesystem. The fix is to change the `or` to check only the role-specific template: remove the `dev` fallback from `_validate_role`, or restructure so the `dev` fallback only applies when a role is explicitly declared as a dev-variant.
- **Verified at**: 2026-04-13 11:06

### Gap 5: .active-role written before deploy/boot
- **Result**: PASS
- **Notes**: Code at lines 201-203 writes `.active-role` immediately after cloning, before `compose.py deploy` (line 207) and `compose.py boot` (line 215). The write uses `write_text(f"{role}\n")` which includes a trailing newline. The `cat -A` check on the existing `.active-role` in this clone shows `dm` with no extra whitespace. The ordering is correct: clone -> write .active-role -> deploy -> generate boot scripts -> sync .local-config -> optional boot.
- **Verified at**: 2026-04-13 11:06

---

## Test Case Results

### TC-1: Happy path -- add a new role with auto-numbered sibling target
- **Result**: NOT TESTABLE (design divergence)
- **Notes**: The implementation uses `{project_name}-{role}` naming (e.g., `SquidSquad-skill`), not auto-numbered siblings (`SquidSquad-2`, `SquidSquad-3`). This is a design choice, not a bug -- the test plan assumed auto-numbering but the implementation uses role-named directories which is arguably clearer. The core clone+configure+sync flow works correctly.
- **Verified at**: 2026-04-13 11:06

### TC-2: Happy path -- --target specifies a custom clone path
- **Result**: PASS (code review)
- **Notes**: `--target` argument is parsed correctly (lines 325-327), resolved to absolute path via `Path(target).resolve()` (line 159). The target path is used for cloning instead of the auto-generated name. Not executed live to avoid creating test clones.
- **Verified at**: 2026-04-13 11:06

### TC-3: --dry-run shows planned actions without executing them
- **Result**: PASS
- **Notes**: Verified live. `python references/scripts/add_role.py skill --dry-run` outputs 4 [dry-run] lines describing planned actions, exits 0. No clone directory created, no .local-config modified. Dry-run returns before any filesystem or git operations.
- **Verified at**: 2026-04-13 11:04

### TC-4: --boot spawns the agent after clone
- **Result**: PASS (code review)
- **Notes**: Boot logic at lines 235-249 checks platform (win32 vs unix), looks for the appropriate boot script (`start-{role}.ps1` or `start-{role}.sh`), and runs it via subprocess. Includes proper error handling if boot script is missing. Not executed live to avoid spawning agent terminals.
- **Verified at**: 2026-04-13 11:06

### TC-5: --register-existing adds a manually-created clone to config
- **Result**: PASS (with syntax note)
- **Notes**: The implementation syntax is `--register-existing <role> <path>` (requires explicit role argument), while the test plan expected `--register-existing <path>` (auto-detect role from .active-role). The actual implementation works correctly: validates path exists, validates .squidsquad/ directory exists, parses existing .local-config, adds the new entry, syncs to all clones. Verified error paths live: nonexistent path returns 1, path without .squidsquad/ returns 1.
- **Verified at**: 2026-04-13 11:06

### TC-6: Cross-clone .local-config sync -- all existing clones updated
- **Result**: PASS (code review)
- **Notes**: `_sync_local_config()` (lines 111-122) iterates all entries in the agents map and writes .local-config to every clone root that has a `.squidsquad/` directory. Uses `_write_local_config()` which does atomic temp-file writes. All clones receive identical content (sorted entries).
- **Verified at**: 2026-04-13 11:06

### TC-7: Error -- role not in config.md
- **Result**: FAIL
- **Notes**: Running `python references/scripts/add_role.py wizard` does NOT produce an error. Instead it creates a full clone at `SquidSquad-wizard`. Root cause: `_validate_role()` line 73 has an `or` clause that always returns True when `references/roles/dev/CLAUDE.md` exists. See Gap 4 above for details.
- **Verified at**: 2026-04-13 11:06

### TC-8: Error -- target directory already exists
- **Result**: PASS
- **Notes**: Code at line 173 checks `target.exists() and not force`. If target exists without --force, prints error with suggestion to use --force or --register-existing, returns 1. The --force flag triggers `shutil.rmtree(target)` before cloning (line 197).
- **Verified at**: 2026-04-13 11:06

### TC-9: Error -- role already has a registered clone
- **Result**: FAIL
- **Notes**: There is NO check for whether a role is already registered in .local-config. The only guard is the target directory existence check (TC-8). If you run `add_role skill` and `SquidSquad-skill` doesn't exist yet but skill is already in .local-config pointing elsewhere, it will create a second clone and overwrite the .local-config entry. A pre-flight check should query `_parse_local_config()` and reject if the role key already exists (unless --force).
- **Verified at**: 2026-04-13 11:06

### TC-10: git clone --local uses hardlinks
- **Result**: PASS (code review)
- **Notes**: Line 198 uses `git clone --local` which enables hardlink optimization. This is a git feature, not application logic -- git handles hardlinks automatically for local clones on the same filesystem.
- **Verified at**: 2026-04-13 11:06

### TC-11: Windows path handling -- spaces and long paths
- **Result**: PASS (code review)
- **Notes**: All path operations use `pathlib.Path` which handles Windows paths natively. `str(target)` and `str(REPO_ROOT)` produce correct Windows-format paths. The .local-config format preserves paths as-is. No manual string path manipulation that could break with spaces.
- **Verified at**: 2026-04-13 11:06

### TC-12: Unix path handling -- forward slashes and tilde expansion
- **Result**: PASS (code review)
- **Notes**: `Path(target).resolve()` at line 159 handles tilde expansion and resolves to absolute path. pathlib handles forward slashes natively on Unix. Not testable on this Windows environment but code logic is correct.
- **Verified at**: 2026-04-13 11:06

### TC-13: .active-role is written before boot scripts are generated
- **Result**: PASS
- **Notes**: Code order verified: line 203 writes .active-role, line 207-210 runs compose.py deploy, line 214-217 runs compose.py boot. The .active-role file exists before any deploy/boot operations reference it.
- **Verified at**: 2026-04-13 11:06

### TC-14: Atomic .local-config writes -- no partial writes
- **Result**: PASS
- **Notes**: `_write_local_config()` at lines 95-108 writes to `.local-config.tmp` first (line 106), then uses `tmp.replace(path)` (line 108) which is an atomic rename on both Unix and Windows (NTFS). No .tmp file left behind after completion.
- **Verified at**: 2026-04-13 11:06

### TC-15: Stale .local-config entry -- missing clone path tolerated
- **Result**: PASS (code review)
- **Notes**: `_sync_local_config()` checks `config_path.parent.exists()` (line 120) before writing. If a clone path doesn't exist, it simply skips writing to that clone but preserves the entry in all other clones' .local-config. Stale entries are not pruned. The script does NOT abort on stale entries.
- **Verified at**: 2026-04-13 11:06

### TC-16: --dry-run with --boot -- no terminal spawned
- **Result**: PASS
- **Notes**: Verified live. `python references/scripts/add_role.py skill --dry-run --boot` outputs "[dry-run] Would boot agent via start-skill.[sh|ps1]" and exits 0. No clone created, no terminal spawned. The dry_run check at line 161 returns before any boot logic executes.
- **Verified at**: 2026-04-13 11:04

### TC-17: health_check.py sees new agent after add_role
- **Result**: PASS (code review)
- **Notes**: add_role updates .local-config with the new clone path, and health_check.py reads .local-config to discover agents. The format is compatible (`- **role**: path`). After add_role, health_check will include the new agent in its scan. Not tested live to avoid creating permanent clones.
- **Verified at**: 2026-04-13 11:06

### TC-18: --register-existing on a path missing .squidsquad/
- **Result**: PASS
- **Notes**: Verified live. `register_existing()` checks `(clone_path / ".squidsquad").exists()` at line 270. Returns error "Not a SquidSquad clone (no .squidsquad/)" with exit code 1. Test with `D:/Dev/Dev/test-not-squid` confirmed this behavior.
- **Verified at**: 2026-04-13 11:06

### TC-19: Auto-numbered sibling skips occupied directories
- **Result**: NOT IMPLEMENTED
- **Notes**: The implementation does not use auto-numbered siblings. Default target is `{project_name}-{role}` (e.g., `SquidSquad-skill`). There is no logic to detect occupied directories and increment a suffix number. This test case is based on a design assumption that was not implemented.
- **Verified at**: 2026-04-13 11:06

### TC-20: --json flag outputs machine-readable result
- **Result**: NOT IMPLEMENTED
- **Notes**: Running `add_role.py skill --json` returns "Unknown argument: --json" and exits 1. The --json flag is not recognized in the argument parser. No JSON output mode exists.
- **Verified at**: 2026-04-13 11:06

---

## Smoke Tests

- [x] `python references/scripts/add_role.py --help` prints usage without error -- PASS
- [x] `python references/scripts/add_role.py skill --dry-run` exits 0 and prints at least the target path -- PASS
- [x] `.active-role` format: `dm` with no trailing whitespace (checked via `cat -A`) -- PASS
- [ ] `.local-config` parse by health_check.py -- NOT TESTED (would require live clone)
- [ ] `boot_remote.py --all --json` includes new role -- NOT TESTED (would require live clone)

---

## Regression Risks Checked

- **health_check.py compatibility**: .local-config format preserved (`- **role**: path`). No format deviation. PASS.
- **compose.py cwd handling**: Uses `cwd=target` parameter in subprocess calls. PASS.
- **Windows path separators**: Uses pathlib throughout, produces native Windows backslash paths. PASS.
- **Permission errors on atomic rename**: `tmp.replace(path)` may fail if file is locked. No explicit PermissionError handling in `_write_local_config`. MINOR RISK.
- **.active-role trailing newline**: Written as `f"{role}\n"` (line 203). Current `.active-role` shows clean content. Downstream readers use `.strip()`. PASS.
- **Concurrent add_role**: Lock file mechanism implemented and tested. PASS.

---

## Summary

| Category | Count |
|----------|-------|
| PASS | 13 |
| FAIL | 3 |
| NOT IMPLEMENTED | 2 |
| NOT TESTABLE | 1 |

### Failures

1. **TC-7 / Gap 4**: Role validation bypass -- `_validate_role()` always returns True due to `dev` template fallback in `or` clause. Any arbitrary role name is accepted.
2. **TC-9**: No duplicate role registration check. A role already in .local-config can be re-added without --force.
3. **TC-19**: Auto-numbered sibling logic not implemented (design divergence, not necessarily a bug).

### Not Implemented Features

1. **TC-20**: `--json` flag for machine-readable output.
2. **TC-19**: Auto-numbered sibling directory naming.

### Verdict

The 5 previously-failed QA gaps show 4/5 resolved and 1 still failing (Gap 4: role validation). The core clone/configure/sync workflow is solid. The lock file, dry-run, atomic writes, and .active-role ordering are all correctly implemented. The role validation bug (TC-7/Gap 4) is the most significant remaining issue -- it allows creating clones for arbitrary undefined roles.
