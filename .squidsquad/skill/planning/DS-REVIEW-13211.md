# Code Review — #13211 (relocate freshen lock into git_ops.ensure_main_and_pull)

Reviewer: Sonnet subagent (DeepSeek degenerate all session → Sonnet per auto-fallback). Fleet-critical concurrency lens (#13197/#13158/#13167/#12906 history).

## Verdict: NO_BLOCKING_FINDINGS

### Verified
1. **No reentrancy/deadlock**: traced ensure_main_and_pull → _run/_run_list/pull → (pull → _run/_stash_top_ref/_safe_stash_pop/_emit). Flat call tree, no cycle; pull() never calls ensure_main_and_pull. Plain non-reentrant Lock is safe.
2. **Lock scope** held across the checkout+pull subprocesses = the intended serialization (identical duration profile to the old _FRESHEN_LOCK; just covers more callers).
3. **Coverage complete**: both racing in-process callers (watcher freshen l4_file_watcher:237 + post-merge deploy harness.py:4221) acquire the SAME module-level lock instance (sys.modules single-object guarantee; no importlib.reload anywhere). The deploy path — previously OUTSIDE the watcher lock — is now serialized with the watcher.
4. **Cross-process CLI** correctly out of scope (threading lock is process-local; the race is in-process harness threads; CLI is a standalone tool).
5. **_FRESHEN_LOCK** fully removed; threading still imported in l4_file_watcher (used by _Debouncer Timer/_lock). Regression-guarded by test_lock_relocated_to_git_ops_13211.
6. **"Never raises" contract sound**: `with` inside `try`; `__exit__` releases on every path incl. returns and exceptions.
7. **Tests prove serialization** (not trivially pass): barrier-timeout technique is deterministic in the fixed direction — without the lock all N rendezvous (max==N); with it max==1. The cross-path test (watcher + deploy concurrently) validates the exact #13211 regression.

### LOW (follow-up, NOT folded)
The git subprocesses inside _ENSURE_MAIN_LOCK have no `timeout=`, so a hung git starves both callers (was: just the watcher). PRE-EXISTING gap, scope slightly widened by unification. Hardening (`timeout=` on _run/_run_list, or a watchdog) is a separate concern touching the fleet-wide _run helpers — noted on #13211 for triage, not folded into this lock relocation.
