# Working State

- **Task**: 12906 — IMPLEMENTED + all gates green; shipping to pending-test (code → branch squidsquad/task/12906, PR pending).
- **Updated**: 2026-06-19 (skill — event-mode; #12906 implemented + DS-reviewed + static gate 4647/0)
- **Quiet Cycle Counter**: 0

## #12906 (HIGH, Phase 1 of #12895) — DONE, shipping
Ensure-main + pull-first guard before every harness-side recompose (kills #12895 stale-source fleet-revert at root).
- **Impl:** new `git_ops.ensure_main_and_pull(role)` (canonical guard, never-raises contract). `l4_file_watcher.py` both batch entries (`_on_change` watch path + `recompose_path` hook path) freshen ONCE before composing via injectable `ensure_fresh_source=`; watch path freshens BEFORE registry read (post-pull config.md). Abort-on-failure = no compose against stale source + `compose-failed`-to-PM event (observable) + agents keep last-known-good. `harness.py` post-merge `deploy-all` (the #12800-ship reverter) freshens before compose, skips on failure.
- **Gates:** static 4647/0; targeted l4(41)+git_ops(147)+harness(290) green; deploy-all zero composed drift (AC2); DS review 4 warnings ALL resolved (DS-REVIEW-12906.md). AC3: no references/ files added/removed → installer-files unchanged.
- **Scope boundary held:** Phase 2 (deploy-signal/non-interruption layer) NOT built here — stays on #12895 (PM design-v2 posted, operator-scope-confirm gated). #12906 introduces the FIRST harness-side git op (PM flagged this as new machinery — deliberate, minimal, recompose-path-only).
- **Filed #12907** (high): all 9 `l4_*.py` scripts missing from installer-files.txt manifest (pre-existing; entire L4 subsystem unshipped to fresh installs). Out of #12906 scope.

## Ship steps remaining
1. commit-code → squidsquad/task/12906 (4 code files). 2. sync main + commit-state (planning artifacts + this file). 3. pr-create. 4. transition #12906 in-progress→pending-test.

## NEXT actionable (after #12906 ships)
1. **#12907** (high, mine): add 9 l4_*.py to installer-files.txt + bump header count + manifest-completeness test. Low-risk mechanical; touches installer surface.
2. **#12905** (medium, mine): pre-commit galaxy-frontmatter guard + test. High-blast-radius (pre-commit hook).
3. **#12801** S1.3+ (Textual TUI): needs `textual` installed + interactive terminal. Plan: planning/TUI-12801-DECOMPOSITION.md.
4. **#12895** Phase 2: awaiting PM doc-first arch spec + operator scope-confirm (DEPLOY-SIGNAL-DESIGN-12895.md posted). Folds #12519.

## Recurring meta-risk
This clone chronically boots/sits behind origin (#12526) → #12895 stale-recompose. Verify `git pull` synced BEFORE any compose/commit each session. (Hit it again this session: was 9 behind at #12906 start; pulled+pushed before implementing.)
