I have completed a thorough review of all three changed files in the diff. Here is my analysis against each of the review criteria:

**Criterion (a) — False-negative liveness**: A dead localhost port triggers an immediate `ConnectionRefusedError` (an `OSError` subclass) — the kernel responds with RST in microseconds, well within the 0.5s timeout. The `except (OSError, ...)` clause catches it and returns `False`. A live port completes the TCP handshake and returns `True`. There is no scenario where a genuinely live harness on the file-port is wrongly skipped under normal localhost conditions.

**Criterion (b) — Latency/regression in `--wait` poll loop**: `_discover_port()` is called each poll iteration. For the common case (live harness, no stale port file), the connect succeeds in ~1ms. For the pathological stale-port case, a dead localhost port yields `ConnectionRefusedError` instantly (microseconds, not 0.5s — the timeout is a safety net for firewalled/non-local scenarios). No material latency regression.

**Criterion (c) — Always-returns-int contract**: All three functions return either a port from the candidates list (always `int`) or `_HARNESS_DEFAULT_PORT` (7373, also `int`). The existing `if port is None` guard in `event_poll.py:271` and `cycle_post.py:825,855` was already dead code pre-patch (the old functions also had `return 7373` fallbacks). No regression.

**Criterion (d) — Nothing listening**: All candidates fail → returns 7373. The caller's own HTTP probe fails cleanly and selects loop mode. Correct.

**Criterion (e) — Three copies consistent**: The three functions (`event_poll._discover_port`, `cycle_pre._discover_harness_port`, `cycle_post._discover_harness_port`) are structurally identical — same candidate list construction, same parent-walk logic (5 levels), same liveness-check loop, same fallback to 7373. Only trivial comment differences exist (e.g., `range(5):  # max 5 levels up` vs `range(5):`).

**Criterion (f) — Exception handling**: `_port_is_live` catches `OSError`, `ValueError`, `TypeError`, `OverflowError` — covering `None` (`TypeError`), garbage strings (`ValueError`), out-of-range ports (`OverflowError`), and all connection failures (`OSError`). `_read_port_file` catches `ValueError` and `OSError` on file read/parse, returns `None` for absent/unreadable/invalid files, and filters those `None` values out before they reach `_port_is_live`.

---

```
NO_FINDINGS
```