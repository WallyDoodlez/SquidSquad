"""Tests for references/scripts/watchdog.py — standalone agent lifecycle supervisor."""

import json
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import watchdog
import health_check


class TestReadContextThreshold:
    def test_reads_from_config(self, tmp_path):
        config = tmp_path / "config.md"
        config.write_text("## Context Pressure\n\n- **Threshold**: 80\n")
        with patch.object(watchdog, "CONFIG_MD", config):
            assert watchdog._read_context_threshold() == 80

    def test_missing_config_returns_default(self, tmp_path):
        with patch.object(watchdog, "CONFIG_MD", tmp_path / "missing"):
            assert watchdog._read_context_threshold() == 70


class TestReadIntervalMinutes:
    def test_reads_from_config(self, tmp_path):
        config = tmp_path / "config.md"
        config.write_text("## Iteration Interval\n\n- **Minutes**: 45\n")
        with patch.object(watchdog, "CONFIG_MD", config):
            assert watchdog._read_interval_minutes() == 45

    def test_missing_config_returns_default(self, tmp_path):
        with patch.object(watchdog, "CONFIG_MD", tmp_path / "missing"):
            assert watchdog._read_interval_minutes() == 30


class TestGetAllRoles:
    def test_includes_pm_always(self, tmp_path):
        config = tmp_path / "config.md"
        config.write_text("## Agents\n\n- **Dev Agents**: skill\n")
        with patch.object(watchdog, "CONFIG_MD", config):
            roles = watchdog._get_all_roles()
        assert "pm" in roles

    def test_includes_dev_agents(self, tmp_path):
        config = tmp_path / "config.md"
        config.write_text("## Agents\n\n- **Dev Agents**: skill, boot\n")
        with patch.object(watchdog, "CONFIG_MD", config):
            roles = watchdog._get_all_roles()
        assert "skill" in roles
        assert "boot" in roles

    def test_includes_dm_when_present(self, tmp_path):
        config = tmp_path / "config.md"
        config.write_text(
            "## Agents\n\n- **Dev Agents**: skill\n- **DM**: present\n"
        )
        with patch.object(watchdog, "CONFIG_MD", config):
            roles = watchdog._get_all_roles()
        assert "dm" in roles

    def test_includes_qa_when_present(self, tmp_path):
        config = tmp_path / "config.md"
        config.write_text(
            "## Agents\n\n- **Dev Agents**: skill\n- **QA**: always present\n"
        )
        with patch.object(watchdog, "CONFIG_MD", config):
            roles = watchdog._get_all_roles()
        assert "qa" in roles

    def test_missing_config_returns_pm_only(self, tmp_path):
        with patch.object(watchdog, "CONFIG_MD", tmp_path / "missing"):
            roles = watchdog._get_all_roles()
        assert roles == ["pm"]


class TestReadContextPressure:
    def test_reads_pressure_value(self, tmp_path):
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        (squid / "context-pressure").write_text("42")
        assert watchdog._read_context_pressure("skill", tmp_path) == 42

    def test_returns_none_when_missing(self, tmp_path):
        assert watchdog._read_context_pressure("skill", tmp_path) is None

    def test_returns_none_on_invalid_content(self, tmp_path):
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        (squid / "context-pressure").write_text("not-a-number")
        assert watchdog._read_context_pressure("skill", tmp_path) is None


class TestReadCurrentState:
    def test_reads_idle_state(self, tmp_path):
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        (squid / "current-state").write_text("idle|")
        phase, desc = watchdog._read_current_state("skill", tmp_path)
        assert phase == "idle"
        assert desc == ""

    def test_reads_active_state(self, tmp_path):
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        (squid / "current-state").write_text("implementing|dev-agent — #42")
        phase, desc = watchdog._read_current_state("skill", tmp_path)
        assert phase == "implementing"
        assert desc == "dev-agent — #42"

    def test_returns_empty_when_missing(self, tmp_path):
        phase, desc = watchdog._read_current_state("skill", tmp_path)
        assert phase == ""
        assert desc == ""


class TestIsCycleComplete:
    def test_idle_means_complete(self, tmp_path):
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        (squid / "current-state").write_text("idle|")
        assert watchdog._is_cycle_complete("skill", tmp_path) is True

    def test_implementing_means_not_complete(self, tmp_path):
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        (squid / "current-state").write_text("implementing|#42")
        assert watchdog._is_cycle_complete("skill", tmp_path) is False


class TestCheckAndAct:
    """Integration tests for the main watchdog logic."""

    def _setup_agent(self, tmp_path, role, health_status="alive",
                     pressure=None, state="idle|", pid=12345):
        """Set up a fake agent directory for testing."""
        squid = tmp_path / ".squidsquad" / role
        squid.mkdir(parents=True, exist_ok=True)
        if health_status:
            (squid / ".health").write_text(health_status)
        if pressure is not None:
            (squid / "context-pressure").write_text(str(pressure))
        if state:
            (squid / "current-state").write_text(state)
        if pid:
            (squid / ".pid").write_text(str(pid))
        # Create CLAUDE.md
        (squid / "CLAUDE.md").write_text("# Test agent")

    @patch.object(watchdog.boot_remote, "_parse_local_config")
    @patch.object(watchdog.health_check, "check_agent_health")
    def test_healthy_agent_no_action(self, mock_health, mock_config, tmp_path):
        mock_config.return_value = {"skill": tmp_path}
        mock_health.return_value = {
            "role": "skill",
            "health": "healthy",
            "reason": "all good",
        }
        self._setup_agent(tmp_path, "skill", pressure=10)

        with patch.object(watchdog, "REPO_ROOT", tmp_path), \
             patch.object(watchdog, "CONFIG_MD", tmp_path / "config.md"):
            (tmp_path / "config.md").write_text(
                "## Agents\n- **Dev Agents**: skill\n"
                "## Context Pressure\n- **Threshold**: 70\n"
                "## Iteration Interval\n- **Minutes**: 30\n"
            )
            actions = watchdog.check_and_act(roles=["skill"])

        assert len(actions) == 1
        assert actions[0]["action"] == "healthy"

    @patch.object(watchdog.boot_remote, "_parse_local_config")
    @patch.object(watchdog.health_check, "check_agent_health")
    @patch.object(watchdog.boot_remote, "boot_agent")
    def test_dead_agent_gets_booted(self, mock_boot, mock_health, mock_config, tmp_path):
        mock_config.return_value = {"skill": tmp_path}
        mock_health.return_value = {
            "role": "skill",
            "health": "stalled",
            "reason": ".health=dead",
        }
        mock_boot.return_value = {
            "role": "skill",
            "action": "spawn",
            "success": True,
            "message": "spawned",
        }

        with patch.object(watchdog, "REPO_ROOT", tmp_path), \
             patch.object(watchdog, "CONFIG_MD", tmp_path / "config.md"), \
             patch.object(watchdog, "WATCHDOG_LOG", tmp_path / "log.txt"):
            (tmp_path / "config.md").write_text(
                "## Agents\n- **Dev Agents**: skill\n"
            )
            actions = watchdog.check_and_act(roles=["skill"])

        assert len(actions) == 1
        assert actions[0]["action"] == "boot"
        mock_boot.assert_called_once_with("skill")

    @patch.object(watchdog.boot_remote, "_parse_local_config")
    @patch.object(watchdog.health_check, "check_agent_health")
    def test_stopped_agent_skipped(self, mock_health, mock_config, tmp_path):
        mock_config.return_value = {"skill": tmp_path}
        mock_health.return_value = {
            "role": "skill",
            "health": "stopped",
            "reason": ".stop sentinel",
        }

        with patch.object(watchdog, "REPO_ROOT", tmp_path), \
             patch.object(watchdog, "CONFIG_MD", tmp_path / "config.md"):
            (tmp_path / "config.md").write_text(
                "## Agents\n- **Dev Agents**: skill\n"
            )
            actions = watchdog.check_and_act(roles=["skill"])

        assert len(actions) == 1
        assert actions[0]["action"] == "skip"

    @patch.object(watchdog, "_kill_agent")
    @patch.object(watchdog.boot_remote, "_parse_local_config")
    @patch.object(watchdog.health_check, "check_agent_health")
    def test_high_pressure_idle_agent_restarted(
        self, mock_health, mock_config, mock_kill, tmp_path
    ):
        mock_config.return_value = {"skill": tmp_path}
        mock_health.return_value = {
            "role": "skill",
            "health": "healthy",
            "reason": "all good",
        }
        mock_kill.return_value = True

        self._setup_agent(tmp_path, "skill", pressure=85, state="idle|", pid=99999)

        with patch.object(watchdog, "REPO_ROOT", tmp_path), \
             patch.object(watchdog, "CONFIG_MD", tmp_path / "config.md"), \
             patch.object(watchdog, "WATCHDOG_LOG", tmp_path / "log.txt"):
            (tmp_path / "config.md").write_text(
                "## Agents\n- **Dev Agents**: skill\n"
                "## Context Pressure\n- **Threshold**: 70\n"
                "## Iteration Interval\n- **Minutes**: 30\n"
            )
            actions = watchdog.check_and_act(roles=["skill"])

        assert len(actions) == 1
        assert actions[0]["action"] == "restart"
        assert "context pressure" in actions[0]["detail"]
        mock_kill.assert_called_once_with(99999)

    @patch.object(watchdog.boot_remote, "_parse_local_config")
    @patch.object(watchdog.health_check, "check_agent_health")
    def test_high_pressure_busy_agent_pending(
        self, mock_health, mock_config, tmp_path
    ):
        mock_config.return_value = {"skill": tmp_path}
        mock_health.return_value = {
            "role": "skill",
            "health": "healthy",
            "reason": "all good",
        }

        self._setup_agent(
            tmp_path, "skill", pressure=85, state="implementing|#42", pid=99999
        )

        with patch.object(watchdog, "REPO_ROOT", tmp_path), \
             patch.object(watchdog, "CONFIG_MD", tmp_path / "config.md"):
            (tmp_path / "config.md").write_text(
                "## Agents\n- **Dev Agents**: skill\n"
                "## Context Pressure\n- **Threshold**: 70\n"
                "## Iteration Interval\n- **Minutes**: 30\n"
            )
            actions = watchdog.check_and_act(roles=["skill"])

        assert len(actions) == 1
        assert actions[0]["action"] == "pending-restart"
        assert "waiting for cycle" in actions[0]["detail"]


class TestRunOnce:
    @patch.object(watchdog, "check_and_act")
    def test_returns_actions_and_flag(self, mock_check):
        mock_check.return_value = [
            {"role": "skill", "action": "healthy", "detail": "ok"},
        ]
        actions, any_intervention = watchdog.run_once()
        assert len(actions) == 1
        assert any_intervention is False

    @patch.object(watchdog, "check_and_act")
    def test_intervention_flag_when_boot(self, mock_check):
        mock_check.return_value = [
            {"role": "skill", "action": "boot", "detail": "spawned"},
        ]
        actions, any_intervention = watchdog.run_once()
        assert any_intervention is True

    @patch.object(watchdog, "check_and_act")
    def test_intervention_flag_when_restart(self, mock_check):
        mock_check.return_value = [
            {"role": "skill", "action": "restart", "detail": "pressure"},
        ]
        actions, any_intervention = watchdog.run_once()
        assert any_intervention is True


class TestLog:
    def test_log_writes_to_file(self, tmp_path):
        log_file = tmp_path / "watchdog-log.txt"
        with patch.object(watchdog, "WATCHDOG_LOG", log_file):
            watchdog._log("test message")
        content = log_file.read_text(encoding="utf-8")
        assert "test message" in content
        assert "INFO" in content

    def test_trim_log_keeps_max_lines(self, tmp_path):
        log_file = tmp_path / "watchdog-log.txt"
        lines = [f"line {i}\n" for i in range(600)]
        log_file.write_text("".join(lines), encoding="utf-8")
        with patch.object(watchdog, "WATCHDOG_LOG", log_file), \
             patch.object(watchdog, "MAX_LOG_LINES", 100):
            watchdog._trim_log()
        remaining = log_file.read_text(encoding="utf-8").splitlines()
        assert len(remaining) == 100


class TestMainCLI:
    @patch.object(watchdog, "run_once")
    def test_once_flag(self, mock_run):
        mock_run.return_value = (
            [{"role": "skill", "action": "healthy", "detail": "ok"}],
            False,
        )
        with patch.object(watchdog, "SQUIDSQUAD_DIR", Path(".")):
            with patch("sys.argv", ["watchdog.py", "--once"]):
                result = watchdog.main()
        assert result == 0

    @patch.object(watchdog, "run_once")
    def test_json_flag(self, mock_run, capsys):
        mock_run.return_value = (
            [{"role": "skill", "action": "boot", "detail": "spawned"}],
            True,
        )
        with patch.object(watchdog, "SQUIDSQUAD_DIR", Path(".")):
            with patch("sys.argv", ["watchdog.py", "--json"]):
                result = watchdog.main()
        assert result == 1
        output = json.loads(capsys.readouterr().out)
        assert output["any_intervention"] is True

    def test_missing_squidsquad_dir(self, tmp_path):
        with patch.object(watchdog, "SQUIDSQUAD_DIR", tmp_path / "nope"):
            with patch("sys.argv", ["watchdog.py", "--once"]):
                result = watchdog.main()
        assert result == 2
