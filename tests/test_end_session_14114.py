"""#14114 -- "end your session" is now executable.

The event-mode contract told an agent to "end your session" on a non-expiry
Monitor exit, relying on the harness seeing the `claude` PID die. An LLM agent
cannot end its own process (#13077): ending the turn left the PID alive with
intent=running, so the session sat deaf and was never respawned.

`cycle.py end-session` asks the harness to FORCE-restart the caller's own agent
(`POST /agents/<role>/restart?force=true`). The harness kills the PID
immediately and stamps it as a requested kill, so the #12458 pause guard does
not hold it (#14132) and the next health poll respawns it. The instructions now
say to run it, then end the turn.
"""

import io
import json
import sys
import urllib.error
from pathlib import Path
from unittest import mock

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "references" / "scripts"))

import cycle  # noqa: E402


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _opener(body, calls):
    def _open(req, timeout=None):
        calls.append((req.full_url, req.get_method(), timeout))
        return _Resp(json.dumps(body).encode("utf-8"))
    return _open


class TestEndSessionHelper:
    def test_posts_force_restart_for_own_role(self, capsys):
        calls = []
        rc = cycle.end_session("skill", port=7373,
                               opener=_opener({"success": True}, calls))
        assert rc == 0
        assert calls == [("http://127.0.0.1:7373/agents/skill/restart?force=true",
                          "POST", 10)]
        assert "End your turn now" in capsys.readouterr().out

    def test_role_defaults_to_env(self, monkeypatch):
        monkeypatch.setenv("SQUIDSQUAD_ROLE", "dm")
        calls = []
        assert cycle.end_session(port=9, opener=_opener({"success": True},
                                                        calls)) == 0
        assert "/agents/dm/restart?force=true" in calls[0][0]

    def test_no_role_fails(self, monkeypatch, capsys):
        monkeypatch.delenv("SQUIDSQUAD_ROLE", raising=False)
        assert cycle.end_session(port=9, opener=_opener({}, [])) == 1
        assert "needs a role" in capsys.readouterr().err

    def test_unreachable_harness_says_end_turn(self, capsys):
        def boom(req, timeout=None):
            raise urllib.error.URLError("refused")
        assert cycle.end_session("skill", port=9, opener=boom) == 1
        out = capsys.readouterr().out
        assert "Harness unreachable" in out and "end your turn" in out

    def test_refused_restart_reported(self, capsys):
        calls = []
        rc = cycle.end_session("skill", port=9, opener=_opener(
            {"success": False, "message": "no-auto-reboot active"}, calls))
        assert rc == 1
        assert "refused" in capsys.readouterr().out

    def test_port_discovered_when_not_given(self):
        calls = []
        with mock.patch("event_poll._discover_port", return_value=4321):
            cycle.end_session("skill", opener=_opener({"success": True}, calls))
        assert calls[0][0].startswith("http://127.0.0.1:4321/")

    def test_cli_exit_code(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["cycle.py", "end-session", "skill"])
        with mock.patch("cycle.end_session", return_value=0) as es:
            with pytest.raises(SystemExit) as ex:
                cycle.main()
        es.assert_called_once_with("skill")
        assert ex.value.code == 0


class TestEndSessionAgainstRealEndpoint:
    """The helper's request is honoured by the real /agents/{role}/restart
    route: an immediate force kill with the requested-kill marker stamped."""

    def test_force_restart_kills_and_stamps(self, tmp_path):
        from fastapi.testclient import TestClient
        import harness
        from harness import AgentState, app, state

        client = TestClient(app, raise_server_exceptions=False)

        def via_testclient(req, timeout=None):
            path = req.full_url.split("127.0.0.1:7373", 1)[1]
            r = client.post(path)
            return _Resp(r.content)

        state.agents.clear()
        a = AgentState("skill", str(tmp_path))
        a.claude_pid = 4321
        a.last_spawn_at = 1.0
        state.set_agent("skill", a)
        with mock.patch("harness._NO_AUTO_REBOOT", False), \
             mock.patch("harness.boot_remote") as boot, \
             mock.patch.object(state, "save_state"), \
             mock.patch("harness.reboot_agent._read_claude_pid",
                        return_value=(4321, True)), \
             mock.patch("harness.reboot_agent._kill_process") as kill, \
             mock.patch("harness._log"):
            boot._get_all_roles.return_value = ["skill"]
            boot._get_clone_path.return_value = str(tmp_path)
            rc = cycle.end_session("skill", port=7373, opener=via_testclient)
        assert rc == 0
        kill.assert_called_once_with(4321)
        after = state.get_agent("skill")
        assert after.intent == AgentState.INTENT_RESTARTING
        assert after.operator_force_death() is True
        harness.state.agents.clear()


class TestInstructionsUseEndSession:
    CONTRACT = REPO / "references" / "sub-skills" / "common-events" / "event-mode-contract.md"
    L1 = REPO / "references" / "roles" / "instructions.md"

    def test_contract_monitor_exit_rule_runs_end_session(self):
        text = self.CONTRACT.read_text(encoding="utf-8")
        rule = text[text.index("**Anything else — end your session right away.**"):]
        rule = rule[:rule.index("---")]
        assert "python references/scripts/cycle.py end-session" in rule
        assert "end your turn" in rule

    def test_contract_harness_loss_paths_run_end_session(self):
        text = self.CONTRACT.read_text(encoding="utf-8")
        section = text[text.index("### Harness-Loss Recovery"):]
        assert section.count("cycle.py end-session") >= 2
        # The false mechanism ("PID dies on its own -> respawn") is gone.
        assert "health poller sees your session die" not in section

    def test_l1_instructions_run_end_session(self):
        text = self.L1.read_text(encoding="utf-8")
        rule = text[text.index("**Any other Monitor exit"):]
        rule = rule[:rule.index("#### 6.")]
        assert "python references/scripts/cycle.py end-session" in rule
        assert "your exit IS the signal" not in rule
