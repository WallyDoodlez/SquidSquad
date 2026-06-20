"""#12294 — keep .claude-pid authoritative across harness restart.

Restart-time liveness hardening (design C + A, dependency-free):

- **A (read-side image verification)** — ``update_health`` trusts a PID only
  when it is alive AND its image is actually claude. A possibly-stale
  ``.claude-pid`` is reconciled against the real process (AC1); a recycled
  live non-claude PID is reclaimed, not trusted (AC3); an undetermined image
  falls back to plain liveness so a live agent is never mis-reclaimed (AC2).
- **C (write-side self-heal)** — when the harness holds an image-verified live
  claude PID, it writes ``.claude-pid`` back from in-memory truth when the file
  is missing or divergent, so a *subsequent* restart isn't blind to the agent.

AC4 regression scenarios are exercised through ``update_health`` itself.

The never-recorded-orphan edge (a live claude.exe whose PID was never recorded
in either ``.claude-pid`` or harness state) is NOT covered here — recovering it
needs cwd/cmdline discovery (psutil), a new dependency gated on a human
decision. terminal_pid descendant re-resolution can't substitute on Windows:
the recorded terminal_pid is the short-lived ``cmd /c start`` process that
exits immediately (boot_remote.py), so claude.exe is detached, not its child.
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import reboot_agent


class TestWriteClaudePid:
    """#12294 (C): the write-back helper, symmetric with _read_claude_pid."""

    def test_writes_pid_atomically(self, tmp_path):
        assert reboot_agent.write_claude_pid(str(tmp_path), "skill", 4242) is True
        pid_file = tmp_path / ".squidsquad" / "skill" / ".claude-pid"
        assert pid_file.read_text(encoding="utf-8") == "4242"
        assert not pid_file.with_suffix(".tmp").exists()

    def test_round_trips_through_read(self, tmp_path):
        reboot_agent.write_claude_pid(str(tmp_path), "skill", 7777)
        pid, _alive = reboot_agent._read_claude_pid(str(tmp_path), "skill")
        assert pid == 7777

    def test_rejects_bad_pid(self, tmp_path):
        for bad in (None, 0, -1, True, "5"):
            assert reboot_agent.write_claude_pid(str(tmp_path), "skill", bad) is False
        assert not (tmp_path / ".squidsquad" / "skill" / ".claude-pid").exists()

    def test_oserror_is_swallowed(self, tmp_path, capsys):
        with patch("reboot_agent.Path") as fake_path:
            chain = MagicMock(name="pid_file")
            chain.__truediv__.return_value = chain  # Path(c)/".."/role/".." → chain
            chain.parent.mkdir.side_effect = OSError("disk full")
            fake_path.return_value = chain
            assert reboot_agent.write_claude_pid(str(tmp_path), "skill", 4242) is False
        assert "WARNING" in capsys.readouterr().err


def _fresh_state(role, clone_path):
    """Build a HarnessState with a single agent, no pollers/side effects."""
    import harness
    state = harness.HarnessState()
    state.agents[role] = harness.AgentState(role, clone_path)
    return harness, state


class TestUpdateHealthImageVerified:
    """#12294 A + C — exercised through update_health (AC1/AC2/AC3/AC4)."""

    ROLE = "skill"
    CLONE = "/fake/clone"

    def _run(self, monkeypatch, *, in_mem_pid, file_pid, file_alive,
             claude_alive, agent_setup=None, legacy_health="unknown"):
        """Drive one update_health pass with the liveness layer mocked.

        ``claude_alive`` is a predicate pid->bool standing in for the
        image-verified is_claude_process_alive.
        """
        harness, state = _fresh_state(self.ROLE, self.CLONE)
        agent = state.agents[self.ROLE]
        agent.claude_pid = in_mem_pid
        agent.status = "running"
        agent.intent = harness.AgentState.INTENT_RUNNING
        if agent_setup:
            agent_setup(agent)

        boot_agent = MagicMock(return_value={"success": True, "terminal_pid": 1})
        write_pid = MagicMock(return_value=True)
        health = MagicMock(return_value={"health": legacy_health})

        monkeypatch.setattr(harness.boot_remote, "_get_all_roles",
                            lambda: [self.ROLE])
        monkeypatch.setattr(harness.boot_remote, "_get_clone_path",
                            lambda r: self.CLONE)
        monkeypatch.setattr(harness.boot_remote, "boot_agent", boot_agent)
        monkeypatch.setattr(harness.process_utils, "is_claude_process_alive",
                            claude_alive)
        monkeypatch.setattr(harness.reboot_agent, "_read_claude_pid",
                            lambda c, r: (file_pid, file_alive))
        monkeypatch.setattr(harness.reboot_agent, "write_claude_pid", write_pid)
        monkeypatch.setattr(harness.health_check, "check_agent_health",
                            lambda *a, **k: health())
        monkeypatch.setattr(state, "save_state", lambda: None)

        state.update_health()
        return agent, boot_agent, write_pid

    def test_ac4_i_stale_file_live_recorded_in_state_stays_running(self, monkeypatch):
        """Stale (dead) .claude-pid + live claude recorded in state →
        agent detected running, not respawned; file self-healed."""
        agent, boot_agent, write_pid = self._run(
            monkeypatch,
            in_mem_pid=5000,                  # restored from harness state
            file_pid=9999, file_alive=False,  # stale dead PID on disk
            claude_alive=lambda pid: pid == 5000,
        )
        assert agent.status == "running"
        assert agent.claude_pid == 5000
        boot_agent.assert_not_called()        # AC2 — never respawned
        write_pid.assert_called_once_with(self.CLONE, self.ROLE, 5000)  # C self-heal

    def test_ac4_iii_missing_file_live_recorded_in_state_stays_running(self, monkeypatch):
        """Missing .claude-pid + live claude recorded in state →
        detected running; file written back from in-memory truth."""
        agent, boot_agent, write_pid = self._run(
            monkeypatch,
            in_mem_pid=5000,
            file_pid=None, file_alive=False,  # missing file
            claude_alive=lambda pid: pid == 5000,
        )
        assert agent.status == "running"
        boot_agent.assert_not_called()
        write_pid.assert_called_once_with(self.CLONE, self.ROLE, 5000)

    def test_ac3_recycled_nonclaude_pid_is_reclaimed(self, monkeypatch):
        """A live PID recycled by a non-claude process must NOT be trusted as
        the agent — it is reclaimed (treated dead) and the agent respawns."""
        agent, boot_agent, write_pid = self._run(
            monkeypatch,
            in_mem_pid=None,                  # nothing recorded in state
            file_pid=7777, file_alive=True,   # live, but NOT claude
            claude_alive=lambda pid: False,   # image check fails for the recycled PID
        )
        # not trusted as alive → reconcile didn't adopt it, write-back skipped
        boot_agent.assert_called_once_with(self.ROLE)   # respawned, not masked
        write_pid.assert_not_called()
        assert agent.claude_pid is None

    def test_file_pid_adopted_when_image_verified(self, monkeypatch):
        """In-memory PID dead but .claude-pid points at a live claude →
        adopt it (AC1 reconcile) and keep running."""
        agent, boot_agent, write_pid = self._run(
            monkeypatch,
            in_mem_pid=1234, file_pid=4242, file_alive=True,
            claude_alive=lambda pid: pid == 4242,  # only the file PID is claude
        )
        assert agent.status == "running"
        assert agent.claude_pid == 4242
        boot_agent.assert_not_called()
        # file already holds 4242 (file_pid == resolved pid) → no write-back
        write_pid.assert_not_called()
