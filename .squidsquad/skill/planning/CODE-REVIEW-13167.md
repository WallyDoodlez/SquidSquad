# CODE-REVIEW — #13167 (P0) git_ops stash-pop guard

**Reviewer:** Claude/Sonnet subagent (DeepSeek model_router unavailable — 402, fleet-wide; [[feedback_model_router_auto_fallback]]).
**Date:** 2026-06-21
**Scope:** references/scripts/git_ops.py (`_stash_top_ref` new; `pull()`, `_safe_checkout()` guards) + tests/test_git_ops.py.

## RCA (confirmed)
`git stash` is a no-op on a clean tree (exit 0, no entry). `pull()`/`_safe_checkout()` popped unconditionally → applied a pre-existing ancient stash → tree-wide `<<<<<<<` markers → config.py SyntaxError → compose pipeline down (16 compose-failed). 26 accumulated ancient stashes = fleet-wide latent landmine.

## Fix
`_stash_top_ref()` (refs/stash top SHA). Both sites capture pre-ref, stash, `stashed = (post != pre)`, pop only when `stashed`. Raw pull-fail pop → guarded `_safe_stash_pop`.

## Audit verdict: NO_BLOCKING_FINDINGS
- **Correctness SOUND**: a new stash always advances refs/stash to a new commit SHA (git content-addressed invariant) → no false-negative (own-stash leak) or false-positive (pop pre-existing) under any realistic path.
- **Edge cases all FAIL SAFE** (skip-pop/leak, never corruption): rev-parse fails post-stash → leak (safe); pre-existing+dirty → pops only OUR top entry; pull-fail branch guarded; `_safe_checkout` non-dirty failure → no-op stash → no pop.
- **All stash→pop sites guarded** (verified table: lines 230/245 inside `_safe_stash_pop`; 272/283/292 in pull; 712/719/725 in `_safe_checkout` — every `_safe_stash_pop` caller gated on `stashed`).
- **Test coverage thorough** (15 mapped scenarios incl. clean-tree-no-pop on both pull + _safe_checkout, pull-fail, conflict handling, `_stash_top_ref` both branches).

## LOW findings & dispositions
1. **LOW** comment at `_safe_checkout` implied dirty-only; stash path runs for any checkout failure → **FIXED** (tightened comment).
2. **LOW** optional missing test: rev-parse fails post-stash → leak. Safe failure, extremely unlikely trigger → **skipped** (not worth the test).
3. **LOW** `_safe_stash_pop` returns False for both conflict and non-conflict-failure; success-path log says "conflict" on an impossible race → **no action** (logically unreachable).

## Gates
160 git_ops tests green; full static gate PASS 4896/0/0. Deterministic code → no CQ; no new shipped file → no manifest.
