# CONTEXT-9926 — orphan_cleanup.py D3 loosened to per-role skip

**Issue**: #9926
**Phase**: 2 (Locked Decisions, post-DeepSeek review)
**Author**: pm-lead
**Date**: 2026-05-22
**Status**: planning → planned (after human approval of these locks)

> **AUTHORITATIVE SCOPE**: `.squidsquad/pm/planning/CONTEXT-9926.md`. Read this artifact in full before pickup. The bullets in the issue body are a summary; this planning artifact is the contract.

---

## Authoritative Scope Statement

#9926 fixes a steady-state-vs-turbulence gap in `references/scripts/orphan_cleanup.py`: the existing decision D3 (CONTEXT-9688.md) skips the ENTIRE sweep if ANY role's `.claude-pid` is missing or its cmd.exe is dead. This is correct under steady state but counter-productive during exactly the wedge/reboot episodes that *create* orphans — so orphans accumulate during outages even though the reaper is "running."

The fix loosens D3 from whole-sweep abort to per-role skip, with a backstop for the zero-healthy-roles case.

Evidence motivating this fix: during the 2026-05-22 harness wedge episode, 3 orphan `claude.exe` accumulated (PIDs 663084 from May 19, 2074300 from 08:47 reboot, 2074804 from 09:03 reboot) and were never reaped despite both invocation paths (`cycle_post.py` end + `boot_remote.py` start) firing repeatedly. PM had to kill them manually with `Stop-Process -Force`.

---

## Locked Decisions

### D1 — Path locked to Fix 1 only: per-role skip (LOCKED, human Option A, supersedes DS F2)

Loosen `orphan_cleanup.py` D3 so that when a specific role's `.claude-pid` is missing or its cmd.exe is dead, only THAT role is excluded from the protected-PID set — the sweep proceeds for all other roles.

**Fix 2 (periodic out-of-band reap in harness.py) is REJECTED** for this issue. Rationale: (a) it adds harness complexity for a marginal belt-and-braces gain; (b) it introduces the concurrency hazard called out by DS F4 (race with `boot_agent`'s inline sweep); (c) per-role skip addresses the root cause directly. Periodic reap may be revisited in a separate issue if v1 evidence shows the gap persists.

### D2 — Zero-healthy-roles backstop preserved (LOCKED, supersedes DS F5)

If `_resolve_protected_pids` returns ZERO healthy roles (because `.local-config` is unreadable, no roles are configured, or every role's cmd.exe is dead), the sweep MUST still abort entirely — same as today. The protected set being empty is qualitatively different from "one role is unhealthy": it removes ALL protection, and the original D3 rationale ("rather miss orphans than kill the wrong process") still holds in that case.

Implementation note: in `orphan_cleanup.sweep()`, check `len(protected_pids) == 0 and all_roles_unhealthy` BEFORE proceeding. Distinguish from `len(protected_pids) == 0 and roles_were_healthy_but_have_no_extra_claude_children` — the latter is a normal idle state and must continue to sweep (otherwise it'd be a regression).

### D3 — Existing tests are UPDATED, not preserved as-is (LOCKED, supersedes DS F1)

The existing assertion `test_d7_missing_claude_pid_skips_entire_sweep` at `tests/test_orphan_cleanup_9688.py` line 220–225 (and `test_stale_pid_with_dead_cmdexe_also_skips_sweep` at line 259) MUST be REWRITTEN to assert the new per-role-skip semantics:

- `test_d7_missing_claude_pid_skips_only_affected_role` — assert `result["skipped_roles"]` lists ONLY the missing role; orphans of other roles ARE killed.
- `test_stale_pid_with_dead_cmdexe_skips_only_affected_role` — same shape for the dead-cmd case.
- `test_no_roles_discoverable_skips_sweep` — RETAINED as-is per D2 backstop.

The original D3 assertion message ("missing .claude-pid for any role must abort the ENTIRE sweep") must be replaced with a new message that encodes the per-role semantics — DS F1 is correct that the message is normative.

CONTEXT-9688.md D3 entry MUST be updated in the same commit to note the supersession (or marked LOCKED-SUPERSEDED-BY-#9926).

### D4 — Single test strategy: unit tests with mocks (LOCKED, supersedes DS F6)

AC verification is via unit tests in `tests/test_orphan_cleanup_9688.py` using the existing mock pattern. No harness integration test is required for this issue (no periodic reap was selected). This makes every AC deterministic and runnable via `pytest tests/test_orphan_cleanup_9688.py`.

### D5 — Full file test coverage, not just D7 scenarios (LOCKED, supersedes DS F7)

After the change, ALL test functions in `tests/test_orphan_cleanup_9688.py` (currently 16, not 7) MUST pass — the file's npm-path-filter, POSIX no-op, JSONL log shape, CSV parser edges, and own-PID defense tests are equally important regression coverage and any change to D3 must preserve them.

---

## Acceptance Criteria (revised after DS review)

- **AC1** — `orphan_cleanup.py` is modified so that a stale `.claude-pid` (missing file OR dead cmd.exe) for one role does NOT abort the entire sweep. Other roles' protected PIDs are still computed and used; orphans whose parents are dead AND who are not in any role's protected set ARE killed.

- **AC2** — `orphan_cleanup.py` retains the zero-healthy-roles backstop per D2: if zero roles resolve to a healthy protected PID, the sweep aborts entirely (returns the same "skipped_run" shape as today).

- **AC3** — All test functions in `tests/test_orphan_cleanup_9688.py` pass. Specifically:
  - The D7 tests asserting whole-sweep abort on a single bad role are REWRITTEN to assert per-role skip semantics per D3.
  - `test_no_roles_discoverable_skips_sweep` is retained AS-IS (D2 backstop).
  - All other tests (npm-path-filter, POSIX no-op, JSONL log shape, CSV parser edges, own-PID defense) pass with no changes required.
  - Total green test count is unchanged or higher than the current 16.

- **AC4** — New unit test `test_partial_skip_kills_orphans_of_healthy_roles` covers the canonical scenario: 2 roles configured, role A has a stale `.claude-pid`, role B is healthy. An orphan claude.exe whose ParentProcessId matches neither A's nor B's `.claude-pid` is correctly classified as ORPHAN and killed. A claude.exe whose parent is role B's live cmd.exe is correctly classified PROTECTED and NOT killed.

- **AC5** — New unit test `test_partial_skip_logs_per_role_decision` asserts the JSONL diagnostics log at `.squidsquad/diagnostics/orphan-cleanup.jsonl` contains a `decision: "per-role-skip"` entry for the unhealthy role AND a normal `decision: "killed" / "protected"` entry for processes evaluated against healthy roles.

- **AC6** — `CONTEXT-9688.md` D3 entry is updated to reference the supersession (link to #9926) in the same PR. Either prepend `**SUPERSEDED-BY-#9926 (per-role skip)** —` to D3's content, or add a new line at the bottom of D3 noting the change.

- **AC7** — A live-system smoke test (manual, documented in `QA-RESULTS-9926.md`): with one role's cmd.exe deliberately killed (leaving a stale `.claude-pid`), `orphan_cleanup.py` is invoked and successfully reaps at least one orphan from another role. This validates the unit-test contract against real Win32 process semantics.

---

## Out of Scope

- Periodic out-of-band reap in `harness.py` — explicitly rejected per D1. Possible future issue.
- POSIX behavior changes — `orphan_cleanup.py` remains a near-no-op on POSIX per CONTEXT-9688.md D6.
- D3 rename / refactor beyond what is needed for the supersession note.
- Removing the JSONL diagnostics log or its format (D4 of CONTEXT-9688.md).

---

## DS Review Findings — Resolution Map

| Finding | Severity | Resolution |
|---|---|---|
| F1 (AC2 contradicts Fix 1) | error | D3 + AC3 (tests are REWRITTEN, not preserved) |
| F2 ("skill's call on which path") | error | D1 locks Fix 1, rejects Fix 2 + both |
| F3 (missing AUTHORITATIVE SCOPE banner + wrong filename) | warning | This file is `CONTEXT-9926.md` with the banner |
| F4 ("both" concurrency hazard) | warning | Moot — Fix 2 rejected per D1 |
| F5 (zero-roles edge case) | warning | D2 + AC2 |
| F6 (bifurcated AC3) | warning | D4: single unit-test path |
| F7 ("existing 7 tests" — there are 16) | warning | D5 + AC3: all 16 must pass |
