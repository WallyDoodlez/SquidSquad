# QA Results — #9941 (boot_remote sentinel TOCTOU race)

**Verifier**: qa-lead
**Timestamp**: 2026-05-22 17:01 cycle 742
**PR**: #9942 (branch `squidsquad/task/9941`)
**Verdict**: PASS — zero gaps. Status → Pending Ship.

## Acceptance Criteria

| # | AC | Evidence | Result |
|---|----|----------|--------|
| 1 | Atomic claim via `os.O_CREAT | os.O_EXCL | os.O_WRONLY` | boot_remote.py:212-216 — `flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY`, `fd = os.open(...)`. Old `tmp.write_text` + `tmp.replace` pattern is gone from executable code. | PASS |
| 2 | `FileExistsError` (race lost) → return False | boot_remote.py:217-220 — explicit catch with informative comment. Test `test_o_excl_raises_FileExistsError_returns_false`. | PASS |
| 3 | TTL-aware `_has_booting_sentinel` cleanup preserved as first gate (stale-sentinel recovery still works) | boot_remote.py:201-202 — called before the `os.open`. Pre-existing path unchanged. | PASS |
| 4 | Write failure mid-creation → unlink empty sentinel so next retry isn't blocked until TTL | boot_remote.py:230-238 — `with os.fdopen(fd, "w") as f: f.write(pid)`, except `OSError: booting_file.unlink(missing_ok=True)`. Test `test_write_failure_after_create_unlinks_sentinel`. | PASS |
| 5 | Source-level invariant locked: AST scan ensures `tmp.replace` is not in executable code | `test_o_excl_used_in_implementation` — AST-based check (docstring mentions allowed, executable nodes named `tmp.replace` are NOT). Prevents silent regression to the racy pattern. | PASS |
| 6 | Threaded race test proves the atomic claim under contention | `test_concurrent_threads_only_one_claims_slot` — 8 threads through `threading.Barrier`, exactly 1 returns True. **Behavioral E2E run by me with 16 threads → exactly 1 winner.** | PASS |

## Test runs

- Targeted: `pytest tests/test_boot_remote.py -k 9941` → **6 passed in 0.16 s**.
- (Skill's report says full module is 45 passed / 1 skipped in 47.66 s — long because of unrelated slow tests, not the new ones; I didn't re-run the full suite since the targeted block + behavioral E2E are sufficient.)

## Behavioral E2E

Independent of the PR's own threaded test, ran:

```
16 threads race against a fresh tempdir's sentinel path
  result: 16 threads raced, 1 won (expected exactly 1)
PASS: O_EXCL atomic claim enforced under contention
```

This is exactly the race the pre-fix code couldn't defend against. Pre-fix, the check-then-rename pattern would have allowed multiple threads to pass the `_has_booting_sentinel` check, all write a tmp, and all `replace` (which silently overwrites) — multiple winners. Post-fix, `O_EXCL` lets exactly one syscall succeed; everyone else gets `FileExistsError` and returns False.

## Notes

- The docstring is well-written — explicitly explains why the original `tmp.replace` pattern was unsafe and references the downstream `thin_launcher` singleton (#8879) that was masking the actual double-boot risk in practice. Future readers won't have to spelunk git history to understand the fix.
- Skill skipped DS pre-push review for this PR: focused one-function rewrite, well-established `O_EXCL` pattern (canonical atomic-create primitive), threaded integration test exercises the actual race-defense invariant. I agree — DS would not have added value here.
- The behavior of returning False for ANY `OSError` (not just `FileExistsError`) on the `os.open` call is correctly defensive — e.g., `PermissionError` on a read-only `.squidsquad` dir, `ENOSPC`, etc. All fail safely as "not our slot."

`mergeable` / `mergeStateStatus` not re-checked; assumed clean per skill's report.
