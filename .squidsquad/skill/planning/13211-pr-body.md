## #13211 — hoist freshen serialization into `git_ops.ensure_main_and_pull`

(verifier-filed; the last deploy-path-fragility cluster sibling, completing #13212/#13215/#13211.)

### Root cause
`#13197` added a watcher-local `_FRESHEN_LOCK` in `l4_file_watcher._default_ensure_fresh_source` to single-flight per-role-class freshen bursts (separate Timer threads colliding on `.git/index.lock`). But the **post-merge deploy-all** path (`harness.py:4221`) calls `git_ops.ensure_main_and_pull` **directly**, outside that watcher lock — so a watcher burst could still race the deploy on the same clone's `.git/index.lock`.

### Fix
**Relocate** the serialization into `git_ops` itself: a module-level `_ENSURE_MAIN_LOCK` wraps `ensure_main_and_pull`'s body (inside the existing `try`, so the "Never raises" contract holds). Now **every in-process caller** — the watcher freshen *and* the deploy path — shares one lock. The redundant watcher-local `_FRESHEN_LOCK` is removed.

- **Non-reentrant Lock is safe:** `ensure_main_and_pull` never re-enters itself (it calls `_run`/`_run_list`/`pull` only; `pull` never calls back).
- **Threading-scoped (correct):** the racing callers are threads in the one harness process; the CLI caller is a separate process, not part of that race.

### Review (Sonnet; DeepSeek degenerate all session → auto-fallback)
- **NO_BLOCKING_FINDINGS.** Verified: no reentrancy/deadlock (flat call tree), complete coverage (both callers acquire the same `sys.modules`-shared lock instance), `_FRESHEN_LOCK` fully removed (threading still used by `_Debouncer`), `with`-inside-`try` releases on every path, tests prove serialization deterministically.
- **LOW (follow-up, not folded):** the git subprocesses inside the lock have no `timeout=`, so a hung git starves both callers (was: just the watcher) — a **pre-existing** gap whose scope is slightly widened. Hardening (`timeout=` on the fleet-wide `_run` helpers, or a watchdog) is a separate slice; noted on the issue for triage.

### Verification
- + git_ops tests: 11-thread barrier-timeout serialization proof, contract-preserved, pull-failure-still-reported, lock-is-a-Lock.
- + l4 tests rewritten to validate the **relocated** lock (mock the git layer so the real `ensure_main_and_pull` lock runs) + a new test proving **watcher AND deploy paths share the lock** + assert `_FRESHEN_LOCK` retired.
- Full static gate: **4975 passed, 0 failures, 0 errors**.
- No CQ (deterministic). No manifest (no new files).
