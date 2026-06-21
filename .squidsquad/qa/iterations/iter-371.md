# iter-371 — 2026-06-19 ~18:05 (POLLING /loop session)

**PRODUCTIVE: TWO verifications → both PASS → pending-ship (DM).** Both high-sev bugs from the #12895 stale-source-recompose work.

## #12906 VERIFIED → PASS → pending-ship
Phase 1 of #12895 — harness recompose must ensure-main + pull-first (PR #12908, branch squidsquad/task/12906, MERGEABLE/CLEAN, Closes-keyword). type:issue/high, role:skill.
- AC1: new `git_ops.ensure_main_and_pull(role)` (git_ops.py:240) = checkout main on mismatch (abort on fail) → `pull()` = MERGE (git_ops.py:194, never-rebase) → never-raises. Wired into ALL 3 recompose paths, freshen-BEFORE-compose + abort-on-fail: l4_file_watcher.recompose_path (L314), _on_change (L427, freshens before registry read), harness.py post-merge deploy-all (L3758 = the path that reverted during #12800 ship). Abort emits compose-failed→PM (observable). Test TestFreshnessGuard12906 locks ordering (order[0]=='fresh', once/batch) + abort-skips-compose + guard-raise-aborts.
- AC2: no regression — l4/git_ops 186 + harness 290 + static gate 4647/0-fail.
- AC3: no new files → installer-files unchanged (correct).
- No CQ (code-only). Phase 1 scope respected (deploy-signal layer = Phase 2 on #12895).

## #12907 VERIFIED → PASS → pending-ship
installer-files.txt missing 9 l4_*.py (PR #12910, branch squidsquad/task/12907, MERGEABLE/CLEAN, Closes-keyword). type:issue/high, role:skill.
- All 9 l4_*.py present; header '# Total: 215 files' matches actual 215 (counted). Integrity: all 215 manifest entries resolve to real files (zero dangling).
- Regression: test_installer_wiring.py +test_l4_subsystem_scripts_listed (globs l4_*.py, asserts each listed — locks exact bug) +test_header_total_matches_entry_count (add-without-recount canary); 24/24.
- **SCOPE NOTE → PM (non-blocking)**: my independent sweep found 17 OTHER references/scripts/*.py still absent incl. **critical event_poll.py** (every agent spawns it for event mode → fresh install can't run event mode). Out of #12907 scope; correctly split to #12909 (high, OPEN — broad completeness audit + per-script dev-vs-runtime triage + allowlist test). Skill disclosed it. Recommended PM prioritize #12909.
- No CQ (manifest data + test).

Both merges deferred to DM (Closes-keywords → QA-merge would auto-close+skip DM). Counter NOT bumped. QA-RESULTS-12906 + QA-RESULTS-12907 on main.

Boot/mode unchanged: POLLING (harness :64049 EXIT=7), `/loop 30m` cron `615cf252`.
