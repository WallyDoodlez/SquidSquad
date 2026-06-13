NO_FINDINGS

The implementation correctly satisfies all acceptance criteria:

- **Dead holder → remove+log**: Lines 229-239 unlink the lock and print a reclaim message when `_is_process_alive` returns `False`.
- **Live holder → preserve**: Line 227-228 returns `False` without touching the lock when the holder PID is alive.
- **No lock → no-op**: Line 215-216 returns `False` immediately when the lock file doesn't exist.
- **Unparseable → preserve+warn**: Lines 217-226 catch both `ValueError` (malformed JSON) and `OSError` (I/O failure), fall back to `holder_pid = None`, and emit a stderr warning. Non-integer `pid` values (missing key, wrong type) trigger the same warn-and-preserve path.
- **Unlink race → treat as gone**: Lines 231-232 catch `FileNotFoundError` specifically (another reclaimer or process already removed it) and return `False` as a no-op.
- **Runs before Popen**: The call is at line 524, while `subprocess.Popen` is at line 561 — strictly before.
- **No unhandled exceptions**: Every operation that could raise (`json.loads`, `read_text`, `unlink`, `_is_process_alive`) is guarded by an appropriate `try/except` block.
- **No silent swallow of a reclaimable stale lock**: The only error path that leaves a known-stale lock in place (OSError on unlink, line 233) emits an explicit stderr warning, conforming to the "conservative (leave+warn)" directive.