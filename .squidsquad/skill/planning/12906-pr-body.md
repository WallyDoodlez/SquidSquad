## #12906 — Phase 1 of #12895: harness recompose ensure-main + pull-first

Closes #12906.

### What
Every harness-side recompose/deploy path now ensures the clone is on `main` and pulls origin (merge, never rebase) **before** running `compose.py deploy*`. A behind-origin or feature-branch clone can no longer regenerate composed `CLAUDE.md`/`CLAUDE.linked.md` from stale source and push that revert fleet-wide (the #12895 root condition; observed 3× on 2026-06-19).

### How
- **`git_ops.ensure_main_and_pull(role)`** — new canonical guard. Ensures `main`, then merge-pulls. Returns `(ok, detail)`, never raises (blanket guard so the direct harness caller can trust `ok`).
- **`l4_file_watcher.py`** — both recompose batch entries (`_on_change` for the file-watch, `recompose_path` for the post-commit hook) freshen source **once** before composing, via an injectable `ensure_fresh_source=` (same pattern as `run_compose=`). In the watch path the guard runs **before** `registry_provider()` so a pulled-in `config.md ## Aliases` change is reflected. On failure the batch **aborts** (no compose against stale source) and surfaces a `compose-failed`-to-PM event so the halt is observable; agents keep last-known-good composed output.
- **`harness.py`** — the post-merge `compose.py deploy-all` path (the one that reverted during #12800's ship) now calls `ensure_main_and_pull("harness")` first; on failure it skips deploy-all and emits `compose-completed success:False` rather than composing from pre-merge source.

### Scope boundary
Phase 1 = pull-first guard only. The Phase 2 non-interruption layer (deploy-signal at the ack-cursor boundary → agent halts → harness deploy/restart) stays on #12895, pending PM's doc-first arch spec. Not built here.

### Tests
- AC1: guard runs before compose, exactly once per batch, and aborts (no compose, no events except the PM `compose-failed`) when the clone can't be freshened; behind/feature-branch clone switches to main then pulls; on-main skips checkout; pull-fail / checkout-fail / unexpected-exception all return `(False, …)`. Static-grep gate locks the post-merge deploy-all guard.
- AC2: `compose.py deploy-all` from current source produces zero composed drift (verified); existing l4/harness/git_ops suites green.
- AC3: no files added/removed under `references/` → `installer-files.txt` unchanged. (Filed #12907 separately for the pre-existing gap: all 9 `l4_*.py` scripts are absent from the manifest.)

DS review: 4 warnings, all resolved (`.squidsquad/skill/planning/DS-REVIEW-12906.md`).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
