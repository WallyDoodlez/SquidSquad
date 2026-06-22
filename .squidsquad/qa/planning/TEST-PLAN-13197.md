# TEST-PLAN-13197 — l4_file_watcher freshen-source pull-failed storm on 0/0-but-dirty clone

**Source**: GitHub issue #13197 (Observed/Impact/Hypotheses — no explicit AC block).
**Derived without reading the diff.**

Deterministic harness code (`l4_file_watcher._default_ensure_fresh_source`). The report gives two
hypotheses (concurrency/index.lock vs dirty-tree) for skill to confirm/refute. Implicit ACs:

- **AC-1** — A burst of per-role-class recomposes on a 0/0 harness clone no longer produces an
  N-way `pull-failed`/compose-failed storm (the freshen pulls must not collide).
- **AC-2** — RCA correctly identifies the root cause (the fix must address the actual mechanism, not
  a refuted hypothesis).
- **AC-3** — Regression test that reproduces the storm pre-fix and would catch reintroduction.

## Test Cases

### TC-1 (AC-2 premise) — debounce fires per-key on separate Timer threads
- **Expected**: `_Debouncer` keeps a per-key `_timers` map and starts a separate `threading.Timer`
  per key → a burst of N keys runs N callbacks concurrently against the same clone (the collision source).
- **Verification**: read `l4_file_watcher.py` `_Debouncer` (per-key `_timers`, `threading.Timer(...).start()`).

### TC-2 (AC-1, AC-3) — freshen is serialized; concurrency storm reproduced pre-fix
- **Expected**: with the fix, 11 concurrent freshen calls observe max in-flight git op == 1 (serialized);
  pre-fix (no `_FRESHEN_LOCK`) the same test observes 11-way concurrency (the regression).
- **Verification**: pytest `TestFreshenSerialized13197::test_concurrent_freshens_are_serialized` (branch:
  pass; origin/main: fails "11 == 1"), `test_freshen_lock_exists`.

### TC-3 (AC-2 refutation) — dirty-tree hypothesis is not the cause
- **Expected**: a 0/0 (up-to-date) `git pull` is a no-op that does not touch the working tree, so a
  dirty tree does not block it — the only 0/0 failure mode is a transient git error (index.lock from
  concurrent invocations). So hypothesis #2 is correctly refuted and the concurrency fix is sufficient.
- **Verification**: reasoning from the 0/0 fact in the issue + the failing pre-fix concurrency test.

### TC-4 (no regression) — full gate green
- **Expected**: `tests/test_l4_file_watcher_e3.py` green; full `tests/run_tests.py` green.

## Coverage matrix
- AC-1 → TC-2 ; AC-2 → TC-1, TC-3 ; AC-3 → TC-2 ; guard → TC-4

## Comprehension Questions
N/A — deterministic harness code, not LLM-consumed instruction. No CQ spec.
