# QA-RESULTS-13197 — l4_file_watcher freshen-source pull-failed storm (serialize freshen)

**Verifier**: qa
**Date**: 2026-06-21 20:02
**Verdict**: PASS — zero gaps. Status → Pending Ship.
**Change under test**: PR #13205, branch `squidsquad/task/13197` (l4_file_watcher.py + tests).

## AC walk (implicit from issue body + hypotheses)

| AC | Result |
|----|--------|
| AC-1 burst of role-class recomposes no longer storms pull-failed | PASS |
| AC-2 RCA identifies the real root cause (concurrency, not dirty-tree) | PASS |
| AC-3 regression reproduces the storm pre-fix + guards reintroduction | PASS |

## Test Cases (isolated worktree of the branch)

### TC-1 (AC-2 premise) — debounce fires per-key on separate Timer threads — **PASS**
`_Debouncer` keeps a per-key `_timers` map and starts a separate `threading.Timer` per key
(l4_file_watcher.py:380/391/395). A burst of N role-class keys → N concurrent callback threads →
N concurrent `_default_ensure_fresh_source` → concurrent `git pull` on the SAME clone. Premise of
the RCA independently confirmed against the code (not taken from the worker's claim).

### TC-2 (AC-1, AC-3) — freshen serialized; storm reproduced pre-fix — **PASS**
- Branch: `test_concurrent_freshens_are_serialized` PASS — 11 concurrent freshen calls observe max
  in-flight git op == 1 (`_FRESHEN_LOCK` single-flights it; first does the real pull, rest are no-ops).
  `test_freshen_lock_exists` PASS.
- **Pre-fix proof**: same test against origin/main (no `_FRESHEN_LOCK`) FAILS:
  `"git freshen ran 11-way concurrent ... assert 11 == 1"` — exactly the 11-way concurrency behind the
  observed 11x compose-failed/pull-failed burst.

### TC-3 (AC-2 refutation) — dirty-tree hypothesis correctly refuted — **PASS**
The clone was 0 ahead / 0 behind. An up-to-date `git pull` is a no-op that does not modify the working
tree, so a dirty tree does not block it — the only 0/0 failure mode is a transient git error
(`.git/index.lock` contention from concurrent invocations). So hypothesis #2 (dirty-tree blocks freshen)
is correctly refuted by the 0/0 fact, and the concurrency fix alone is sufficient. (The gitignore-transient
-artifacts idea remains an optional separate hygiene improvement, not required to close this defect.)

### TC-4 (no regression) — full gate — **PASS**
`tests/run_tests.py`: `4907 passed, 17 skipped, 12 subtests passed`; static-gate verdict
`PASS — 4936 gated test(s) passed (0 failures, 0 errors)`.

## Coverage matrix
- AC-1 → TC-2 ; AC-2 → TC-1, TC-3 ; AC-3 → TC-2 ; guard → TC-4 ✓

## Notes
Deterministic harness code — no CQ. Tests ship under `tests/` (preserved). No HUMAN-REQUIRED TCs.
Sibling of the deploy/recompose fragility class (#13158/#13030/#13036/#12906); this is the freshen-path
concurrency instance. Directly relevant to this clone's own restart-required/recompose-propagation
situation — serialized freshen should make those bursts succeed.
