I have thoroughly reviewed all four changed files and their tests. Here is my complete analysis:

## Analysis Summary

### activity_hook.py — Fail-open completeness
- `main()` line 85-100: `os.environ.get` → never raises. `sys.stdin.read()` is inside try/except (line 89-96). `payload.get()` → never raises. `post_activity()` → has its own try/except (line 74-82). `return 0` → never raises. The outer `if __name__ == "__main__"` try/except (line 103-109) catches `Exception` and exits 0 — belt-and-suspenders.
- `post_activity()` line 59-82: every error path (no role → line 64-65, connection error → line 81-82, timeout → line 81-82, bad response → line 80-81) returns False without raising. Complete fail-open.
- `_discover_port()` line 47-56: `OSError` and `ValueError` caught, safe fallback to 7373.

### compose.py — Hook JSON shape and idempotency
- `_activity_hook_group()` line 1839-1849: `type: "command"`, `async: true`, exec form with `["${CLAUDE_PROJECT_DIR}/references/scripts/activity_hook.py"]` — one-element args array, no shell, cross-platform.
- `_ensure_hook_entries()` line 1853-1886: correctly preserves all untouched keys (statusLine, other hooks). Compares `json.dumps(data, sort_keys=True)` before and after modification — same serialization both times ensures deterministic idempotency check. Corrupt file → empty dict → writes. Non-dict hooks → replaced with warning. Idempotent (line 1883-1884: returns False on no change).
- Refactored `_ensure_session_end_hook` (line 1890-1894) delegates to `_ensure_hook_entries` with identical logic. The warning message, comparison strategy, and write behavior are all preserved from the old standalone implementation.

### cycle_post.py — Heartbeat integration
- `_do_activity_heartbeat()` line 926-939: lazy imports `activity_hook` inside try/except. Passes `port=_discover_harness_port()` explicitly (liveness-aware). Any exception — import error, poster raise, port discovery failure — is swallowed.
- Positioned at step 8b (line 1046-1047), after step 8's cycle-end event and before step 9's context pressure check. Correct: heartbeat fires regardless of restart decision, and even if step 8's event_bus import fails (try/except at line 1037-1044).
- `_discover_harness_port()` line 782-815 always returns an int, never raises.

### Tests — Egress guard and coverage
- `_block_live_harness_egress` autouse fixture (test_cycle_post.py line 58-108): correctly patches `activity_hook.post_activity` to a no-op (line 103-107), preventing egress leaks from any test that reaches `cycle_post.main()`. Tests that need to assert heartbeat behavior re-patch inside their own body (line 545).
- `test_heartbeat_import_error_is_fail_open` (line 561-564): `patch.dict("sys.modules", {"activity_hook": None})` causes `import activity_hook` to raise `ImportError` (Python looks up `sys.modules`, finds `None`). Caught by `except Exception: pass`. Correct.
- `test_idempotent_no_rewrite` (line 593-596): first call True, second False — confirms idempotency.
- `test_coexists_with_session_end_hook` (line 598-616): verifies both hook families coexist, SessionEnd remains `type: "http"`.

### Cross-platform
- Exec form (`args` array, not shell string) avoids quoting issues. `${CLAUDE_PROJECT_DIR}` substitution is done by Claude Code itself. Forward-slash path separators work on Windows Python.
- `_repo_root()` uses `Path(__file__).resolve().parent.parent.parent` — pure pathlib, cross-platform.

NO_FINDINGS