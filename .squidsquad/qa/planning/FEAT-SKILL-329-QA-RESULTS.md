# QA Results — #329 Consistent Per-Cycle Reporting

## Summary
- Total: 33 (25 TC + 8 Smoke)
- Pass: 31
- Fail: 1
- Skip: 1

## Results

### TC-1: Active cycle log-iteration (skill role)
- **Result**: PASS
- **Evidence**: `python references/scripts/cycle.py log-iteration _test_role 1 --issues "#100 #101" --tasks "refactor parser" --notes "test active cycle"` produced iter-1.md with correct unified format: `# Iteration 1`, `- **Date**: 2026-04-17 21:33`, `- **Type**: active`, `- **Work Summary**:` with `Issues: #100 #101` and `Tasks: refactor parser` bullets, `- **Notes**: test active cycle`.
- **Notes**: All fields present and correctly formatted.

### TC-2: Quiet cycle log-iteration
- **Result**: PASS
- **Evidence**: `--quiet` flag produced condensed entry: `- **Type**: quiet`, `- **Note**: No actionable work available`. Only 4 lines total (header + 3 metadata lines).
- **Notes**: Quiet format is compact as designed.

### TC-3: Quiet cycle with custom notes
- **Result**: PASS
- **Evidence**: `--quiet --notes "Waiting for upstream PR"` produced `- **Note**: Waiting for upstream PR`.
- **Notes**: Custom note correctly overrides default.

### TC-4: Active cycle with tests param
- **Result**: PASS
- **Evidence**: `--issues "#200" --tasks "add tests" --tests "15 pass, 0 fail"` produced three work bullets: Issues, Tasks, Tests. All rendered correctly.
- **Notes**: Tests param properly included in work summary.

### TC-5: Active cycle with "none" values
- **Result**: PASS
- **Evidence**: `--issues "none" --tasks "none" --tests "n/a"` produced `- **Work Summary**:` with `  - none` (single empty bullet). The "none"/"n/a" sentinel values are correctly filtered out.
- **Notes**: Sentinel filtering works as designed.

### TC-6: Active cycle with --work param (unified format)
- **Result**: PASS
- **Evidence**: `--work "Fixed #300, Deployed compose.py"` produced two separate bullets: `  - Fixed #300` and `  - Deployed compose.py`. Comma-separated values correctly split.
- **Notes**: Unified `--work` param works correctly.

### TC-7: Active cycle for different role
- **Result**: PASS
- **Evidence**: Same format produced for a different test role. Issues and Tasks bullets correct.
- **Notes**: Role-independent format confirmed.

### TC-8: vault_remember.py is-quiet after active cycle
- **Result**: PASS
- **Evidence**: After creating an active iter file (iter-7), `vault_remember.py is-quiet _test_role` returned `non-quiet` with exit code 1.
- **Notes**: Correctly detects active cycle.

### TC-9: vault_remember.py is-quiet after quiet cycle
- **Result**: PASS
- **Evidence**: After creating quiet iter-8, `vault_remember.py is-quiet _test_role` returned `quiet` with exit code 0.
- **Notes**: Correctly detects quiet cycle via Type field.

### TC-10: Numbering gaps
- **Result**: PASS
- **Evidence**: Created iter-10 (skipping 9). File created successfully. Directory shows iter-1 through iter-8 plus iter-10.
- **Notes**: No sequential numbering enforcement, gaps handled gracefully.

### TC-11: Non-numeric iteration number
- **Result**: PASS
- **Evidence**: `log-iteration _test_role abc` produced `ERROR: iteration number must be numeric, got 'abc'` on stderr with exit code 1.
- **Notes**: Proper input validation and error message.

### TC-12: Quiet cycle counter management
- **Result**: PASS
- **Evidence**: `reset-counter` -> 0, `inc-counter` -> 1, `inc-counter` -> 2, `get-counter` -> 2. All counter operations work correctly via working-state.md.
- **Notes**: Counter persists in working-state.md regex field.

### TC-13: Old format coexistence
- **Result**: PASS
- **Evidence**: Existing iter files in skill (iter-43.md with `Issues Fixed`/`Tasks Progressed` format) and pm (iter-343.md with `Human Check-in`/`Issues Filed` format) are untouched and readable. New unified format uses `Type`/`Work Summary` fields.
- **Notes**: Old and new formats coexist without conflict.

### TC-14: is-quiet on role with no iterations directory
- **Result**: PASS
- **Evidence**: `vault_remember.py is-quiet _empty_role` returned `quiet` (no iterations dir = quiet).
- **Notes**: Graceful handling of missing directory.

### TC-15: Old format without Type field
- **Result**: PASS
- **Evidence**: An old-format iter file (with `Bugs`/`Features` fields but no `Type` field) is treated as `non-quiet` by vault_remember.py. This is correct -- old active files should not be misclassified as quiet.
- **Notes**: Fallback behavior is safe and correct.

### TC-16: cleanup-iterations
- **Result**: PASS
- **Evidence**: Created 25 iter files, ran `cleanup-iterations --keep 5`. Removed 20 files, kept 5 most recent (iter-21 through iter-25 by mtime).
- **Notes**: Cleanup uses mtime ordering, works correctly.

### TC-17: vault write-budget (side effect check)
- **Result**: PASS
- **Evidence**: `vault_remember.py write-budget _test_role` returned `2` (default budget). No side effects on working-state.
- **Notes**: Read-only check, no mutations.

### TC-18: Existing commands regression (timestamp, timestamp-short, step-marker)
- **Result**: PASS
- **Evidence**: `timestamp` -> `2026-04-17 21:34`, `timestamp-short` -> `21:34:46`, `step-marker "test marker"` -> `[squid 21:34:46] test marker`. All existing commands work unchanged.
- **Notes**: No regressions in pre-existing commands.

### TC-19: Counter regression (inc-counter, reset-counter, get-counter)
- **Result**: PASS
- **Evidence**: `reset-counter` -> 0, `inc-counter` -> 1, `get-counter` -> 1, `reset-counter` -> 0. Full round-trip works.
- **Notes**: No regressions in counter management.

### TC-20: Old format preservation
- **Result**: PASS
- **Evidence**: Existing pm/iter-343.md still starts with `# PM Iteration 343` (old format). Existing skill/iter-43.md still starts with `# SKILL Iteration 43` (old format). Neither was modified.
- **Notes**: Feature does not alter existing files.

### TC-21: compose.py deploy-all
- **Result**: PASS
- **Evidence**: `compose.py deploy-all` completed successfully. All 4 composed CLAUDE.md files exist: skill (56811 bytes), pm (82383 bytes), qa (35953 bytes), dm (32596 bytes).
- **Notes**: Composition pipeline works end-to-end.

### TC-22: Template references log-iteration
- **Result**: PASS
- **Evidence**: All 4 composed CLAUDE.md files contain `log-iteration` references (2 each -- active and quiet examples). Skill line 567, pm line 797, qa line 583, dm line 529.
- **Notes**: All roles have correct iteration logging instructions.

### TC-23: Quiet-cycle instructions in templates
- **Result**: PASS
- **Evidence**: All 4 composed CLAUDE.md files contain `--quiet` flag (1 reference each) and multiple references to quiet cycle behavior (skill: 14, pm: 14, qa: 9, dm: 8 total quiet-related mentions).
- **Notes**: Quiet cycle instructions properly deployed to all roles.

### TC-24: Unified format in templates (no old --bugs/--features)
- **Result**: PASS
- **Evidence**: Templates reference `--work` param and "unified format" description. Zero references to `--bugs` or `--features` flags in any composed CLAUDE.md.
- **Notes**: Clean migration from old to new format in templates.

### TC-25: Source templates reference log-iteration
- **Result**: PASS
- **Evidence**: Source sub-skill files found at: `references/sub-skills/common/iteration-log.md`, `references/sub-skills/pm-specific/iteration-log.md`, `references/sub-skills/qa-specific/iteration-log.md`, `references/sub-skills/dm-specific/iteration-log.md`. All reference `log-iteration` with `--work` and `--quiet` flags. All describe "unified format with Date, Type (active/quiet), Work Summary, and Notes".
- **Notes**: Source templates consistent with composed output.

---

## Smoke Tests

### SM-1: --quiet flag in all composed templates
- **Result**: PASS
- **Evidence**: All 4 roles (skill, pm, qa, dm) have exactly 1 `--quiet` reference in their composed CLAUDE.md.

### SM-2: "unified format" description in all templates
- **Result**: PASS
- **Evidence**: All 4 roles have exactly 1 "unified format" mention.

### SM-3: cleanup-iterations in all templates
- **Result**: PASS
- **Evidence**: All 4 roles have exactly 1 `cleanup-iterations` reference.

### SM-4: No old --bugs/--features in templates
- **Result**: PASS
- **Evidence**: Zero references to `--bugs` or `--features` in any composed CLAUDE.md.

### SM-5: Role-specific sub-skills use correct role name
- **Result**: PASS
- **Evidence**: pm-specific uses `pm [N]`, qa-specific uses `qa [N]`, dm-specific uses `dm [N]`, common uses `[ROLE] [N]`.

### SM-6: Quiet entries are condensed
- **Result**: PASS
- **Evidence**: Quiet iter files are 4 lines (header + date + type + note). Active files are 6+ lines. Templates describe "condensed (2-3 lines)".

### SM-7: cycle.py is-quiet command (listed in help)
- **Result**: FAIL
- **Evidence**: `cycle.py --help` lists `is-quiet <role>` as a command, but running `cycle.py is-quiet _test_role` returns `Unknown command: is-quiet`. The `is-quiet` subcommand is documented in the help text (line 14) but has no handler in `main()`. The actual is-quiet functionality exists only in `vault_remember.py`.
- **Notes**: Bug: cycle.py help advertises `is-quiet` but doesn't implement it. Either add a handler that delegates to vault_remember.py logic, or remove from help text.

### SM-8: Comprehension test -- agent understands new format
- **Result**: SKIP
- **Evidence**: N/A -- requires spawning a fresh agent to quiz on iteration log format.
- **Notes**: Manual comprehension test, cannot be automated.

---

## Bugs Found

### BUG: cycle.py help lists `is-quiet` command but doesn't implement it
- **File**: `references/scripts/cycle.py`, line 14 (docstring) vs `main()` function (missing handler)
- **Severity**: Low (cosmetic/documentation)
- **Impact**: Agent following cycle.py help could attempt `cycle.py is-quiet` and get an error. The actual functionality is in `vault_remember.py is-quiet`.
- **Fix**: Either add `elif cmd == "is-quiet":` handler in main() that reuses vault_remember.py logic, or remove line 14 from the docstring.
