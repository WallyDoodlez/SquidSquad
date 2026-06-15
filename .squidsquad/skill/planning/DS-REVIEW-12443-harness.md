I've now thoroughly reviewed the diff and the surrounding context. Let me present my finding.

---

### Finding 1

- **File**: `references/scripts/harness.py`
- **Line**: 2232–2233, 2241–2242, 2267 (the `hook_activity` function)
- **Severity**: warning
- **Issue**: `hook_activity` omits all `_log` calls for dropped and recorded heartbeats, despite being advertised as mirroring `/hooks/session-end` which logs every code path.
- **Evidence**: The commit message states "mirrors /hooks/session-end (X-Agent-Role header, uninterpolated-token=no-role, unknown/missing-role drop, fail-open always-200)." The mirrored endpoint `hook_session_end` logs three distinct paths:
  - **no-role drop** (line 2164): `_log(f"SessionEnd hook DROPPED — no X-Agent-Role header (reason={reason!r})")`
  - **unknown-role drop** (line 2174): `_log(f"SessionEnd hook DROPPED unknown role={role!r} (reason={reason!r})")`
  - **success** (line 2188): `_log(f"{role}: SessionEnd reason={reason!r} recorded (#12418)")`

  `hook_activity` has zero `_log` calls anywhere — silent returns for all three paths (lines 2232–2233 no-role, lines 2241–2242 unknown-role, line 2267 success). Since activity heartbeats fire on **every tool call**, silent drops are an operational blind spot: operators cannot distinguish between "no heartbeats arriving" and "heartbeats arriving but being silently dropped due to a misconfigured `X-Agent-Role` header."

- **Suggested fix**: Add `_log` calls in `hook_activity` matching the pattern from `hook_session_end`:
  - After line 2233 (no-role): `_log("Activity hook DROPPED — no X-Agent-Role header")`
  - After line 2242 (unknown-role): `_log(f"Activity hook DROPPED unknown role={role!r}")`
  - Before line 2267 (success, but throttled): optionally log at debug level or only on first heartbeat, since these fire per-tool-call and would be noisy logged at default level. Minimally, log the drop paths.