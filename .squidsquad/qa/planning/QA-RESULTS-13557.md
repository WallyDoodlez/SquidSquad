# QA-RESULTS-13557

**Verdict: PASS -> Pending Ship.**

Direct-to-main fix (commit 1482437da, no PR — `.claude/` paths correctly cannot ride a PR per #13554 scope guard).

## Checks (all independently derived from the issue body, verified live)

- **TC-1 (untrack)** — PASS. `git ls-tree HEAD .claude/` shows only `.claude/settings.json`; all 4 stale worktree gitlinks (a6c409b5, a78aff93, a88a4be2, a98f9146, aa96d365 — 4 siblings beyond the originally-filed one) removed from the index.
- **TC-2 (no status noise)** — PASS. `git status --short` clean for the class.
- **TC-3 (recurrence prevention — the issue's own explicit ask)** — PASS. Live probe: created a file under `.claude/worktrees/`, confirmed `git status` shows nothing and `git check-ignore -v` matches `.gitignore:70:.claude/worktrees/`. This closes the recurrence vector via the .gitignore mechanism alone (a broad `git add -A` will never pick these up again) — sufficient per the issue's own "any one closes it" framing, independent of whether the #4829 static-gate list is widened.
- **TC-4 (safety — no resurrection via #13556's restore guard)** — PASS. `TestRestoreMergeDroppedState13556::test_blob_sizes_excludes_gitlinks` passes; its own docstring documents this was an observed-live bug (guard previously resurrected a deliberately-removed worktree gitlink) now fixed. Confirms the skill's stated claim ("guard-safe: #13556's restore guard excludes gitlinks").
- **TC-5 (static-gate coverage gap, flagged in the issue but non-blocking)** — the #4829 `TestGitignoreVolatileFiles` list does not cover `.claude/worktrees/*` (different artifact category — gitlinks vs tracked-volatile-files). Since TC-3 already closes the actual recurrence risk, this is non-blocking. QA added a small dedicated regression test to close the loop the issue explicitly asked about checking: `tests/test_feat_13557_worktree_gitlinks_untracked_qa.py` (3/3 passing, promoted directly — no code changes needed a new test, this is QA value-add for the exact concern the issue raised).

## Test coverage
No new production code — data-only fix (`.gitignore` + `git rm --cached`-equivalent). Promoted regression test added by QA (see TC-5).

## Full static gate (fresh, fully-synced origin/main, post this session's #13574-reject + #13583 em-dash fix merge)
PASS — 5524/5524 gated tests, 0 failures, 0 errors. Fully green (both the #13574 staleness-gate regression and the inject-permissions.ps1 em-dash residual are resolved on this main tip — the former by this verdict keeping #13574 off main, the latter by a separately-merged fix).

No LLM-consumed instructions touched by this fix — no comprehension gate required.
