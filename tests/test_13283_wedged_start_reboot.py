"""#13283 — never-resolved-PID agent stuck at status="starting" must auto-reboot.

The verifier found this blind spot while verifying the #12492 cutover: an agent
whose initial spawn never resolved a claude PID sits at status="starting"
(claude_pid=None → alive=False, bootup_complete=False) and was invisible to every
reboot trigger — the cutover kill-step needs alive=True, the status block only
runs its death branch for status != "starting", and is_dead excludes "starting".

The fix consumes progress_liveness()'s wedged-boot-timeout verdict (#13179) for
this no-PID case via a `wedged_start` death_candidate disjunct, so the agent
reboots through the normal death/backoff path instead of needing a manual reap.

Tests use the same deterministic update_health patching as the #12492 cutover
tests, asserting boot_remote.boot_agent is (or isn't) called for the role.
"""

import sys
import unittest
from unittest.mock import patch

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))

import harness  # noqa: E402
from harness import HarnessState, AgentState  # noqa: E402

# A spawn old enough that lifetime > FAST_DEATH_WINDOW_SECONDS so the wedged
# reboot is immediate (not held by the #12244 fast-death backoff).
_SPAWN_AT = 1000.0
_NOW = _SPAWN_AT + harness.FAST_DEATH_WINDOW_SECONDS + 100.0


class TestWedgedStartReboot13283(unittest.TestCase):
    def _set_up(self, *, intent=AgentState.INTENT_RUNNING, status="starting"):
        hs = HarnessState()
        agent = AgentState("skill", "/clone")
        agent.intent = intent
        agent.claude_pid = None            # initial spawn never resolved a PID
        agent.bootup_complete = False
        agent.status = status
        agent.last_spawn_at = _SPAWN_AT
        hs.set_agent("skill", agent)
        return hs, agent

    def _patches(self, *, prog_alive, prog_reason="wedged-boot-timeout"):
        return [
            patch("harness.boot_remote._get_all_roles", return_value=["skill"]),
            patch("harness.boot_remote._get_clone_path", return_value="/clone"),
            patch("harness.boot_remote._is_process_alive", return_value=False),
            patch("harness.process_utils.is_claude_process_alive",
                  return_value=False),
            patch("harness.reboot_agent._read_claude_pid",
                  return_value=(None, None)),
            patch("harness.health_check.check_agent_health",
                  return_value={"health": "unknown"}),
            patch.object(AgentState, "progress_liveness",
                         return_value=(prog_alive, prog_reason)),
            patch("harness.time.time", return_value=_NOW),
            patch("harness._log"),
        ]

    def _run(self, hs, patches):
        with patch("harness.boot_remote.boot_agent",
                   return_value={"success": True, "action": "spawn",
                                 "terminal_pid": 999}) as boot:
            for p in patches:
                p.start()
            try:
                hs.update_health()
            finally:
                for p in patches:
                    p.stop()
        return boot

    def test_wedged_start_past_grace_is_rebooted(self):
        """No PID + status=starting + progress dead (past boot grace) + RUNNING
        + cutover on → auto-rebooted (the #13283 fix)."""
        hs, agent = self._set_up()
        with patch("harness._PROGRESS_LIVENESS_AUTHORITATIVE", True), \
                patch("harness._NO_AUTO_REBOOT", False):
            boot = self._run(hs, self._patches(prog_alive=False))
        boot.assert_called_once_with("skill")

    def test_legitimately_booting_not_rebooted(self):
        """Within boot grace progress_liveness returns alive ('booting') → a
        genuinely-booting agent must NOT be rebooted (no premature reap)."""
        hs, agent = self._set_up()
        with patch("harness._PROGRESS_LIVENESS_AUTHORITATIVE", True), \
                patch("harness._NO_AUTO_REBOOT", False):
            boot = self._run(hs, self._patches(prog_alive=True,
                                               prog_reason="booting"))
        boot.assert_not_called()

    def test_shadow_only_does_not_reboot(self):
        """Escape hatch off → the wedged_start verdict is not consumed."""
        hs, agent = self._set_up()
        with patch("harness._PROGRESS_LIVENESS_AUTHORITATIVE", False), \
                patch("harness._NO_AUTO_REBOOT", False):
            boot = self._run(hs, self._patches(prog_alive=False))
        boot.assert_not_called()

    def test_no_auto_reboot_does_not_respawn(self):
        """Under --no-auto-reboot the wedge is observed but not respawned
        (the death path's no-reboot branch handles it)."""
        hs, agent = self._set_up()
        with patch("harness._PROGRESS_LIVENESS_AUTHORITATIVE", True), \
                patch("harness._NO_AUTO_REBOOT", True):
            boot = self._run(hs, self._patches(prog_alive=False))
        boot.assert_not_called()

    def test_stopping_intent_not_rebooted(self):
        """A starting agent under intent=STOPPING (operator stop mid-boot) must
        not be rebooted by the wedge path (should_reboot is False)."""
        hs, agent = self._set_up(intent=AgentState.INTENT_STOPPING)
        with patch("harness._PROGRESS_LIVENESS_AUTHORITATIVE", True), \
                patch("harness._NO_AUTO_REBOOT", False):
            boot = self._run(hs, self._patches(prog_alive=False))
        boot.assert_not_called()


if __name__ == "__main__":
    unittest.main()
