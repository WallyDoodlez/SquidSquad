# QA Results — #9932 (shared_fs.write_secret atomic write)

**Verifier**: qa-lead
**Timestamp**: 2026-05-22 13:01 cycle 734
**PR**: #9935 (branch `squidsquad/task/9932`)
**Verdict**: PASS — zero gaps. Status → Pending Ship.

## Acceptance Criteria

| # | AC | Evidence | Result |
|---|----|----------|--------|
| 1 | `Path.write_text` direct call removed; `mkstemp` + `os.replace` pattern used | Diff at shared_fs.py:156-176 — `tempfile.mkstemp(prefix=".secrets-", suffix=".tmp", dir=secrets_file.parent)` creates a tmp in the same directory; `os.fdopen(tmp_fd, "w", encoding="utf-8")` writes content; `os.replace(tmp_path, secrets_file)` atomic-swaps. `secrets_file.write_text(...)` is gone. Locked by test `test_uses_atomic_pattern_in_source`. | PASS |
| 2 | `_restrict_permissions` runs on the tmp file BEFORE rename (closes ACL window) | `_restrict_permissions(tmp_path)` at shared_fs.py:163, immediately before `os.replace`. Matches the issue body's "chmod the `.tmp` BEFORE rename" recommendation. | PASS |
| 3 | Crash mid-write leaves original file unchanged | `try/except Exception` wraps mkstemp-through-replace; on any error, `tmp_path.unlink()` (best-effort) and re-raise. The original `secrets_file` is untouched throughout because nothing writes to it directly. Test `test_secrets_file_survives_write_failure` patches `os.fdopen` to raise OSError after mkstemp succeeded, asserts original is byte-for-byte unchanged. | PASS |
| 4 | No `.tmp` leak on failure | Same try/except cleanup path. Behavioral E2E confirmed: simulated disk-full → original intact + zero `.secrets-*.tmp` files left in directory. | PASS |
| 5 | Tests added covering happy-path + crash invariant | `TestWriteSecretAtomic9932` (4 tests): `test_basic_round_trip`, `test_existing_secrets_preserved_on_update`, `test_secrets_file_survives_write_failure` (core invariant), `test_uses_atomic_pattern_in_source` (source-level lock against regression). | PASS |

## Test runs

- Targeted: `pytest tests/test_shared_fs.py -k 9932` → **4 passed in 0.13 s**.
- Full module: `pytest tests/test_shared_fs.py` → **26 passed in 0.42 s** (22 baseline + 4 new).

## Behavioral end-to-end check

Simulated a real `OSError("simulated disk full")` raised from `os.fdopen` AFTER mkstemp succeeded. Result:

- Original secrets file: 46 bytes, **byte-for-byte unchanged** after the failed `write_secret` call.
- `.secrets-*.tmp` glob: 0 matches — no leak.
- `write_secret` re-raised the OSError as expected (caller can decide whether to retry).

This is the core #9932 invariant — the pre-fix `Path.write_text` would have truncated the file before writing, so any failure mid-write would have left the file empty. Confirmed eliminated.

## Notes

- PR body explicitly skipped DS pre-push review for this PR: ~30-line diff using a well-established stdlib pattern (`mkstemp` + `os.replace`), no novel logic. I agree this is the right call — the change is small and matches the standard atomic-write idiom (same pattern used by `status_bar` in #9901 and many other places in stdlib code). The `test_uses_atomic_pattern_in_source` test gives source-level regression protection without needing a DS audit.
- `mergeable: MERGEABLE, mergeStateStatus: CLEAN, isDraft: false` per `gh pr view`.
