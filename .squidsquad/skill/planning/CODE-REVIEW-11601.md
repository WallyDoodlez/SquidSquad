After a thorough review of both files — tracing every code path, comparing against `cycle_post._discover_harness_port()` and `cycle_pre._discover_harness_port()`, verifying error handling, retry logic, test coverage, and edge cases — I find no correctness issues, regressions, or philosophy violations.

- **`_discover_port()`** (event_poll.py:92-125) is byte-for-byte identical in logic to `cycle_post._discover_harness_port()` (cycle_post.py:764-788) and `cycle_pre._discover_harness_port()` (cycle_pre.py:282-302): SQUID_DIR check → 5-level parent walk → default 7373. The "always returns int" contract is verified.
- **File-present path**: Same as before — `int(port_file.read_text(...).strip())` — no regression.
- **Defensive `if port is None` guard** (event_poll.py:186-188) is never reached post-fix but is exercised via stub in `test_poll_returns_none_when_discover_port_returns_none` (test_event_poll.py:447-456).
- **Tests** cover: file-present, file-absent→7373, parent-walk inheritance, garbage→7373, never-None contract, eviction, retry/backoff, timeout, since-seeding, URL building, malformed payloads, connection drops, exit codes, and wait-loop advancement.

NO_FINDINGS