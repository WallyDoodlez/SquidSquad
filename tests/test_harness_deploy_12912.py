"""#12912 (deploy-signal recompose model) — S2 intent-sequencing tests.

Covers AC9: the harness sets intent=deploying before the agent halts so a
deploy-halt PID-death is NOT misread as a crash + auto-respawned out of order.

The health poller is an async loop that is impractical to drive directly, so
its deploy-halt handling is asserted via source inspection (the established
pattern in test_harness.py::test_ack_stop_confirmed_guarded_by_stopping_intent).
The load-state reset is exercised behaviorally.
"""

import inspect
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import sys

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from harness import AgentState, HarnessState, receive_event, HarnessState as _HS  # noqa: E402


class TestIntentDeployingConstant(unittest.TestCase):
    def test_constant_exists_and_value(self):
        self.assertTrue(hasattr(AgentState, "INTENT_DEPLOYING"))
        self.assertEqual(AgentState.INTENT_DEPLOYING, "deploying")

    def test_deploying_excluded_from_should_reboot(self):
        """AC9: a deploy-halt death must never satisfy should_reboot. The
        respawn-eligible intent set is RUNNING/RESTARTING only — DEPLOYING is
        not in it, so the health poller cannot auto-respawn a deploy-halt."""
        src = inspect.getsource(_HS)  # health poller lives on HarnessState
        # Locate the should_reboot assignment and assert DEPLOYING is absent.
        idx = src.find("should_reboot = agent.intent in (")
        self.assertNotEqual(idx, -1, "should_reboot intent set not found")
        block = src[idx:idx + 200]
        self.assertIn("INTENT_RUNNING", block)
        self.assertIn("INTENT_RESTARTING", block)
        self.assertNotIn("INTENT_DEPLOYING", block,
                         "DEPLOYING must NOT be respawn-eligible (AC9)")


class TestHealthPollStatusSettling(unittest.TestCase):
    def test_deploying_death_settles_to_deploying_not_stalled(self):
        """A dead agent with intent=DEPLOYING settles to status='deploying'
        (HARNESS-ARCH §7.1.1), keeping it out of the is_dead crash set."""
        src = inspect.getsource(_HS)
        self.assertIn("INTENT_DEPLOYING", src)
        # The settling branch maps DEPLOYING -> "deploying" within the deploy
        # window, and recovers to "running" past it (Finding 2 timeout).
        idx = src.find("agent.intent == AgentState.INTENT_DEPLOYING")
        self.assertNotEqual(idx, -1)
        block = src[idx:idx + 2400]
        self.assertIn('agent.status = "deploying"', block)
        self.assertIn("_DEPLOY_WINDOW_SECONDS", block)
        self.assertIn('agent.status = "running"', block)


class TestLoadStateResetsDeploying(unittest.TestCase):
    def test_load_state_resets_deploying_to_running(self):
        """#12912: a restored DEPLOYING intent (interrupted deploy across a
        harness restart) resets to RUNNING with the clock cleared, so the agent
        respawns normally on its existing committed CLAUDE.md."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".harness-state.json"
            state_file.write_text(json.dumps({
                "harness_pid": 1, "start_time": 0.0, "port": 7373,
                "agents": {
                    "skill": {"intent": "deploying",
                              "intent_set_at": 100.0,
                              "status": "deploying", "boot_time": None,
                              "clone_path": "", "claude_pid": 4321,
                              "terminal_pid": None},
                },
            }), encoding="utf-8")
            with patch("harness.HARNESS_STATE_FILE", state_file), \
                 patch("harness._log"), \
                 patch("harness.time.time", return_value=9999.0):
                hs = HarnessState()
                hs.load_state()
                loaded = hs.get_agent("skill")
                self.assertEqual(loaded.intent, AgentState.INTENT_RUNNING)
                self.assertIsNone(loaded.intent_set_at)


class TestAckStopDeployHalted(unittest.TestCase):
    def test_deploy_halted_branch_exists(self):
        """The ack-stop handler must branch on result=='deploy-halted',
        distinct from the stop-confirmed branch."""
        src = inspect.getsource(receive_event)
        self.assertIn('ack_payload.get("result") == "deploy-halted"', src)

    def test_deploy_halted_sets_deploying_status_and_intent(self):
        """The deploy-halted branch records the halt: status='deploying' and
        intent=DEPLOYING (defensive if the emit side didn't set it)."""
        src = inspect.getsource(receive_event)
        idx = src.find('"deploy-halted"')
        self.assertNotEqual(idx, -1)
        block = src[idx:idx + 2400]
        self.assertIn('agent.status = "deploying"', block)
        self.assertIn("INTENT_DEPLOYING", block)
        # DS Finding 3: reboot_blocked_until armed in the ack-stop handler.
        self.assertIn("reboot_blocked_until", block)


class TestRebootAffectedAgentsEmitsDeploySignal(unittest.TestCase):
    """S3 (AC4/AC5, closes #12397): _reboot_affected_agents is the deploy-signal
    emitter — it sets intent=DEPLOYING and emits a deploy-signal to each affected
    alias instead of force-restarting them directly."""

    def _make_agent(self, intent, status="running"):
        a = AgentState("skill", "")
        a.intent = intent
        a.status = status
        return a

    def test_emits_deploy_signal_to_affected_running_agent(self):
        import harness
        agent = self._make_agent(AgentState.INTENT_RUNNING)

        emitted = []

        class _FakeState:
            def get_agent(self, role):
                return agent if role == "skill" else None

            def set_agent(self, role, a):
                pass

            def save_state(self):
                pass

        class _FakeDiff:
            returncode = 0
            stdout = ".squidsquad/skill/CLAUDE.md\n"

        with patch.object(harness, "_NO_AUTO_REBOOT", False), \
             patch.object(harness, "state", _FakeState()), \
             patch.object(harness, "subprocess") as msub, \
             patch.object(harness, "_emit_event",
                          side_effect=lambda *a, **k: emitted.append((a, k))), \
             patch.object(harness, "_log"), \
             patch.object(harness, "time") as mtime:
            msub.run.return_value = _FakeDiff()
            mtime.time.return_value = 123.0
            harness._reboot_affected_agents(99, ["references/roles/instructions.md"])

        # Intent moved to DEPLOYING (sequencing), not RESTARTING.
        self.assertEqual(agent.intent, AgentState.INTENT_DEPLOYING)
        # Exactly one deploy-signal emitted, scoped to the affected alias.
        self.assertEqual(len(emitted), 1)
        args, kwargs = emitted[0]
        self.assertEqual(args[0], "deploy-signal")
        self.assertEqual(kwargs["payload"]["target_alias"], "skill")
        self.assertEqual(kwargs["payload"]["event_type"], "deploy-signal")
        self.assertEqual(kwargs["payload"]["event_context"], "deploy-signal")

    def test_crash_looping_agent_not_signaled(self):
        """DS iter-3 Finding 1: an affected agent that is NOT alive (e.g.
        crash-looping, intent still RUNNING) must NOT be flipped to DEPLOYING —
        that would lock it out of crash-loop recovery."""
        import harness
        agent = self._make_agent(AgentState.INTENT_RUNNING, status="crash-looping")
        emitted = []

        class _FakeState:
            def get_agent(self, role):
                return agent if role == "skill" else None

            def set_agent(self, role, a):
                pass

            def save_state(self):
                pass

        class _FakeDiff:
            returncode = 0
            stdout = ".squidsquad/skill/CLAUDE.md\n"

        with patch.object(harness, "_NO_AUTO_REBOOT", False), \
             patch.object(harness, "state", _FakeState()), \
             patch.object(harness, "subprocess") as msub, \
             patch.object(harness, "_emit_event",
                          side_effect=lambda *a, **k: emitted.append((a, k))), \
             patch.object(harness, "_log"), \
             patch.object(harness, "time") as mtime:
            msub.run.return_value = _FakeDiff()
            mtime.time.return_value = 123.0
            harness._reboot_affected_agents(99, ["references/roles/instructions.md"])

        self.assertEqual(emitted, [])                              # not signaled
        self.assertEqual(agent.intent, AgentState.INTENT_RUNNING)  # intent untouched

    def test_no_auto_reboot_suppresses_emit(self):
        """HARNESS-ARCH §7.6: under --no-auto-reboot the emit is skipped."""
        import harness
        emitted = []
        with patch.object(harness, "_NO_AUTO_REBOOT", True), \
             patch.object(harness, "_emit_event",
                          side_effect=lambda *a, **k: emitted.append(a)), \
             patch.object(harness, "_log"):
            harness._reboot_affected_agents(99, ["references/roles/instructions.md"])
        self.assertEqual(emitted, [])

    def test_no_direct_restart_intent_in_emitter(self):
        """The emitter must not set INTENT_RESTARTING (that was the old path)."""
        src = inspect.getsource(receive_event.__globals__["_reboot_affected_agents"])
        self.assertIn("INTENT_DEPLOYING", src)
        self.assertIn("deploy-signal", src)
        self.assertNotIn("INTENT_RESTARTING", src)


class _CP:
    """Minimal CompletedProcess stand-in."""
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class _DeployFakeState:
    def __init__(self, agent):
        self._agent = agent
        self.checksum = None

    def get_agent(self, role):
        return self._agent

    def set_agent(self, role, a):
        self._agent = a

    def save_state(self):
        pass

    def set_last_compose_checksum(self, c):
        self.checksum = c


class TestRunDeploySequence(unittest.TestCase):
    """S4 (AC8 / §11) + DS-12912 Findings 1 & 2: the per-clone pull-first deploy
    sequence advances the cursor past the deploy-signal (AC4 guard) and respawns
    the agent explicitly."""

    def _run(self, git_router, compose_rc=0, staged=True, event_id="evt-123"):
        import harness
        agent = AgentState("skill", "")
        agent.intent = AgentState.INTENT_DEPLOYING
        fake_state = _DeployFakeState(agent)
        emitted = []
        bumped = []
        respawns = []
        cursor = []

        class _FakeLifecycle:
            def advance_cursor(self, role, eid):
                cursor.append((role, eid))
                return "advanced"

        import config as _cfg
        with patch.object(harness.boot_remote, "_get_clone_path", return_value="/tmp/clone"), \
             patch.object(_cfg, "get_alias", return_value="skill"), \
             patch.object(harness, "state", fake_state), \
             patch.object(harness, "event_lifecycle", _FakeLifecycle()), \
             patch.object(harness, "_git_in_clone", side_effect=git_router), \
             patch.object(harness, "subprocess") as msub, \
             patch.object(harness, "_stage_composed_outputs", return_value=staged), \
             patch.object(harness, "_bump_compose_checksum",
                          side_effect=lambda cp: bumped.append(cp)), \
             patch.object(harness, "_respawn_agent_process",
                          side_effect=lambda r: respawns.append(r) or True), \
             patch.object(harness, "_emit_event",
                          side_effect=lambda *a, **k: emitted.append((a, k))), \
             patch.object(harness, "_log"):
            msub.run.return_value = _CP(returncode=compose_rc)
            msub.TimeoutExpired = Exception
            harness._run_deploy_sequence("skill", event_id)
        return dict(agent=agent, emitted=emitted, bumped=bumped,
                    respawns=respawns, cursor=cursor)

    @staticmethod
    def _all_ok_router(clone_path, args, timeout=120):
        return _CP(returncode=0)

    def test_advances_cursor_past_deploy_signal(self):
        """DS Finding 1 / AC4: cursor advanced past the deploy-signal up front."""
        r = self._run(self._all_ok_router)
        self.assertEqual(r["cursor"], [("skill", "evt-123")])

    def test_success_path_respawns_and_bumps_checksum(self):
        r = self._run(self._all_ok_router)
        self.assertEqual(r["respawns"], ["skill"])   # explicit respawn (Finding 2)
        self.assertEqual(len(r["bumped"]), 1)         # checksum advanced
        self.assertEqual(r["emitted"], [])           # no deploy-error

    def test_no_change_is_clean_success(self):
        r = self._run(self._all_ok_router, staged=False)
        self.assertEqual(r["respawns"], ["skill"])
        self.assertEqual(len(r["bumped"]), 1)
        self.assertEqual(r["emitted"], [])

    def test_deploy_pull_merges_not_ff_only_13158(self):
        """#13158: the deploy-pull must MERGE (--no-rebase), not --ff-only — else
        a diverged main (an unpushed compose commit from a prior push-rejected
        deploy + an advanced origin) FATALS every deploy with deploy-error
        stage=pull. Merge reconciles benign divergence; a real conflict still
        fails the pull → §11 recovery."""
        calls = []

        def _capturing_router(clone_path, args, timeout=120):
            calls.append(list(args))
            return _CP(returncode=0)

        self._run(_capturing_router)
        pull_calls = [a for a in calls if a and a[0] == "pull"]
        self.assertEqual(len(pull_calls), 1, f"expected exactly one pull: {calls}")
        pull = pull_calls[0]
        self.assertIn("--no-rebase", pull, f"deploy-pull must merge (#13158): {pull}")
        self.assertNotIn("--ff-only", pull,
                         f"deploy-pull must not be --ff-only (#13158): {pull}")

    def test_pull_failure_recovers_without_checksum_bump(self):
        def router(clone_path, args, timeout=120):
            if args[0] == "pull":
                return _CP(returncode=1, stderr="non-fast-forward")
            return _CP(returncode=0)
        r = self._run(router)
        self.assertEqual(r["respawns"], ["skill"])    # respawn on existing
        self.assertEqual(r["bumped"], [])             # checksum NOT advanced
        self.assertEqual(r["cursor"], [("skill", "evt-123")])  # cursor still advanced
        self.assertEqual(len(r["emitted"]), 1)        # deploy-error to pm
        args, kwargs = r["emitted"][0]
        self.assertEqual(args[0], "deploy-error")
        self.assertEqual(args[1], "pm")
        self.assertEqual(kwargs["payload"]["stage"], "pull")

    def test_compose_failure_recovers(self):
        r = self._run(self._all_ok_router, compose_rc=1)
        self.assertEqual(r["respawns"], ["skill"])
        self.assertEqual(r["bumped"], [])
        self.assertEqual(len(r["emitted"]), 1)
        self.assertEqual(r["emitted"][0][1]["payload"]["stage"], "compose")

    def test_push_rejection_recovers_immediately(self):
        """DS iter-3 Finding 3: a rejected push goes straight to §11 recovery
        (no futile --ff-only retry of a diverged branch)."""
        pushes = []

        def router(clone_path, args, timeout=120):
            if args[0] == "push":
                pushes.append(1)
                return _CP(returncode=1, stderr="rejected")
            return _CP(returncode=0)
        r = self._run(router)
        self.assertEqual(len(pushes), 1)              # single push, no retry
        self.assertEqual(r["bumped"], [])
        self.assertEqual(len(r["emitted"]), 1)
        self.assertEqual(r["emitted"][0][1]["payload"]["stage"], "push")

    def test_commit_failure_detail_combines_stdout_13176(self):
        """#13176: a non-zero `git commit` whose failure text is on STDOUT (empty
        stderr — e.g. 'nothing to commit, working tree clean') must still produce
        a non-empty, diagnosable deploy-error detail. The old code sourced
        commit.stderr only → empty detail."""
        def router(clone_path, args, timeout=120):
            if args[0] == "commit":
                return _CP(returncode=1,
                           stdout="nothing to commit, working tree clean",
                           stderr="")
            return _CP(returncode=0)
        r = self._run(router)  # staged=True default → reaches the commit step
        self.assertEqual(len(r["emitted"]), 1)
        payload = r["emitted"][0][1]["payload"]
        self.assertEqual(payload["stage"], "commit")
        self.assertTrue(payload["detail"].strip(),
                        "deploy-error detail must not be empty (#13176)")
        self.assertIn("nothing to commit", payload["detail"])


class TestStageComposedOutputs(unittest.TestCase):
    """#13176: _stage_composed_outputs must return True only on an ACTUAL staged
    diff, not merely on `git add` exit 0 — `git add` of an unchanged file exits 0
    while staging nothing, so the old behavior surfaced a benign 'nothing to
    commit' as a deploy-error (empty detail) + left the checksum unadvanced
    (re-trigger risk)."""

    def _make_clone(self, tmpdir, alias="skill"):
        import harness
        d = Path(tmpdir)
        for fn in harness._DEPLOY_COMPOSED_FILES:
            p = d / ".squidsquad" / alias / fn
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("x", encoding="utf-8")
        return d

    def test_returns_false_when_add_ok_but_no_staged_diff(self):
        """The regression: add exits 0 but `git diff --cached --quiet` shows no
        staged diff → False (routes to the caller's clean no-op success path)."""
        import tempfile, harness
        with tempfile.TemporaryDirectory() as tmp:
            clone = self._make_clone(tmp)

            def router(clone_path, args, timeout=120):
                # add → 0; diff --cached --quiet → 0 (no staged diff)
                return _CP(returncode=0)
            with patch.object(harness, "_git_in_clone", side_effect=router), \
                 patch.object(harness, "_log"):
                self.assertFalse(harness._stage_composed_outputs(clone, "skill"))

    def test_returns_true_when_real_staged_diff(self):
        import tempfile, harness
        with tempfile.TemporaryDirectory() as tmp:
            clone = self._make_clone(tmp)

            def router(clone_path, args, timeout=120):
                if args and args[0] == "diff":
                    return _CP(returncode=1)  # staged diff present
                return _CP(returncode=0)
            with patch.object(harness, "_git_in_clone", side_effect=router), \
                 patch.object(harness, "_log"):
                self.assertTrue(harness._stage_composed_outputs(clone, "skill"))

    def test_returns_false_when_no_composed_files_exist(self):
        import tempfile, harness
        with tempfile.TemporaryDirectory() as tmp:
            calls = []

            def router(clone_path, args, timeout=120):
                calls.append(list(args))
                return _CP(returncode=0)
            with patch.object(harness, "_git_in_clone", side_effect=router), \
                 patch.object(harness, "_log"):
                # no composed files created → nothing staged → False, and we never
                # reach the diff probe.
                self.assertFalse(harness._stage_composed_outputs(Path(tmp), "skill"))
            self.assertFalse(any(a and a[0] == "diff" for a in calls))


class TestRespawnAgentProcess(unittest.TestCase):
    """DS-12912 Finding 2: the deploy respawn boots the agent explicitly (the
    health poller never would — status='deploying' is not in is_dead)."""

    def _respawn(self, boot_side_effect, *, claude_pid=None, pid_dies=True,
                 pid_alive=True):
        import harness
        agent = AgentState("skill", "")
        agent.intent = AgentState.INTENT_DEPLOYING
        agent.status = "deploying"
        agent.claude_pid = claude_pid
        emitted = []
        self.killed = []  # PIDs the harness force-killed (#13077)
        with patch.object(harness.boot_remote, "boot_agent", side_effect=boot_side_effect), \
             patch.object(harness.boot_remote, "_is_process_alive", return_value=pid_alive), \
             patch.object(harness.reboot_agent, "_kill_process",
                          side_effect=lambda p: self.killed.append(p)), \
             patch.object(harness, "_await_pid_death", return_value=pid_dies), \
             patch.object(harness, "_emit_event",
                          side_effect=lambda *a, **k: emitted.append((a, k))), \
             patch.object(harness, "state", _DeployFakeState(agent)), \
             patch.object(harness, "_log"):
            ok = harness._respawn_agent_process("skill")
        return agent, ok, emitted

    def test_explicit_boot_and_running_intent(self):
        agent, ok, emitted = self._respawn(
            lambda r: {"success": True, "action": "spawn", "message": "ok"})
        self.assertTrue(ok)
        self.assertEqual(agent.intent, AgentState.INTENT_RUNNING)
        self.assertIsNone(agent.reboot_blocked_until)
        self.assertEqual(agent.status, "starting")
        self.assertEqual(emitted, [])                  # clean spawn → no deploy-error

    def test_boot_agent_raises_leaves_recoverable_error_status(self):
        """DS iter-2 Finding 1: boot_agent raising must NOT leave the agent at
        'deploying' (a permanent wedge) — settle to is_dead 'error'."""
        def boom(r):
            raise RuntimeError("spawn failed")
        agent, ok, _ = self._respawn(boom)
        self.assertFalse(ok)
        self.assertEqual(agent.status, "error")        # is_dead, not "deploying"
        self.assertEqual(agent.intent, AgentState.INTENT_RUNNING)

    def test_success_non_spawn_is_now_a_deploy_failure(self):
        """#13032: success with action='skip' (agent STILL ALIVE at respawn,
        after we waited for the PID to die) is the original no-op bug — it must
        NOT be settled to running on stale instructions. Fail honest (is_dead
        'error', returns False). The deploy-error emit is owned by the caller
        (_respawn_after_deploy / _deploy_recover_and_respawn), so
        _respawn_agent_process itself emits nothing (DS-13032-B F1)."""
        agent, ok, emitted = self._respawn(
            lambda r: {"success": True, "action": "skip", "message": "already alive"})
        self.assertFalse(ok)
        self.assertEqual(agent.status, "error")        # is_dead, not silent "running"
        self.assertEqual(emitted, [])                  # caller owns the emit

    def test_boot_failure_returns_false_and_errors(self):
        agent, ok, emitted = self._respawn(
            lambda r: {"success": False, "action": "spawn", "message": "boom"})
        self.assertFalse(ok)
        self.assertEqual(agent.status, "error")
        self.assertEqual(emitted, [])                  # caller owns the emit

    def test_force_kills_old_pid_since_agent_cannot_self_quit(self):
        """#13077: the agent CANNOT self-/quit, so the harness actively
        force-kills the deploy-halted process before booting. With the old PID
        alive, _kill_process MUST be called with it; once it dies the respawn
        boots fresh."""
        agent, ok, emitted = self._respawn(
            lambda r: {"success": True, "action": "spawn", "message": "ok"},
            claude_pid=4242, pid_alive=True, pid_dies=True)
        self.assertTrue(ok)
        self.assertEqual(self.killed, [4242])           # harness actively killed it
        self.assertEqual(agent.status, "starting")
        self.assertEqual(emitted, [])

    def test_old_pid_survives_force_kill_aborts_respawn(self):
        """#13077: if the force-kill itself fails (PID still alive after it),
        do NOT boot over the live process (singleton would no-op) — abort and
        leave is_dead 'error'. boot_agent must NOT be called; the deploy-error
        is the caller's to emit (DS-13032-B F1)."""
        called = []
        agent, ok, emitted = self._respawn(
            lambda r: called.append(r) or {"success": True, "action": "spawn"},
            claude_pid=4242, pid_alive=True, pid_dies=False)
        self.assertFalse(ok)
        self.assertEqual(self.killed, [4242])           # we DID try to kill it
        self.assertEqual(called, [])                    # never booted over a live process
        self.assertEqual(agent.status, "error")
        self.assertEqual(agent.intent, AgentState.INTENT_RUNNING)
        self.assertEqual(emitted, [])                  # caller owns the emit

    def test_old_pid_already_dead_skips_kill_and_boots(self):
        """#13077: if the old PID is already gone (rare — the deploy's own
        steps ran first), no force-kill is needed and the respawn boots fresh."""
        agent, ok, emitted = self._respawn(
            lambda r: {"success": True, "action": "spawn", "message": "ok"},
            claude_pid=4242, pid_alive=False, pid_dies=True)
        self.assertTrue(ok)
        self.assertEqual(self.killed, [])               # nothing to kill
        self.assertEqual(agent.status, "starting")
        self.assertEqual(emitted, [])

    def test_deploy_error_reports_respawn_outcome(self):
        """DS iter-2 Finding 3: deploy-error payload carries the real respawn_ok."""
        import harness
        agent = AgentState("skill", "")
        emitted = []
        with patch.object(harness, "state", _DeployFakeState(agent)), \
             patch.object(harness, "_respawn_agent_process", return_value=False), \
             patch.object(harness, "_emit_event",
                          side_effect=lambda *a, **k: emitted.append((a, k))), \
             patch.object(harness, "_log"):
            harness._deploy_recover_and_respawn("skill", "pull", "conflict")
        self.assertEqual(len(emitted), 1)
        self.assertEqual(emitted[0][1]["payload"]["respawn_ok"], False)

    def test_success_path_respawn_failure_emits_single_deploy_error(self):
        """#13032 DS-13032-B F1/F2: a respawn failure on the SUCCESS path
        (deploy composed/committed fine but the agent didn't come back) is no
        longer silent — _respawn_after_deploy emits exactly one deploy-error."""
        import harness
        emitted = []
        with patch.object(harness, "_respawn_agent_process", return_value=False), \
             patch.object(harness, "_emit_event",
                          side_effect=lambda *a, **k: emitted.append((a, k))), \
             patch.object(harness, "_log"):
            harness._respawn_after_deploy("skill")
        self.assertEqual(len(emitted), 1)
        self.assertEqual(emitted[0][0][0], "deploy-error")
        self.assertEqual(emitted[0][1]["payload"]["stage"], "respawn")
        self.assertFalse(emitted[0][1]["payload"]["respawn_ok"])

    def test_success_path_respawn_ok_emits_nothing(self):
        import harness
        emitted = []
        with patch.object(harness, "_respawn_agent_process", return_value=True), \
             patch.object(harness, "_emit_event",
                          side_effect=lambda *a, **k: emitted.append((a, k))), \
             patch.object(harness, "_log"):
            harness._respawn_after_deploy("skill")
        self.assertEqual(emitted, [])

    def test_recovery_path_emits_single_deploy_error_no_double(self):
        """#13032 DS-13032-B F1: the recovery path emits ONE deploy-error (its
        stage failure) — _respawn_agent_process no longer emits its own, so a
        respawn failure during recovery does not double-emit."""
        import harness
        agent = AgentState("skill", "")
        # Old PID alive AND survives the force-kill (pid_dies=False) → respawn
        # aborts inside the call. Mock _is_process_alive/_kill_process so the
        # #13077 force-kill block actually executes (not the real OS — #13077
        # DS Finding 1) rather than falling through to the boot_agent path.
        agent.claude_pid = 4242
        emitted = []
        with patch.object(harness, "state", _DeployFakeState(agent)), \
             patch.object(harness.boot_remote, "_is_process_alive", return_value=True), \
             patch.object(harness.reboot_agent, "_kill_process", side_effect=lambda p: None), \
             patch.object(harness, "_await_pid_death", return_value=False), \
             patch.object(harness.boot_remote, "boot_agent",
                          side_effect=AssertionError("must not boot over live PID")), \
             patch.object(harness, "_emit_event",
                          side_effect=lambda *a, **k: emitted.append((a, k))), \
             patch.object(harness, "_log"):
            harness._deploy_recover_and_respawn("skill", "pull", "conflict")
        self.assertEqual(len(emitted), 1)              # not two
        self.assertEqual(emitted[0][1]["payload"]["stage"], "pull")
        self.assertFalse(emitted[0][1]["payload"]["respawn_ok"])


class TestAwaitPidDeath(unittest.TestCase):
    """#13032: the deploy respawn waits for the halted agent's own claude
    process to exit before booting its replacement."""

    def test_returns_true_when_already_dead(self):
        import harness
        with patch.object(harness.boot_remote, "_is_process_alive",
                          return_value=False):
            self.assertTrue(harness._await_pid_death(4242, 5))

    def test_returns_false_when_alive_past_timeout(self):
        import harness
        with patch.object(harness.boot_remote, "_is_process_alive",
                          return_value=True), \
             patch.object(harness.time, "monotonic",
                          side_effect=[0.0, 0.0, 10.0]), \
             patch.object(harness.time, "sleep"):
            self.assertFalse(harness._await_pid_death(4242, 5))

    def test_returns_true_when_dies_mid_wait(self):
        import harness
        alive = [True, False]
        with patch.object(harness.boot_remote, "_is_process_alive",
                          side_effect=lambda p: alive.pop(0)), \
             patch.object(harness.time, "monotonic",
                          side_effect=[0.0, 1.0, 2.0]), \
             patch.object(harness.time, "sleep") as slept:
            self.assertTrue(harness._await_pid_death(4242, 30))
            slept.assert_called()


class TestLoadStateRestoresStatus(unittest.TestCase):
    """DS-12912 iter-2 Finding 5: load_state must restore `status`."""

    def _load(self, status_value, intent="running"):
        import harness
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            sf = Path(tmp) / ".harness-state.json"
            sf.write_text(json.dumps({
                "harness_pid": 1, "start_time": 0.0, "port": 7373,
                "agents": {"skill": {"intent": intent, "status": status_value,
                                     "clone_path": "", "claude_pid": 999}},
            }), encoding="utf-8")
            with patch.object(harness, "HARNESS_STATE_FILE", sf), \
                 patch.object(harness, "_log"):
                hs = harness.HarnessState()
                hs.load_state()
                return hs.get_agent("skill")

    def test_running_status_restored(self):
        self.assertEqual(self._load("running").status, "running")

    def test_deploying_settles_to_running(self):
        """An interrupted mid-deploy restores to 'running' (dead PID → rebooted),
        and its intent is reset away from DEPLOYING."""
        from harness import AgentState as A
        a = self._load("deploying", intent="deploying")
        self.assertEqual(a.status, "running")
        self.assertEqual(a.intent, A.INTENT_RUNNING)

    def test_legacy_missing_status_defaults_unknown(self):
        import harness
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            sf = Path(tmp) / ".harness-state.json"
            sf.write_text(json.dumps({
                "harness_pid": 1, "start_time": 0.0, "port": 7373,
                "agents": {"skill": {"intent": "running", "clone_path": ""}},
            }), encoding="utf-8")
            with patch.object(harness, "HARNESS_STATE_FILE", sf), \
                 patch.object(harness, "_log"):
                hs = harness.HarnessState()
                hs.load_state()
                self.assertEqual(hs.get_agent("skill").status, "unknown")


class TestDetectOnlyFreshness(unittest.TestCase):
    """S5 (AC5 / §10 step 1b): boot freshness check is detect-only — it never
    runs compose.py deploy-all locally."""

    def test_detect_only_drift_does_not_run_compose(self):
        import compose_freshness as cf
        ran = []
        res = cf.check_and_repair(
            repo_root="/tmp/x",
            stored_checksum="oldsum",
            detect_only=True,
            compute_checksum=lambda r: "newsum",
            runner=lambda r: ran.append(r) or (0, "", ""),
        )
        self.assertEqual(res.status, "drift")
        self.assertEqual(res.new_checksum, "newsum")
        self.assertEqual(ran, [])  # compose runner NEVER invoked

    def test_detect_only_absent_checksum_is_drift(self):
        import compose_freshness as cf
        ran = []
        res = cf.check_and_repair(
            repo_root="/tmp/x",
            stored_checksum=None,
            detect_only=True,
            compute_checksum=lambda r: "sum",
            runner=lambda r: ran.append(r) or (0, "", ""),
        )
        self.assertEqual(res.status, "drift")
        self.assertEqual(ran, [])

    def test_detect_only_clean_on_match(self):
        import compose_freshness as cf
        res = cf.check_and_repair(
            repo_root="/tmp/x",
            stored_checksum="same",
            detect_only=True,
            compute_checksum=lambda r: "same",
            runner=lambda r: (_ for _ in ()).throw(AssertionError("runner ran")),
        )
        self.assertEqual(res.status, "clean")

    def test_boot_path_is_detect_only(self):
        src = (Path(__file__).resolve().parent.parent / "references" / "scripts"
               / "harness.py").read_text(encoding="utf-8")
        start = src.index("async def lifespan(")
        end = src.index("app = FastAPI(", start)
        block = src[start:end]
        self.assertIn("detect_only=True", block)
        self.assertNotIn('status == "failed"', block)


class TestEmitBootDeploySignals(unittest.TestCase):
    """S5: on boot drift, _emit_boot_deploy_signals emits a deploy-signal to each
    running agent (no local compose)."""

    def test_emits_to_running_agents(self):
        import harness
        agent = AgentState("skill", "")
        agent.intent = AgentState.INTENT_RUNNING
        emitted = []
        with patch.object(harness, "_NO_AUTO_REBOOT", False), \
             patch.object(harness.boot_remote, "_get_all_roles", return_value=["skill"]), \
             patch.object(harness, "state", _DeployFakeState(agent)), \
             patch.object(harness, "_emit_event",
                          side_effect=lambda *a, **k: emitted.append((a, k))), \
             patch.object(harness, "_log"):
            harness._emit_boot_deploy_signals()
        self.assertEqual(len(emitted), 1)
        self.assertEqual(emitted[0][0][0], "deploy-signal")
        self.assertEqual(emitted[0][1]["payload"]["target_alias"], "skill")

    def test_no_auto_reboot_skips_boot_emit(self):
        import harness
        emitted = []
        with patch.object(harness, "_NO_AUTO_REBOOT", True), \
             patch.object(harness, "_emit_event",
                          side_effect=lambda *a, **k: emitted.append(a)), \
             patch.object(harness, "_log"):
            harness._emit_boot_deploy_signals()
        self.assertEqual(emitted, [])


class TestLoopModeDoesNotConsume(unittest.TestCase):
    """AC7: a loop-mode (polling) agent does not consume a deploy-signal — the
    event bus is event-mode only. It picks up the updated CLAUDE.md at its next
    session start via cycle_pre.py's pull (AGENT-RUNTIME §7.8)."""

    def _read(self, rel):
        return (Path(__file__).resolve().parent.parent / rel).read_text(encoding="utf-8")

    def test_event_contract_states_loop_mode_does_not_consume(self):
        txt = self._read("references/sub-skills/common-events/event-mode-contract.md")
        idx = txt.find("deploy-signal")
        self.assertNotEqual(idx, -1)
        # The Case E deploy-signal bullet must call out the loop-mode exemption.
        block = txt[idx:idx + 4000]
        self.assertIn("oop", block)  # loop/polling
        self.assertTrue("never consume" in block or "does not apply" in block
                        or "next session start" in block)

    def test_polling_fragments_have_no_deploy_signal_handling(self):
        # The runtime-loaded polling fragments must NOT carry deploy-signal
        # handling — loop mode never touches the bus.
        for role in ("worker", "pm", "verifier", "dm"):
            rel = f"references/sub-skills/roles/{role}/ralph-loop-overview.md"
            p = Path(__file__).resolve().parent.parent / rel
            if p.exists():
                self.assertNotIn("deploy-signal", p.read_text(encoding="utf-8"),
                                 f"{rel} must not handle deploy-signal (loop mode)")


class TestDeployLockSerializes(unittest.TestCase):
    def test_deploy_lock_is_a_lock(self):
        import harness
        import threading as _t
        self.assertIsInstance(harness._deploy_lock, type(_t.Lock()))

    def test_ack_stop_spawns_deploy_thread(self):
        src = inspect.getsource(receive_event)
        idx = src.find('"deploy-halted"')
        block = src[idx:idx + 3000]
        self.assertIn("_run_deploy_sequence", block)
        self.assertIn("Thread", block)
        # DS Finding 1: the deploy-signal's event_id (ack_event_id) is handed to
        # the deploy sequence so it can advance the cursor past the signal.
        self.assertIn("ack_event_id", block)


if __name__ == "__main__":
    unittest.main()
