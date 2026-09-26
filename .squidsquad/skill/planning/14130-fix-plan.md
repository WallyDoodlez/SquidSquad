# Fix plan -- #14130

_Lineage file (VAULT-ARCH 9.3): the direction a reviewer judges before the
diff. Keep each section to a few lines._

## Root cause

`tests/test_12825_harness_restart.py`'s launcher stub did its own count.txt I/O
with no guard. Under full static-gate load a transient failure there, such as
a Windows sharing violation from AV or an indexer on the freshly written file,
made the stub exit 1 without incrementing. The launcher correctly counts that
as a crash, so the guard tripped after 3 launches with count.txt still "1".
That matches the observed `'1' != '3'` with launcher exit 1. It did not
reproduce in 8 parallel isolated runs; it only showed under the 6351-test gate.
The launcher itself (`.squidsquad/start.ps1` Invoke-Supervised) behaved
correctly, so it is not changed.

## Intended direction

This is a test-only change. A shared `_LAUNCH_STUB` for both the .sh and .ps1
classes retries its file I/O (50 x 0.1s). If a failure survives the retries, it
exits 97 and appends the exception to stub-errors.txt, so a stub self-failure
can never pass for a scripted exit code. The crash-loop tests pin
`SQUIDSQUAD_HARNESS_CRASH_WINDOW=3600` (the issue's wall-clock suggestion),
assert that no stub errors occurred, and include launcher stdout/stderr and the
stub errors in every assertion message, so any recurrence names its cause.
Mechanism verified: with count.txt made unwritable, the launcher reports
`code 97` and stub-errors.txt holds the `PermissionError`.

## Impact

Only the two launcher test classes change. No production code changes.

## Vault context consumed

- [[learning-single-static-gate-red-may-be-flake-rerun-before-reject]] -- this flake is that class; the fix makes a recurrence self-diagnosing instead of needing a rerun to tell it apart

## Applicable rules

- None matched (searched: flake, launcher, static-gate, windows, test)
