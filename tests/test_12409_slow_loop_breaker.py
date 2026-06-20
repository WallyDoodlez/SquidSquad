"""#12409 — frequency-based slow reboot-loop breaker.

#12244's breaker only trips on >=FAST_DEATH_THRESHOLD deaths that each lived
<FAST_DEATH_WINDOW_SECONDS. A loop where each session outlives that window (qa's
incident: 4 auto-reboots in ~18min, each >60s) keeps resetting the fast-death
streak, so #12244 never engages. This frequency breaker is lifetime-agnostic:
>=SLOW_LOOP_THRESHOLD auto-reboots within SLOW_LOOP_WINDOW_SECONDS → back off,
reusing the crash-looping + reboot_blocked_until machinery.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import harness
from harness import (AgentState, HarnessState, SLOW_LOOP_THRESHOLD,
                     SLOW_LOOP_WINDOW_SECONDS)

NOW = 1_000_000.0


class TestRebootHistoryHelpers(unittest.TestCase):
    def test_record_reboot_appends(self):
        a = AgentState("skill")
        a.record_reboot(NOW)
        self.assertEqual(a.reboot_history, [NOW])

    def test_record_reboot_prunes_outside_window(self):
        a = AgentState("skill")
        a.reboot_history = [NOW - SLOW_LOOP_WINDOW_SECONDS - 100,  # stale → pruned
                            NOW - 100]
        a.record_reboot(NOW)
        self.assertEqual(a.reboot_history, [NOW - 100, NOW])

    def test_recent_reboot_count_prunes_and_counts(self):
        a = AgentState("skill")
        a.reboot_history = [NOW - SLOW_LOOP_WINDOW_SECONDS - 1,   # just outside
                            NOW - SLOW_LOOP_WINDOW_SECONDS + 1,   # just inside
                            NOW - 10]
        self.assertEqual(a.recent_reboot_count(NOW), 2)
        # prune persisted as a side effect
        self.assertEqual(len(a.reboot_history), 2)

    def test_default_history_is_empty(self):
        self.assertEqual(AgentState("skill").reboot_history, [])


class TestRebootHistoryPersistence(unittest.TestCase):
    def test_to_dict_includes_history_copy(self):
        a = AgentState("skill")
        a.reboot_history = [NOW]
        d = a.to_dict()
        self.assertEqual(d["reboot_history"], [NOW])
        self.assertIsNot(d["reboot_history"], a.reboot_history)  # copy, not alias

    def test_save_load_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            sf = Path(tmp) / ".harness-state.json"
            with patch.object(harness, "HARNESS_STATE_FILE", sf):
                hs = HarnessState()
                a = AgentState("skill", "/clone/skill")
                a.reboot_history = [NOW - 50, NOW]
                hs.set_agent("skill", a)
                hs.save_state()
                hs2 = HarnessState()
                hs2.load_state()
                self.assertEqual(hs2.get_agent("skill").reboot_history,
                                 [NOW - 50, NOW])

    def test_load_drops_corrupt_history_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            sf = Path(tmp) / ".harness-state.json"
            sf.write_text(json.dumps({
                "harness_pid": 1, "start_time": 0.0, "port": 7373,
                "agents": {"skill": {"intent": "running", "status": "running",
                                     "clone_path": "", "claude_pid": None,
                                     "terminal_pid": None,
                                     "reboot_history": [NOW, "bad", None, 42]}},
            }), encoding="utf-8")
            with patch.object(harness, "HARNESS_STATE_FILE", sf), \
                 patch.object(harness, "_log"):
                hs = HarnessState()
                hs.load_state()
                self.assertEqual(hs.get_agent("skill").reboot_history, [NOW, 42])


class TestSlowLoopBreakerInUpdateHealth(unittest.TestCase):
    """Drive update_health for a SLOW reboot loop (lifetime > fast-death window)."""

    def _run(self, *, reboot_history, lifetime, fake_now=NOW, boot_result=None):
        hs = HarnessState()
        agent = AgentState("skill", "/clone")
        agent.status = "running"
        agent.intent = AgentState.INTENT_RUNNING
        agent.claude_pid = 4242                       # will read as dead
        agent.last_spawn_at = fake_now - lifetime     # how long it lived
        agent.reboot_history = list(reboot_history)
        hs.set_agent("skill", agent)

        boot = patch.object(harness.boot_remote, "boot_agent",
                            return_value=boot_result or {
                                "success": True, "terminal_pid": 9,
                                "action": "spawn"})
        patches = [
            patch.object(harness.boot_remote, "_get_all_roles", return_value=["skill"]),
            patch.object(harness.boot_remote, "_get_clone_path", return_value="/clone"),
            patch.object(harness.boot_remote, "_is_process_alive", return_value=False),
            patch.object(harness.process_utils, "is_claude_process_alive",
                         return_value=False),
            patch.object(harness.reboot_agent, "_read_claude_pid",
                         return_value=(None, False)),
            patch.object(harness.reboot_agent, "write_claude_pid", return_value=True),
            patch.object(harness.health_check, "check_agent_health",
                         return_value={"health": "unknown"}),
            patch.object(harness.time, "time", return_value=fake_now),
            patch.object(harness, "_log"),
            patch.object(hs, "save_state"),
        ]
        boot_mock = boot.start()
        for p in patches:
            p.start()
        try:
            hs.update_health()
        finally:
            for p in patches:
                p.stop()
            boot.stop()
        return hs.get_agent("skill"), boot_mock

    def test_slow_loop_trips_breaker_not_reboot(self):
        """A slow death (lived > fast-death window) with >=SLOW_LOOP_THRESHOLD
        recent reboots backs off instead of rebooting — #12244's fast-death
        breaker would have missed it (streak reset by the long lifetime)."""
        history = [NOW - 600, NOW - 400, NOW - 200]   # 3 within the 900s window
        self.assertGreaterEqual(len(history), SLOW_LOOP_THRESHOLD)
        agent, boot_mock = self._run(reboot_history=history,
                                     lifetime=harness.FAST_DEATH_WINDOW_SECONDS + 120)
        self.assertEqual(agent.status, "crash-looping")
        self.assertIsNotNone(agent.reboot_blocked_until)
        self.assertEqual(agent.consecutive_fast_deaths, 0)  # long lifetime → reset
        boot_mock.assert_not_called()                       # backed off, not rebooted

    def test_below_threshold_reboots_normally(self):
        history = [NOW - 600, NOW - 200]              # only 2 within window
        agent, boot_mock = self._run(reboot_history=history,
                                     lifetime=harness.FAST_DEATH_WINDOW_SECONDS + 120)
        boot_mock.assert_called_once_with("skill")          # normal reboot
        self.assertEqual(agent.status, "starting")

    def test_stale_reboots_outside_window_do_not_trip(self):
        """Reboots older than the window are pruned and don't count toward the
        breaker — a long-stable agent that finally dies reboots normally."""
        history = [NOW - SLOW_LOOP_WINDOW_SECONDS - 10,
                   NOW - SLOW_LOOP_WINDOW_SECONDS - 20,
                   NOW - SLOW_LOOP_WINDOW_SECONDS - 30]   # all stale
        agent, boot_mock = self._run(reboot_history=history,
                                     lifetime=harness.FAST_DEATH_WINDOW_SECONDS + 120)
        boot_mock.assert_called_once_with("skill")
        self.assertEqual(agent.status, "starting")

    def test_skip_result_does_not_record_reboot(self):
        """DS-12409 F1: a success/action='skip' dispatch (agent came back alive
        in a race) must NOT record a reboot or stamp last_spawn_at — no spawn
        happened, so it must not inflate the slow-loop count."""
        history = [NOW - 600]                          # 1 prior, below threshold
        agent, boot_mock = self._run(
            reboot_history=history,
            lifetime=harness.FAST_DEATH_WINDOW_SECONDS + 120,
            boot_result={"success": True, "action": "skip", "message": "alive"})
        boot_mock.assert_called_once_with("skill")
        # reboot_history unchanged (the prior entry is still in-window) — the
        # skip did NOT append a new reboot timestamp.
        self.assertEqual(agent.recent_reboot_count(NOW), 1)


if __name__ == "__main__":
    unittest.main()
