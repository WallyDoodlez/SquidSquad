Now I have full context. Here are my findings.

---

### Finding 1

- **File**: `.squidsquad/pm/planning/CONTEXT-9926.md`
- **Line**: 35–36 (D2 implementation note)
- **Severity**: warning
- **Issue**: The implementation note uses the undefined variable `all_roles_unhealthy` and describes an edge case that cannot occur under the current `_resolve_protected_pids` logic. The note says "Distinguish from `len(protected_pids) == 0 and roles_were_healthy_but_have_no_extra_claude_children`" — but if roles are healthy (cmd.exe alive, child_count == 1), their claude.exe IS in `protected`, so `len(protected_pids) > 0` by definition. The condition `len(protected_pids) == 0` with "healthy roles" is logically impossible under the function's contract. This confuses the implementer about what the D2 check should actually compare.
- **Evidence**: `_resolve_protected_pids` (orphan_cleanup.py lines 193–242) only skips a role when pid_file is missing, unparseable, cmd.exe dead, or child_count != 1. In all other cases the role's claude.exe PID is added to `protected`. The only way `len(protected) == 0` is if no role passes all four checks — which IS "all roles unhealthy." The "normal idle state" the note warns about (healthy roles, no extra children) always produces `len(protected) > 0`.
- **Suggested fix**: Replace the two-sentence implementation note with a single unambiguous condition: "Check `len(protected) == 0` AFTER `_resolve_protected_pids` returns. If true, abort the entire sweep (D2 backstop). If `len(protected) > 0`, proceed — even if `skipped_roles` is non-empty — and use the partial protected set. The `len(protected) == 0` check covers all cases: no roles configured, all roles dead, all roles missing pid files, and all roles with wrong child count."

---

### Finding 2

- **File**: `.squidsquad/pm/planning/CONTEXT-9926.md`
- **Lines**: 55, 69
- **Severity**: warning
- **Issue**: D5 and AC3 claim the test file has "currently 16" test functions, but the actual count is **25** (16 standalone `def test_*` functions plus 9 methods in `class TestKillReverify9937` added by #9937). AC3 also says "Total green test count is unchanged or higher than the current 16" — this baseline is wrong. The implementer reading "16" may mistakenly believe only 16 tests need to pass, when all 25 must pass.
- **Evidence**: `tests/test_orphan_cleanup_9688.py` contains 16 standalone test functions (lines 87–412) plus the `TestKillReverify9937` class (line 420) with 9 methods (lines 429–548). The #9937 code (`_pid_is_claude_exe` at orphan_cleanup.py lines 274–327) and its tests are already present in the file at the time CONTEXT-9926.md was authored (the #9937 issue is referenced as "already shipped").
- **Suggested fix**: Replace "16" with "25" in D5 line 55 and AC3 line 69. AC3 should read: "Total green test count is unchanged or higher than the current 25."

---

### Finding 3

- **File**: `.squidsquad/pm/planning/CONTEXT-9926.md`
- **Lines**: 39–42 (D3 test rewrite specification)
- **Severity**: warning
- **Issue**: D3 specifies what the rewritten tests must *assert* but omits a necessary change to the *mock setup*. The existing test `test_d7_missing_claude_pid_skips_entire_sweep` (test file line 217) mocks `_is_pid_alive` with `return_value=True`, which makes ALL PIDs appear alive. In the rewritten per-role-skip test, the sweep proceeds for the healthy role, and the orphan candidate (PID 8008, parent 99999) would be classified as "live subagent" (kept), not "orphan" (killed), because `_is_pid_alive(99999)` returns `True`. The assertion "orphans of other roles ARE killed" would fail unless the implementer also changes the `_is_pid_alive` mock to return `False` for non-cmd.exe PIDs (e.g., `side_effect=lambda pid: pid == 1000`).
- **Evidence**: Test file line 217: `patch.object(orphan_cleanup, "_is_pid_alive", return_value=True)`. In the current test this is irrelevant because the sweep aborts before classification. In the rewritten test, classification runs for the healthy role's processes, and `_classify` (orphan_cleanup.py line 269) calls `_is_pid_alive(ppid)` to distinguish live subagents from orphans. An always-True mock makes every non-protected process appear to be a live subagent.
- **Suggested fix**: Add a sentence to D3: "The rewritten tests must also adjust the `_is_pid_alive` mock so that only the healthy role's cmd.exe PID is considered alive; the orphan's parent PID must be dead (`side_effect=lambda pid: pid == <healthy_cmd_pid>`)." This ensures the implementer doesn't write a test whose mock contradicts its own assertion.

---

### Finding 4

- **File**: `.squidsquad/pm/planning/CONTEXT-9926.md`
- **Line**: 77 (AC7)
- **Severity**: warning
- **Issue**: AC7's live-system smoke test says "successfully reaps at least one orphan from another role" but does not specify how to ensure at least one orphan exists at test time. Orphans are transient — they only exist when a previous subagent invocation left a `claude.exe` with a dead parent. On a freshly booted system where no subagent tasks have run, there will be zero orphans to reap, and the test will fail regardless of whether the per-role skip code is correct. The smoke test underspecifies its precondition.
- **Evidence**: The evidence motivating #9926 (CONTEXT-9926.md line 19) describes orphans that accumulated over days across reboots — they are not guaranteed to exist at any arbitrary moment. AC7 says "killed (leaving a stale `.claude-pid`)" for the unhealthy role but says nothing about how the *other* role should have an orphan to reap.
- **Suggested fix**: Add a precondition step to AC7: "Before killing the unhealthy role's cmd.exe, trigger at least one Agent-tool subagent invocation on a healthy role, then kill that subagent's parent (or let it complete naturally) so at least one orphan `claude.exe` exists in the process table. Verify the orphan exists via `Get-CimInstance Win32_Process` before running the test." Alternatively, scope the smoke test to validate only that the sweep *does not abort* when one role is unhealthy — the actual reaping is already covered by unit tests per D4.

---

### Answers to the five explicit questions

**(a) Residual gaps from the first review:** Finding 2 (stale test count — the DS review's F7 correction of "7 → 16" is itself now stale at "16 → 25" because #9937 landed after the DS review but before this CONTEXT was written) and Finding 1 (the D2 implementation note uses undefined terms and describes an impossible edge case — a new specification gap introduced by the rewrite, not directly addressed in the DS review).

**(b) D2 zero-healthy-roles backstop testability:** It **is** testable from unit tests alone. The implementer can mock `_role_pid_files` to return multiple roles, mock `_is_pid_alive` to make all cmd.exe dead, and assert `skipped_run is True` / `_kill` is never called. The existing `test_no_roles_discoverable_skips_sweep` already covers the no-roles case. A new unit test covering "all configured roles unhealthy" (e.g., 2 roles, both cmd.exe dead) would close the gap — no harness integration needed.

**(c) AC3's rewritten test assertion semantics:** Partially precise. D3 specifies *what* to assert (`result["skipped_roles"]` lists ONLY the unhealthy role; orphans ARE killed) and D3's requirement to "replace the normative assertion message" is correct. But D3 omits the necessary mock-adjustment detail (Finding 3 above). QA verifying the rewrite would see the old `return_value=True` mock, attempt to run the test, get a failure (orphan not killed), and conclude the implementation is broken when the test setup is wrong. The assertion semantics are correct; the test-construction semantics are underspecified.

**(d) AC7's live-system smoke test scope:** It is sufficiently scoped in its *intent* (exactly one role unhealthy, at least one other role healthy) but underspecified in its *precondition* (Finding 4). The question of "which roles to leave healthy" is answerable: leave all roles *except* the killed one healthy. The under-specification is not about role selection but about orphan existence.

**(e) Interaction with #9937:** The changes are **independent**. #9937 adds `_pid_is_claude_exe` (orphan_cleanup.py lines 274–327) as a re-verification gate inside `_kill` (line 342) — it operates at the individual-kill level. #9926 changes the `sweep()` function's abort logic (lines 418–428) — it operates at the sweep-orchestration level. Neither supersedes the other; they address orthogonal race conditions (PID reuse vs. sweep abort). The #9937 tests (`TestKillReverify9937`, 9 methods) mock `_pid_is_claude_exe` in isolation and will not be affected by the per-role skip change. The #9926 change does not touch `_kill` or `_pid_is_claude_exe`.