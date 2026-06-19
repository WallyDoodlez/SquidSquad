# QA-RESULTS-12906 — VERDICT: PASS → pending-ship

- **Verified**: 2026-06-19 18:05 (cy371, POLLING session)
- **Issue**: #12906 (type:issue/high, role:skill) — Phase 1 of #12895: harness-side recompose/deploy MUST ensure-main + pull-first before composing, so a behind/feature-branch clone can't regenerate composed `CLAUDE.md` from stale source and push a revert fleet-wide (observed 3× on 2026-06-19).
- **PR**: #12908, branch `squidsquad/task/12906` (MERGEABLE/CLEAN, "Closes #12906").
- **Result**: **PASS — all 3 ACs + zero regression.** Append-only.

## Evidence (independent, on-branch)
- **AC1 (ensure-main + pull before every compose) — PASS.**
  - New canonical guard `git_ops.ensure_main_and_pull(role)` (git_ops.py:240): checks branch → `git checkout main` on mismatch (abort on failure) → `pull()`. `pull()` is **merge** (git_ops.py:194 "Pull with merge", `git pull` default — satisfies [[feedback_never_rebase_merge_instead]]). **Never-raises contract** (blanket try/except → returns `(ok, detail)`).
  - Wired into **all three** harness-side recompose paths, each freshen-BEFORE-compose with abort-on-failure:
    1. `l4_file_watcher.recompose_path` (L314-319): `_freshen_or_abort` → on fail `return []` before `recompose_for_role_class`.
    2. `l4_file_watcher._on_change` (L427-434): freshens BEFORE the registry read (so a pulled-in `config.md` `## Aliases` change is reflected) and before compose; on fail `return`.
    3. `harness.py` post-merge `deploy-all` (L3758-3770, **the exact path that reverted during #12800's ship**): `ensure_main_and_pull("harness")` → on fail emit `compose-completed success:False` + `return` (no deploy).
  - Abort is **observable**: a stale-source abort emits `compose-failed` → PM (DS-12906 F1), agents keep last-known-good.
  - **Test (locks AC1)**: `TestFreshnessGuard12906` in `tests/test_l4_file_watcher_e3.py` — `test_recompose_path_freshens_before_compose` asserts the guard fires exactly once and strictly before any compose (`order[0]=="fresh"`); `test_recompose_path_abort_skips_compose_and_events` asserts a failing guard → `results==[]`, `composed==[]` (no compose against stale source) + one `compose-failed` event to PM; `test_recompose_path_guard_raise_aborts` covers the never-crash path. This is the "behind clone pulls first / stale source never composes" AC1 demands.
- **AC2 (no regression to deploy outputs) — PASS.** The guard is a pure pre-step; it does not touch compose logic. `tests/test_l4_file_watcher_e3.py` + `tests/test_git_ops.py` = **186 passed**; `tests/test_harness.py` = **290 passed**; `run_tests.py static` = **`[static-gate] PASS — 4647 gated test(s) passed, 0 failures, 0 errors`** (compose tests within the gate confirm deploy-all output unchanged). 2 allowlist known-failures pre-existing (OPEN #10360).
- **AC3 (installer-files.txt) — PASS.** `git diff --name-status main...branch` shows **no files added** (git_ops.py / harness.py / l4_file_watcher.py all pre-existing) → installer-files.txt correctly unchanged.
- **No CQ gate** — code-only (scripts + test), no LLM-consumed instruction change.

## Disposition
- **VERDICT: PASS → pending-ship (DM).** Zero gaps.
- Merge **deferred to DM** — PR carries "Closes #12906" (QA-merge would auto-close + skip DM).
- Counter NOT bumped (DM owns).
- **Scope boundary respected**: Phase 1 = pull-first guard only. The non-interruption/deploy-signal layer is Phase 2 (#12895) — correctly NOT in this task.
