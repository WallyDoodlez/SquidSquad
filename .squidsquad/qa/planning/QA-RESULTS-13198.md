# QA-RESULTS-13198 — fleet-wide cp1252 stdout crash class

**Verifier**: qa
**Date**: 2026-06-21 20:30
**Verdict**: FAIL (zero-gap) — AC-4 ASCII sweep incomplete. Status → In Progress (back to skill).
**Change under test**: PR #13214, branch `squidsquad/task/13198`.

## AC walk

| AC | Result |
|----|--------|
| AC-1 shared canonical helper | PASS |
| AC-2 each agent-facing CLI calls it at main() | PASS |
| AC-3 tracker.py refactored to shared helper (no dup) | PASS |
| **AC-4 ASCII sweep of decorative non-ASCII in stdout** | **FAIL** |
| AC-5 new file in installer manifest | PASS |
| AC-6 tests | PASS |

## What's correct (so the fix needs only AC-4 completed)
- **AC-1/TC-1**: `references/scripts/cli_stdio.py` `harden_stdio()` — reconfigure `errors="backslashreplace"`,
  best-effort (guards AttributeError/ValueError/OSError), CLI-only, idempotent. Mirrors #13185.
- **AC-2/AC-3/TC-2**: all 9 agent-facing CLIs (add_role, boot_remote, compose, config, migrate_state_branch,
  model_router, scan_index, subloop_driver) call `harden_stdio()` at `main()` top; tracker.py refactored
  to delegate to the shared helper (no duplicate impl). 15/15 in `test_cli_stdio_13198.py` PASS
  (parametrized fleet-wiring + delegation + module-exists).
- **AC-5/TC-4**: `installer-files.txt` updated (253→254) including `references/scripts/cli_stdio.py`.
- **TC-6 crash-net**: verified on a strict cp1252 stream — after `harden_stdio()`, `print("→ — •")`
  does NOT raise (backslash-escaped). The crash/false-failure/double-emit harm is eliminated.

## The gap (AC-4 / TC-3) — FAIL
The issue Direction explicitly scopes an "ASCII-replacement sweep of decorative non-ASCII (→, —, •, etc.)
in those scripts' stdout so the common output displays cleanly on every console." The sweep is INCOMPLETE
— 9 decorative chars remain in stdout/stderr print lines across 6 of the swept files (with the helper they
no longer crash, but on a cp1252 console they now render as `→` / `—` — the ugly output the sweep
is meant to prevent, including common success lines):

- `add_role.py:295` — `—` (stderr) ; `add_role.py:384` — `→` (stdout, "Fixing origin: ... → ...")
- `boot_remote.py:703` — `—` (stdout, the per-role status line — common output)
- `compose.py:987` — `—` ; `:1151` — `—` ; `:2244` — `—` (stderr)
- `migrate_state_branch.py:116` — `—` (stdout, "(dry run — no files moved)")
- `model_router.py:909` — `—` (stdout)
- `scan_index.py:444` — `→` (stdout, "Recorded decision: ... → ..." — common success line)

Secondary: no regression guard for the sweep — a test that greps the swept scripts for decorative
non-ASCII in stdout would have caught this (and would prevent reintroduction). Consider adding one
alongside the cleanup.

## Verdict
FAIL — back to In Progress. Complete the ASCII sweep (replace the 9 remaining `→`→`->`, `—`→`--`/`-`)
and ideally add a grep-guard test. The helper/wiring/refactor/manifest/tests are all correct and need
no rework.
