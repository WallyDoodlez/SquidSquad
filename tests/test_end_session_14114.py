"""#14114 -- "end your session" is now executable.

The event-mode contract told an agent to "end your session" on a non-expiry
Monitor exit, relying on the harness seeing the `claude` PID die. An LLM agent
cannot end its own process (#13077): ending the turn left the PID alive with
intent=running, so the session sat deaf and was never respawned.

`cycle.py end-session` asks the harness to FORCE-restart the caller's OWN agent
(`POST /agents/<alias>/restart?force=true`). The harness kills the PID
immediately and stamps it as a requested kill, so the #12458 pause guard does
not hold it (#14132) and the next health poll respawns it. Guards: own alias
only (AC1); an operator stop or a deploy is left alone (AC2b); a repeat call
while a respawn is in flight is harmless (AC2c). The instructions now say to
run it, then end the turn (AC3).

Safety: every helper test injects an opener (or drives the harness app
in-process via TestClient). An unmocked call would force-restart a live agent.
"""

import io
import json
import re
import subprocess
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


def _opener(calls, intent="running", post_body=None):
    """Fake urlopen: GET /agents/<alias> returns ``intent``; POST restart
    returns ``post_body`` (default success)."""
    def _open(req, timeout=None):
        calls.append((req.full_url, req.get_method(), timeout))
        if req.get_method() == "GET":
            body = {"intent": intent}
        else:
            body = post_body if post_body is not None else {"success": True}
        return _Resp(json.dumps(body).encode("utf-8"))
    return _open


@pytest.fixture
def as_skill(monkeypatch):
    monkeypatch.setenv("SQUIDSQUAD_ROLE", "skill")


class TestEndSessionHelper:
    def test_posts_force_restart_for_own_alias(self, as_skill, capsys):
        calls = []
        assert cycle.end_session(port=7373, opener=_opener(calls)) == 0
        assert calls == [
            ("http://127.0.0.1:7373/agents/skill", "GET", 10),
            ("http://127.0.0.1:7373/agents/skill/restart?force=true", "POST", 10),
        ]
        assert "End your turn now" in capsys.readouterr().out

    def test_matching_role_arg_accepted(self, as_skill):
        calls = []
        assert cycle.end_session("skill", port=9, opener=_opener(calls)) == 0
        assert calls[-1][1] == "POST"

    def test_foreign_role_refused_no_http(self, as_skill, capsys):
        """AC1: a teammate can never be targeted."""
        calls = []
        assert cycle.end_session("dm", port=9, opener=_opener(calls)) == 2
        assert calls == []
        assert "only your own agent" in capsys.readouterr().err

    def test_no_env_role_fails_no_http(self, monkeypatch, capsys):
        monkeypatch.delenv("SQUIDSQUAD_ROLE", raising=False)
        calls = []
        assert cycle.end_session("skill", port=9, opener=_opener(calls)) == 1
        assert calls == []
        assert "SQUIDSQUAD_ROLE" in capsys.readouterr().err

    def test_unreachable_harness_single_attempt(self, as_skill, capsys):
        """AC2a: clear message, non-zero exit, no retry loop."""
        attempts = []

        def boom(req, timeout=None):
            attempts.append(req.full_url)
            raise urllib.error.URLError("refused")
        assert cycle.end_session(port=9, opener=boom) == 1
        assert len(attempts) == 1
        out = capsys.readouterr().out
        assert "Harness unreachable" in out and "end your turn" in out

    @pytest.mark.parametrize("intent", ["stopping", "stopped", "deploying"])
    def test_hands_off_intents_do_not_restart(self, as_skill, intent, capsys):
        """AC2b: an operator stop wins (and a deploy owns its own respawn)."""
        calls = []
        assert cycle.end_session(port=9, opener=_opener(calls, intent)) == 0
        assert [c[1] for c in calls] == ["GET"]
        assert "Not restarting" in capsys.readouterr().out

    def test_refused_restart_reported(self, as_skill, capsys):
        calls = []
        rc = cycle.end_session(port=9, opener=_opener(
            calls, post_body={"success": False,
                              "message": "no-auto-reboot active"}))
        assert rc == 1
        assert "refused" in capsys.readouterr().out

    def test_port_discovered_when_not_given(self, as_skill):
        calls = []
        with mock.patch("event_poll._discover_port", return_value=4321):
            cycle.end_session(opener=_opener(calls))
        assert calls[0][0].startswith("http://127.0.0.1:4321/")

    def test_cli_passes_optional_role(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["cycle.py", "end-session"])
        with mock.patch("cycle.end_session", return_value=0) as es:
            with pytest.raises(SystemExit) as ex:
                cycle.main()
        es.assert_called_once_with(None)
        assert ex.value.code == 0


class TestEndSessionAgainstRealEndpoint:
    """The helper's requests are honoured by the real harness routes."""

    @pytest.fixture
    def harness_env(self, tmp_path, monkeypatch):
        from fastapi.testclient import TestClient
        import harness
        from harness import AgentState, app, state

        monkeypatch.setenv("SQUIDSQUAD_ROLE", "skill")
        client = TestClient(app, raise_server_exceptions=False)

        def via_testclient(req, timeout=None):
            path = req.full_url.split("127.0.0.1:7373", 1)[1]
            r = (client.get(path) if req.get_method() == "GET"
                 else client.post(path))
            return _Resp(r.content)

        state.agents.clear()
        a = AgentState("skill", str(tmp_path))
        a.claude_pid = 4321
        a.last_spawn_at = 1.0
        a.waiting_since = 2.0
        state.set_agent("skill", a)
        pid_alive = {"alive": True}
        with mock.patch("harness._NO_AUTO_REBOOT", False), \
             mock.patch("harness.boot_remote") as boot, \
             mock.patch.object(state, "save_state"), \
             mock.patch("harness.reboot_agent._read_claude_pid",
                        side_effect=lambda *a_: (4321, pid_alive["alive"])), \
             mock.patch("harness.reboot_agent._kill_process") as kill, \
             mock.patch("harness._log"):
            boot._get_all_roles.return_value = ["skill"]
            boot._get_clone_path.return_value = str(tmp_path)
            yield {"opener": via_testclient, "kill": kill, "state": state,
                   "boot": boot, "pid_alive": pid_alive,
                   "AgentState": AgentState}
        harness.state.agents.clear()

    def test_force_restart_kills_and_stamps(self, harness_env):
        """AC1: own agent force-killed, marked as a requested kill."""
        e = harness_env
        assert cycle.end_session(port=7373, opener=e["opener"]) == 0
        e["kill"].assert_called_once_with(4321)
        after = e["state"].get_agent("skill")
        assert after.intent == e["AgentState"].INTENT_RESTARTING
        assert after.operator_force_death() is True

    def test_double_call_is_harmless(self, harness_env):
        """AC2c: a second call while the respawn is in flight kills nothing,
        spawns nothing, and keeps the requested-kill marker (so the #14132
        pause bypass still applies to the pending respawn)."""
        e = harness_env
        assert cycle.end_session(port=7373, opener=e["opener"]) == 0
        marker = e["state"].get_agent("skill").operator_force_at
        e["pid_alive"]["alive"] = False          # first call's kill landed
        assert cycle.end_session(port=7373, opener=e["opener"]) == 0
        e["kill"].assert_called_once_with(4321)  # not killed again
        e["boot"].boot_agent.assert_not_called()  # endpoint never spawns
        after = e["state"].get_agent("skill")
        assert after.operator_force_at == marker
        assert after.operator_force_death() is True

    def test_operator_stop_wins(self, harness_env):
        """AC2b against the real GET route: intent=stopping -> no restart."""
        e = harness_env
        e["state"].get_agent("skill").intent = e["AgentState"].INTENT_STOPPING
        assert cycle.end_session(port=7373, opener=e["opener"]) == 0
        e["kill"].assert_not_called()
        assert (e["state"].get_agent("skill").intent
                == e["AgentState"].INTENT_STOPPING)


class TestInstructionsUseEndSession:
    CONTRACT = REPO / "references" / "sub-skills" / "common-events" / "event-mode-contract.md"
    WORKFLOW = REPO / "references" / "sub-skills" / "common-events" / "event-driven-workflow.md"
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
        assert "health poller sees your session die" not in section

    def test_workflow_error_handling_runs_end_session(self):
        text = self.WORKFLOW.read_text(encoding="utf-8")
        section = text[text.index("### Error handling"):]
        section = section[:section.index("### Context pressure")]
        assert "cycle.py end-session" in section

    def test_l1_instructions_run_end_session(self):
        text = self.L1.read_text(encoding="utf-8")
        rule = text[text.index("**Any other Monitor exit"):]
        rule = rule[:rule.index("#### 6.")]
        assert "python references/scripts/cycle.py end-session" in rule
        assert "your exit IS the signal" not in rule

    @pytest.mark.parametrize("doc", ["docs/AGENT-RUNTIME.md",
                                     "docs/HARNESS-ARCH.md"])
    def test_arch_docs_name_end_session(self, doc):
        assert "cycle.py end-session" in (REPO / doc).read_text(encoding="utf-8")

    def test_no_residual_drift(self):
        """AC3: the old 'the exit itself triggers the respawn' wording is gone."""
        out = subprocess.run(
            ["git", "grep", "-n", "-i",
             "-e", "sees the .claude. pid die",
             "-e", "exit is the signal",
             "-e", "exiting IS the signal",
             "--", "docs/", "references/", ":!docs/archive"],
            cwd=REPO, capture_output=True, text=True, encoding="utf-8")
        assert out.stdout.strip() == "", out.stdout
