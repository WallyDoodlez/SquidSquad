# Code Review — #13197 (serialize l4_file_watcher freshen — index.lock collision)

**Reviewer**: DeepSeek 402 → **Sonnet fallback** (per [[feedback_model_router_auto_fallback]]).
**Scope**: `references/scripts/l4_file_watcher.py` (`_FRESHEN_LOCK` + `_default_ensure_fresh_source`) + `tests/test_l4_file_watcher_e3.py` (`TestFreshenSerialized13197`).

## Verdict: NO_BLOCKING_FINDINGS

RCA confirmed: per-role-class debounce callbacks fire on independent `threading.Timer` threads → N concurrent `ensure_main_and_pull` on the shared clone → `.git/index.lock` collision → pull-failed storm. `_FRESHEN_LOCK` serializes the git freshen; first call pulls, rest are fast no-ops. The 0/0-but-dirty state rules out divergence (#13158) and dirty-tree.

## Findings & disposition

1. **MED — watcher-vs-deploy residual race** — the post-merge deploy path (`harness.py`) calls `git_ops.ensure_main_and_pull("harness")` **directly**, outside `_FRESHEN_LOCK`. A watcher burst (holding `_FRESHEN_LOCK`) concurrent with a post-merge deploy can still race on `.git/index.lock`. → **OUT OF SCOPE / DOCUMENTED** (not silently dropped): #13197 is watcher-burst-only (N Timer threads, one process). The comprehensive fix is to move the lock into `git_ops.ensure_main_and_pull` itself (covers all callers) — a cross-module higher-blast-radius change. Documented here + in the #13197 ship comment with the fix direction so it is not re-filed as a fresh mystery. (Mitigant: the deploy path already serializes against other deploys via `harness._deploy_lock`; only watcher-vs-deploy remains, a rare overlap.)

2. **LOW — lock held across the `git pull` subprocess** — a slow/network-stalled pull blocks the other queued callbacks for its duration. → **NO CHANGE**: pre-existing (`git_ops.pull` has no timeout today), and acceptable given the serialize-not-dedup goal; daemon Timer threads don't block process exit.

3. **LOW — concurrency test could pass vacuously on a loaded runner** (0.02s sleep window). → **FIXED**: replaced the sleep-window with a `threading.Barrier(N)` rendezvous — a missing lock now deterministically yields max==N; with the lock the barrier times out/breaks (serialized → max==1).

4. **LOW — `_FRESHEN_LOCK` bypassable via `ensure_fresh_source=` injection** — tests bypass it. → **NO CHANGE**: intended design (lock is production-only; production always passes `ensure_fresh_source=None` → `_default_ensure_fresh_source`). Correct placement for #13197's scope.

5. **LOW — serialization yields 11 sequential no-ops, not 1 pull** — → **NO CHANGE**: accepted by the issue ("fast no-ops"); no staleness risk (each call re-reads repo state). True single-flight dedup is a separate optimization.

## Gate
Full static gate exit 0 (see PR). Targeted `test_l4_file_watcher_e3`: 42 passed.
