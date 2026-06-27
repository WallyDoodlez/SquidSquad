"""#12492 (#12271 slice-4 pt2) — progress-liveness CUTOVER.

The shadow machinery (#12460) computed progress_liveness alongside the PID check
but never acted on it. This cutover makes progress_liveness AUTHORITATIVE: a
ZOMBIE (PID-alive but progress-dead — the #10855 inert-agent case PID-liveness
reports healthy forever) is killed in the health poll so the normal death/reboot
path respawns it. PID is demoted to teardown-only: PID-aliveness no longer vetoes
a reboot.

These tests pin the cutover decision in `update_health` — using the same
deterministic patching as TestForceKillSafetyNet in test_harness.py — and the
guards that must hold: only RUNNING agents, never under _NO_AUTO_REBOOT, off when
the escape hatch reverts to shadow-only, and never for a genuinely healthy or
already-dead PID (AC1-AC4).
"""

import sys
import unittest
from unittest.mock import patch

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))

import harness  # noqa: E402
from harness import HarnessState, AgentState  # noqa: E402


class TestProgressLivenessCutover12492(unittest.TestCase):
    def _set_up(self, *, intent=AgentState.INTENT_RUNNING, pid=12345,
                status="running"):
        hs = HarnessState()
        agent = AgentState("skill", "/clone")
        agent.intent = intent
        agent.claude_pid = pid
        agent.status = status
        agent.bootup_complete = True
        hs.set_agent("skill", agent)
        return hs, agent

    def _patches(self, *, pid_alive, prog_alive, prog_reason="zombie",
                 fake_now=1000.0):
        return [
            patch("harness.boot_remote._get_all_roles", return_value=["skill"]),
            patch("harness.boot_remote._get_clone_path", return_value="/clone"),
            patch("harness.boot_remote._is_process_alive",
                  return_value=pid_alive),
            patch("harness.process_utils.is_claude_process_alive",
                  return_value=pid_alive),
            patch("harness.reboot_agent.write_claude_pid", return_value=True),
            patch("harness.reboot_agent._read_claude_pid",
                  return_value=(None, None)),
            patch.object(AgentState, "progress_liveness",
                         return_value=(prog_alive, prog_reason)),
            patch("harness.time.time", return_value=fake_now),
            patch("harness._log"),
        ]

    def _run(self, hs, patches):
        with patch("harness.reboot_agent._kill_process") as kill:
            for p in patches:
                p.start()
            try:
                hs.update_health()
            finally:
                for p in patches:
                    p.stop()
        return kill

    # -- the core cutover: zombie → kill -----------------------------------

    def test_zombie_is_killed_when_authoritative(self):
        """PID alive + progress dead + RUNNING + cutover on → kill the inert PID."""
        hs, agent = self._set_up()
        with patch("harness._PROGRESS_LIVENESS_AUTHORITATIVE", True), \
                patch("harness._NO_AUTO_REBOOT", False):
            kill = self._run(hs, self._patches(pid_alive=True, prog_alive=False))
        kill.assert_called_once_with(12345)

    def test_healthy_agent_not_killed(self):
        """PID alive + progress ALSO alive → never a zombie, never killed."""
        hs, agent = self._set_up()
        with patch("harness._PROGRESS_LIVENESS_AUTHORITATIVE", True), \
                patch("harness._NO_AUTO_REBOOT", False):
            kill = self._run(hs, self._patches(pid_alive=True, prog_alive=True))
        kill.assert_not_called()

    # -- guards ------------------------------------------------------------

    def test_shadow_only_does_not_kill(self):
        """Escape hatch: _PROGRESS_LIVENESS_AUTHORITATIVE=False reverts to the
        pre-cutover shadow-only behaviour — divergence logged, never acted on."""
        hs, agent = self._set_up()
        with patch("harness._PROGRESS_LIVENESS_AUTHORITATIVE", False), \
                patch("harness._NO_AUTO_REBOOT", False):
            kill = self._run(hs, self._patches(pid_alive=True, prog_alive=False))
        kill.assert_not_called()

    def test_no_auto_reboot_does_not_kill(self):
        """A kill with no respawn is silent death — worse than the zombie. The
        cutover must respect _NO_AUTO_REBOOT and leave the process alone."""
        hs, agent = self._set_up()
        with patch("harness._PROGRESS_LIVENESS_AUTHORITATIVE", True), \
                patch("harness._NO_AUTO_REBOOT", True):
            kill = self._run(hs, self._patches(pid_alive=True, prog_alive=False))
        kill.assert_not_called()

    def test_non_running_intent_not_killed_by_cutover(self):
        """intent=DEPLOYING (not RUNNING) is handled by its own deploy path, not
        the zombie cutover — even with a progress-dead verdict. (Deploying has no
        force-kill net at running, so a kill here would be the cutover's.)"""
        hs, agent = self._set_up(intent=AgentState.INTENT_DEPLOYING)
        with patch("harness._PROGRESS_LIVENESS_AUTHORITATIVE", True), \
                patch("harness._NO_AUTO_REBOOT", False):
            kill = self._run(hs, self._patches(pid_alive=True, prog_alive=False))
        kill.assert_not_called()

    def test_dead_pid_is_not_a_cutover_kill(self):
        """A genuinely dead PID (alive=False) is the normal death path, not the
        zombie cutover — the cutover only fires for an ALIVE PID. No kill call
        (the process is already gone; the reboot path respawns it)."""
        hs, agent = self._set_up()
        with patch("harness._PROGRESS_LIVENESS_AUTHORITATIVE", True), \
                patch("harness._NO_AUTO_REBOOT", False):
            kill = self._run(hs, self._patches(pid_alive=False, prog_alive=False))
        kill.assert_not_called()

    def test_kill_failure_does_not_abort_poll(self):
        """If _kill_process raises (already-dead / permission), the health poll
        must not crash — the next poll re-evaluates."""
        hs, agent = self._set_up()
        patches = self._patches(pid_alive=True, prog_alive=False)
        with patch("harness._PROGRESS_LIVENESS_AUTHORITATIVE", True), \
                patch("harness._NO_AUTO_REBOOT", False), \
                patch("harness.reboot_agent._kill_process",
                      side_effect=OSError("already dead")):
            for p in patches:
                p.start()
            try:
                hs.update_health()  # must not raise
            finally:
                for p in patches:
                    p.stop()


if __name__ == "__main__":
    unittest.main()
