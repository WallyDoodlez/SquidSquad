I've now thoroughly read both files — `references/scripts/harness.py` (the full ~5300-line harness) and the test file. Let me trace through every spawn path and verify the `reset_session_telemetry()` implementation.

Here's my analysis of all 5 spawn paths where `reset_session_telemetry()` is called:

| # | Spawn Path | Location | Under lock? | `last_dispatch_at = None` present? |
|---|-----------|----------|-------------|-----------------------------------|
| 1 | Auto-reboot (`update_health`) | L1180-1206 | Yes (`with self._lock`) | L1201 |
| 2 | `_deferred_init` auto-start | L2186-2200 | No (pre-existing TOCTOU) | L2197 |
| 3 | `POST /agents/all/start` | L2517-2531 | No (pre-existing TOCTOU) | L2528 |
| 4 | `POST /agents/{role}/start` | L2631-2649 | No (pre-existing TOCTOU) | L2643 |
| 5 | Deploy respawn (`_respawn_agent_process`) | L4325-4336 | No (pre-existing) | L4330 |

All 5 call `reset_session_telemetry()` (verified at L1206, L2198, L2529, L2644, L4331). The structural test counts 5 `last_dispatch_at = None` (excluding `__init__`) and 5 `.reset_session_telemetry()` calls — they match.

After reviewing the reset scope, spawn-path coverage, persistence semantics, thread safety, and the regression tests, I find no issues.

NO_FINDINGS