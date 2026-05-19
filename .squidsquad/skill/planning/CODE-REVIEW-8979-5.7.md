Now I have all the evidence I need. Let me produce the final review.

---

### Finding 1

- **File**: `references/scripts/squidsquad_cli.py`
- **Line**: 168–170 and 177
- **Severity**: error
- **Issue**: `cmd_stop` unconditionally returns 0 (line 177) even when the harness API reports a stop failure. The single-role path (lines 168–170) does not extract `result.get("success")` and does not branch on it, unlike `cmd_start` (line 143–147) and `cmd_restart` (line 189–191), which both inspect `success` and return `0 if success else 1`.

- **Evidence**: `start_team.cmd_stop` (lines 76–83 of `start_team.py`) iterates roles and checks `rc = squidsquad_cli.cmd_stop(role)`; it returns `False` only when `rc != 0`. Because `squidsquad_cli.cmd_stop` always returns 0, `start_team.cmd_stop` will *always* report success — stop failures are silently swallowed. The test `test_cmd_stop_returns_false_on_failure` at `tests/test_start_team.py:44-47` only passes because it patches the return value to 1; the real implementation never returns 1. Meanwhile `cmd_start(role)` (line 147) and `cmd_restart` (line 191) both correctly return 1 on failure, making `cmd_stop` the lone inconsistent command.

- **Suggested fix**: In the single-role branch (after line 170), extract `success = result.get("success", False)`, print an OK/FAIL line consistent with `cmd_restart`, and `return 0 if success else 1`. Similarly, the all-agents branch (lines 171–175) should aggregate individual `success` fields and return non-zero if any agent failed.

---

### Finding 2

- **File**: `references/scripts/squidsquad_cli.py`
- **Line**: 158
- **Severity**: warning
- **Issue**: The all-agents path of `cmd_start` (`cmd_start()` with `role=None`) always returns 0 (line 158) regardless of whether individual agent starts succeeded. The per-role path (line 147) correctly returns 0/1 based on `success`.

- **Evidence**: The all-agents branch at lines 149–158 prints per-agent `OK`/`FAIL` status but then unconditionally `return 0`. While `start_team.cmd_boot` always calls the per-role path (`cmd_start(role)`) and is therefore unaffected, a direct `squidsquad_cli start` invocation would exit 0 even when every agent failed to start. This creates a misleading operator experience inconsistent with the per-role behavior.

- **Suggested fix**: After the results loop (line 156), compute `all_ok = all(r.get("success", False) for r in result.get("results", []))` and `return 0 if all_ok else 1`.

---

### Additional observations (not findings)

The remaining acceptance criteria are satisfied:

1. **CLI surface preservation**: `start_team.py` retains `--all`, `--role`, `--reboot`, `--stop`, and `--force` argparse flags (lines 94–106). `--force` is a documented no-op with a deprecation print (lines 62–64). All legacy invocations parse correctly.

2. **Pure delegation**: `cmd_boot` (lines 50–56), `cmd_reboot` (lines 59–77), and `cmd_stop` (lines 80–86) all iterate roles and call `squidsquad_cli.cmd_start`/`cmd_restart`/`cmd_stop` respectively. No direct `boot_remote.boot_agent` or `reboot_agent._kill_process` calls exist — confirmed by source-grep guards at `tests/test_start_team.py:128-138`.

3. **Per-role `cmd_start`**: `squidsquad_cli.cmd_start(role=None)` (line 123) correctly dispatches to `/agents/{role}/start` when role is given (line 142) and `/agents/all/start` when None (line 151). The `main()` dispatch (lines 280–282) accepts an optional role argument.

4. **Tests**: `TestDelegation` verifies per-role delegation and failure propagation (modulo Finding 1). `TestRemovedHelpers` parametrically asserts removal of six deprecated helpers plus absence of direct `boot_remote`/`reboot_agent` calls. `TestSquidsquadCliPerRoleStart` validates the new per-role start path. All 52 new tests exercise the right contracts.