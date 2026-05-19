"""Tests for references/scripts/start_team.py — thin shim over squidsquad_cli.

Post-#4792 §5.7: start_team.py is a backward-compatible operator shim that
delegates every command to `squidsquad_cli.cmd_start/stop/restart`. The
familiar `--all` / `--role` / `--reboot` / `--stop` CLI surface is preserved
(Q11) but the sentinel-file lifecycle (`.stop` writes, force-kill fallback)
is gone.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import start_team


class TestDelegation:
    """Each cmd_* delegates to its squidsquad_cli counterpart per role."""

    def test_cmd_boot_delegates_per_role(self):
        with patch.object(start_team.squidsquad_cli, "cmd_start", return_value=0) as m:
            ok = start_team.cmd_boot(["pm", "skill"])
        assert ok is True
        assert m.call_args_list == [(("pm",),), (("skill",),)]

    def test_cmd_boot_returns_false_on_any_failure(self):
        with patch.object(start_team.squidsquad_cli, "cmd_start",
                          side_effect=[0, 1]) as m:
            ok = start_team.cmd_boot(["pm", "skill"])
        assert ok is False
        assert m.call_count == 2

    def test_cmd_stop_delegates_per_role(self):
        with patch.object(start_team.squidsquad_cli, "cmd_stop", return_value=0) as m:
            ok = start_team.cmd_stop(["skill"])
        assert ok is True
        m.assert_called_once_with("skill")

    def test_cmd_stop_returns_false_on_failure(self):
        with patch.object(start_team.squidsquad_cli, "cmd_stop", return_value=1):
            ok = start_team.cmd_stop(["skill"])
        assert ok is False

    def test_cmd_reboot_delegates_per_role(self):
        with patch.object(start_team.squidsquad_cli, "cmd_restart", return_value=0) as m:
            ok = start_team.cmd_reboot(["skill"])
        assert ok is True
        m.assert_called_once_with("skill")

    def test_cmd_reboot_force_is_noop(self, capsys):
        """--force is preserved on the CLI for muscle memory but no longer
        invokes a direct SIGKILL fallback. Per CONTEXT-4792.md §5.7, the
        harness force-kill safety net covers stuck cases."""
        with patch.object(start_team.squidsquad_cli, "cmd_restart", return_value=0) as m:
            ok = start_team.cmd_reboot(["skill"], force=True)
        assert ok is True
        m.assert_called_once_with("skill")
        out = capsys.readouterr().out
        assert "deprecated no-op" in out

    def test_cmd_reboot_returns_false_on_failure(self):
        with patch.object(start_team.squidsquad_cli, "cmd_restart", return_value=1):
            ok = start_team.cmd_reboot(["skill"])
        assert ok is False


class TestCLIParsing:
    def test_all_flag_defaults_to_boot(self):
        with patch.object(sys, "argv", ["start_team.py", "--all"]):
            with patch.object(start_team, "cmd_boot", return_value=True) as mock_boot:
                with patch.object(start_team, "_get_all_roles", return_value=["pm", "skill"]):
                    start_team.main()
                    mock_boot.assert_called_once_with(["pm", "skill"])

    def test_reboot_single_role(self):
        with patch.object(sys, "argv", ["start_team.py", "--reboot", "skill"]):
            with patch.object(start_team, "cmd_reboot", return_value=True) as mock_reboot:
                with patch.object(start_team, "_get_all_roles", return_value=["pm", "skill"]):
                    start_team.main()
                    mock_reboot.assert_called_once_with(["skill"], force=False)

    def test_stop_single_role(self):
        with patch.object(sys, "argv", ["start_team.py", "--stop", "skill"]):
            with patch.object(start_team, "cmd_stop", return_value=True) as mock_stop:
                with patch.object(start_team, "_get_all_roles", return_value=["pm", "skill"]):
                    start_team.main()
                    mock_stop.assert_called_once_with(["skill"])

    def test_role_flag_with_default_action_boots(self):
        with patch.object(sys, "argv", ["start_team.py", "--role", "skill"]):
            with patch.object(start_team, "cmd_boot", return_value=True) as mock_boot:
                start_team.main()
                mock_boot.assert_called_once_with(["skill"])

    def test_reboot_all(self):
        with patch.object(sys, "argv", ["start_team.py", "--reboot", "--all"]):
            with patch.object(start_team, "cmd_reboot", return_value=True) as mock_reboot:
                with patch.object(start_team, "_get_all_roles", return_value=["pm", "skill"]):
                    start_team.main()
                    mock_reboot.assert_called_once_with(["pm", "skill"], force=False)


class TestRemovedHelpers:
    """#4792 §5.7: legacy helpers removed when start_team became a thin shim.

    The sentinel-file write fallbacks (`_write_stop`, `_remove_stop`,
    `_clean_stale_sentinels`) were already removed in §5.2. This cycle also
    removes `_harness_api` and `_discover_harness_port` (squidsquad_cli has
    its own) and the dead `_is_agent_idle` function.
    """

    @pytest.mark.parametrize("name", [
        "_write_stop",
        "_remove_stop",
        "_clean_stale_sentinels",
        "_harness_api",
        "_discover_harness_port",
        "_is_agent_idle",
    ])
    def test_helper_removed(self, name):
        assert not hasattr(start_team, name), (
            f"start_team.{name} should be removed after §5.7 shim conversion"
        )

    def test_no_direct_boot_remote_boot_agent_call(self):
        """cmd_boot must not call boot_remote.boot_agent directly any more —
        all spawning flows through squidsquad_cli → harness API."""
        import inspect
        source = inspect.getsource(start_team)
        # boot_remote is imported for _get_all_roles only
        assert "boot_remote.boot_agent" not in source
        assert "boot_remote._needs_boot" not in source

    def test_no_reboot_agent_kill_fallback(self):
        """The `--force` SIGKILL fallback that imported reboot_agent and
        invoked `_kill_process` directly is gone. Force is now a no-op."""
        import inspect
        source = inspect.getsource(start_team)
        assert "reboot_agent._kill_process" not in source
        assert "reboot_agent._read_claude_pid" not in source


class TestSquidsquadCliPerRoleStart:
    """§5.8 audit: `squidsquad_cli.cmd_start` gained a per-role parameter so
    the start_team shim has something to delegate to."""

    def test_cmd_start_no_role_starts_all(self):
        import squidsquad_cli
        with patch.object(squidsquad_cli, "_discover_harness", return_value=7373), \
             patch.object(squidsquad_cli, "_api_call", return_value={
                 "results": [
                     {"role": "skill", "success": True, "action": "spawned", "message": ""},
                     {"role": "pm", "success": True, "action": "spawned", "message": ""},
                 ]
             }) as api:
            rc = squidsquad_cli.cmd_start()
        assert rc == 0
        api.assert_called_once_with(7373, "POST", "/agents/all/start")

    def test_cmd_start_no_role_returns_1_when_any_agent_fails(self):
        """All-agents start aggregates per-agent success — any failure → 1."""
        import squidsquad_cli
        with patch.object(squidsquad_cli, "_discover_harness", return_value=7373), \
             patch.object(squidsquad_cli, "_api_call", return_value={
                 "results": [
                     {"role": "skill", "success": True, "action": "spawned", "message": ""},
                     {"role": "pm", "success": False, "action": "failed", "message": "boom"},
                 ]
             }):
            rc = squidsquad_cli.cmd_start()
        assert rc == 1

    def test_cmd_start_with_role_targets_single_agent(self):
        import squidsquad_cli
        with patch.object(squidsquad_cli, "_discover_harness", return_value=7373), \
             patch.object(squidsquad_cli, "_api_call",
                          return_value={"success": True, "action": "spawned", "message": ""}) as api:
            rc = squidsquad_cli.cmd_start("skill")
        assert rc == 0
        api.assert_called_once_with(7373, "POST", "/agents/skill/start")

    def test_cmd_start_returns_1_when_role_start_fails(self):
        import squidsquad_cli
        with patch.object(squidsquad_cli, "_discover_harness", return_value=7373), \
             patch.object(squidsquad_cli, "_api_call",
                          return_value={"success": False, "action": "failed", "message": "boom"}):
            rc = squidsquad_cli.cmd_start("skill")
        assert rc == 1
