"""QA independent verification for #13276 — the TUI agent-refresh data path must
survive a None status (harness unreachable) end-to-end.

Independent angle vs skill's test_agent_rows_tolerates_none_status (which checks
agent_rows in isolation): the actual crash was in app.refresh_agents, which calls
BOTH agent_table_rows AND agent_rows over the fetch_status() result (None when the
harness is down). This exercises that exact consumer sequence with None and asserts
no exception + an empty/unreachable result. Authored by verifier (qa); preserved
permanently. Skips if the tui package is unavailable.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "references"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "references", "tui"))

try:
    import harness_client as hc
    _AVAILABLE = True
except Exception:
    _AVAILABLE = False


@unittest.skipUnless(_AVAILABLE, "tui.harness_client unavailable")
class TestRefreshPathNoneStatus13276(unittest.TestCase):
    def test_refresh_data_sequence_survives_none(self):
        # Mirror app.refresh_agents' data-layer calls with a harness-down status.
        status = None  # what fetch_status() returns on a transport error
        rows = hc.agent_table_rows(status, 0)
        meta = {r["role"]: r for r in hc.agent_rows(status, 0)}  # the line that crashed pre-fix
        reachable = status is not None
        self.assertEqual(rows, [])
        self.assertEqual(meta, {})
        self.assertFalse(reachable, "the 'unreachable' flag must now be reachable (no crash before it)")


if __name__ == "__main__":
    unittest.main()
