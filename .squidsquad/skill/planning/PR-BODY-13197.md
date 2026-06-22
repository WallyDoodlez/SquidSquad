Closes #13197.

## Problem
The harness L4 file-watcher emitted **11x `compose-failed`-to-pm** in a ~2s burst (`reason=freshen-source-failed`, `stderr="recompose for '<X>' aborted: pull-failed"`), one per role-class. The harness clone was **0-ahead/0-behind** origin/main, so a plain pull should have been an "Already up to date" no-op — yet all 11 failed.

## RCA (facts, confirmed)
Each per-role-class debounce callback fires `make_change_callback._on_change` → `_default_ensure_fresh_source` → `git_ops.ensure_main_and_pull` on its **own `threading.Timer` thread** (`_Debouncer._fire` runs the callback per-key, no cross-key serialization). A burst touching N role-classes therefore runs **N concurrent `git pull`** against the **same** harness clone → they collide on `.git/index.lock` → most return `pull-failed`. The all-fail-at-once pattern is lock contention, **not** staleness:
- **Divergence (#13158) ruled out**: clone was 0/0.
- **Dirty-tree ruled out**: `ensure_main_and_pull` skips `checkout main` when already on main; a 0/0 `git pull` is "Already up to date" even on a dirty tree.

The `_freshen_or_abort` docstring's "later pulls are fast already-up-to-date no-ops" assumption is only true *serially* — concurrent pulls collide before they can no-op.

## Fix
Module-level **`_FRESHEN_LOCK = threading.Lock()`** held around the `git_ops.ensure_main_and_pull` call in `_default_ensure_fresh_source`, so concurrent burst freshens **serialize** instead of colliding: the first does the real pull, the rest run as the fast no-ops the design assumed. Scoped to this process's watcher Timer threads (the collision source) — a `threading.Lock` is the right primitive.

## Tests
+2 in `TestFreshenSerialized13197`: lock-exists, and an **11-thread concurrency test** using a `threading.Barrier(N)` rendezvous so it deterministically exposes a missing lock (without the lock all N reach the barrier → max-in-flight==N; with it the barrier times out/breaks → max==1). File: 42 passed.

## Review (step:cycle/ds-review)
DeepSeek 402 → **Sonnet fallback**. **NO_BLOCKING_FINDINGS**; 1 MED + 4 LOW. MED + the test-flakiness LOW addressed; rest dispositioned no-change. Artifact: `.squidsquad/skill/planning/DS-REVIEW-13197.md` (on main).

## Known residual (documented, NOT silently dropped — review MED-1)
The post-merge deploy path (`harness.py`) calls `git_ops.ensure_main_and_pull("harness")` **directly**, outside `_FRESHEN_LOCK` — so a watcher burst concurrent with a post-merge deploy could still race on `.git/index.lock`. This is **out of scope for #13197** (watcher-burst-only); the comprehensive fix is to move the lock into `git_ops.ensure_main_and_pull` itself (covers all callers, higher blast radius — separate slice). Mitigant: the deploy path already serializes against other deploys via `harness._deploy_lock`; only the rare watcher-vs-deploy overlap remains. Flagged here so it isn't re-filed as a fresh mystery.

## Scope
Deterministic harness code → no CQ. No new/renamed files → no manifest update. Sibling fragility class: #13158 (deploy-pull divergence, shipped), #13030, #13036, #12906. Full static gate: see below.
