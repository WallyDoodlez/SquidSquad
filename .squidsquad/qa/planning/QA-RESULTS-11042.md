# QA-RESULTS-11042 — pytest suite red (partial fix on PR #11048)

**Verified at**: 2026-06-04 cycle 910
**PR**: #11048 (squidsquad/skill/11042-pytest-suite-stale-refs @ 80246d56c)
**Scope**: 5 clusters skill committed to fix here. Remaining clusters tracked as #11044, #11045, #11046, #11047 (independently verified).

## AC walk (Expected-section)

The issue body has no explicit AC block; the "Expected" section is the contract. Walked against the in-scope clusters only.

- **AC-1 (in-scope clusters pass pytest)** — PASS
  - `python -m pytest tests/test_installer_wiring.py tests/test_feat_6126_harness_merge.py tests/test_feat_3663_pr_conflict_check.py tests/test_feat_9747_role_placeholder_elimination_live.py tests/test_git_ops.py tests/test_compose.py tests/test_manifest.py -q` → **270 passed in 4.29s**.
- **AC-2 (installer-files.txt only lists existing paths)** — PASS
  - `test_installer_wiring.py::TestInstallerFileManifest::test_every_listed_file_exists_on_disk` PASS.
  - Independent parse: 234 non-comment entries, 0 missing on disk.
- **AC-3 (running the suite does not mutate `.squidsquad/` or `references/`)** — PASS for this verification run
  - `git status --short` empty after the 270-test run. Note: full-suite mutation (`config.md` pollution from test_feat_2495) is the explicit subject of follow-up #11044 and remains out of scope for #11042.

## Cluster-by-cluster

| # | Cluster | Evidence | Result |
|---|---------|----------|--------|
| 1 | installer-files.txt prune (39 stale entries removed; 258→219 header count) | `test_every_listed_file_exists_on_disk` PASS; independent parse 234 entries / 0 missing | PASS |
| 2 | TestEventReactionsTable removed (3 cases, event-reactions.md was pruned by 811a4060) | `test_feat_6126_harness_merge.py` collects/passes without the deleted class | PASS |
| 3 | test_feat_3663_pr_conflict_check tokens migrated rebase→merge | 4 assertions updated to `git merge origin/`, `git push origin`, `git merge --abort`, `squidsquad/ + never-touch-other-agents`; suite PASS | PASS |
| 4 | test_feat_9747 dev/qa → worker/verifier parametrize | TC-1 parametrize list updated; 2 previously-missing-file params now resolve; suite PASS | PASS |
| 5 | .squidsquad/.backlog-cache git rm --cached | `test_git_ops.py::TestGitignoreVolatileFiles::{test_gitignore_covers_volatile_files,test_volatile_files_not_tracked}` PASS | PASS |

## Decision

**Verdict**: PASS for the 5 in-scope clusters. Transition `pending-test → pending-ship`.

The four follow-ups (#11044 config.md pollution + test_feat_2495, #11045 test_feat_9588 internal-pinning, #11046 test_event_mode_fragments missing manifests, #11047 test_feat_9415 stale event_id refs) are appropriately scoped out and remain tracked separately. PR #11048 is honest about its partial-fix scope.

PR ready-for-review action taken alongside the transition.

---

## Round 2 — Post-merge re-verification (cycle 913, 2026-06-05)

**Trigger**: DM routed back at 02:13 UTC for merge conflict on `.squidsquad/.backlog-cache` (deleted by PR via `git rm --cached`; modified on main by PM cycle). Skill merged `origin/main` into the PR branch, kept the deletion (gitignored per TestGitignoreVolatileFiles), pushed merge commit `e4feee9bd`, re-transitioned to pending-test.

**Re-ran the same 7-suite sweep at `e4feee9bd`**:
- `python -m pytest tests/test_installer_wiring.py tests/test_feat_6126_harness_merge.py tests/test_feat_3663_pr_conflict_check.py tests/test_feat_9747_role_placeholder_elimination_live.py tests/test_git_ops.py tests/test_compose.py tests/test_manifest.py -q` → **270 passed in 3.33s** (identical to round 1).
- `installer-files.txt`: 234 non-comment entries, 0 missing on disk (unchanged from round 1).
- `git status --short` clean after the run — no `.squidsquad/`/`references/` mutation.

All five clusters carry through the merge intact. **Verdict unchanged: PASS. Transition `pending-test → pending-ship`.**

---

## Round 3 — Post-#11065/#11050 re-merge (cycle 916, 2026-06-05)

**Trigger**: After #11065 (PR #11067, commit `1dd58709c`) and #11050 (PR #11064, commit `1deeac641`) landed on main, skill re-merged main into PR #11048 at HEAD `5de4b7c57` — zero conflicts (the structural fix in #11065 eliminated the spiral surface). Re-transitioned to pending-test.

**Re-ran the same 7-suite sweep at `5de4b7c57`**:
- 7-suite sweep → **271 passed in 3.29s** (+1 vs R1/R2's 270 — the new `test_backlog_cache_not_in_allowlist` from #11065 picks up here, as skill predicted).
- `installer-files.txt`: 234 entries, 0 missing.
- No `.squidsquad/`/`references/` mutation observed during the run.

All five original clusters still carry through, plus the #11065 regression test lives alongside them. **Verdict unchanged: PASS. Transition `pending-test → pending-ship`.**

