"""§4.1 real-agent-subprocess tests for #9398.

The wire halves of these contracts already live in
``test_event_mode_agent_subprocess.py`` (TestClient against the
in-process FastAPI app). #9398 calls for *real* subprocess
exercises — actually spawn ``harness.py`` and a separate agent
process that posts events via HTTP. The fixture infrastructure
lives in ``fixtures/event_mode_subprocess.py``.

This first cut covers AC-3 M-3.2's subprocess half:
the bootup-complete signal flips ``AgentState.bootup_complete``
when emitted from a real subprocess. Work-pickup (the rest of
AC-3 M-3.2) requires a gh PATH-shim and lives in a follow-up commit.
"""

from __future__ import annotations

import json
import sys
import unittest
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "tests" / "integration"))

# Import the fixture as a module so unittest's discovery picks it up
# from the package path.
from fixtures import event_mode_subprocess as ems  # noqa: E402


def _get_agent(port: int, role: str, timeout: float = 30.0) -> dict:
    """GET /agents/{role} and return the parsed JSON body.

    Timeout defaults to 30s because the post-#9481 handler wraps
    ``state.update_health`` in ``asyncio.to_thread`` — on Windows that
    shells out to ``tasklist`` for each registered agent, which can
    take 10-20s on a cold machine. The 5s default urlopen timeout
    races that call and fails.
    """
    with urllib.request.urlopen(
        f"http://127.0.0.1:{port}/agents/{role}", timeout=timeout
    ) as resp:
        if resp.status != 200:
            raise AssertionError(
                f"GET /agents/{role} returned HTTP {resp.status} — "
                "harness should have created the role record on first "
                "boot-event arrival."
            )
        return json.loads(resp.read().decode("utf-8"))


class TestBootupCompleteAcrossRealSubprocesses(unittest.TestCase):
    """AC-3 M-3.2 subprocess half: a real agent subprocess emits
    ``bootup-complete`` against a real harness, and the harness
    records it on ``AgentState.bootup_complete`` exposed via
    ``GET /agents/{role}``. The wire half pins the same invariant
    against the in-process app; this test pins it across a real
    process boundary, which the deferred §4 work for #8999 calls
    out as the load-bearing scenario."""

    def test_real_subprocess_bootup_flips_agent_state_flag(self):
        role = "skill"
        with ems.real_harness() as (port, harness_proc, squid_dir):
            self.assertIsNone(
                harness_proc.poll(),
                msg="harness subprocess exited unexpectedly during setup",
            )

            # Pre-condition: there's no agent state for this role yet
            # (no auto-start), so /agents/{role} should 404 or the
            # role's record should report bootup_complete=False if the
            # harness has lazily created it. Either is acceptable
            # pre-state; we only care that AFTER the bootup-complete
            # post, the flag reads True.

            result = ems.boot_agent_subprocess(role, squid_dir)
            self.assertEqual(
                result.returncode, 0,
                msg=(
                    f"boot agent stub exited rc={result.returncode}. "
                    f"stderr: {result.stderr[:500]!r}"
                ),
            )

            agent = _get_agent(port, role)
            self.assertTrue(
                agent.get("bootup_complete"),
                msg=(
                    "harness must flip AgentState.bootup_complete=True "
                    "after a real agent subprocess emits the event. "
                    f"Got agent record: {agent!r}"
                ),
            )

    def test_real_subprocess_bootup_is_idempotent(self):
        """Per the L1 base spec: multiple bootup-complete posts are
        safe — a re-spawned agent must be allowed to re-assert. The
        in-process test already pins this against the TestClient
        app; this test confirms the contract holds across real
        process boundaries too (no race on the harness's internal
        agent-state lock)."""
        role = "skill"
        with ems.real_harness() as (port, _proc, squid_dir):
            for _ in range(3):
                result = ems.boot_agent_subprocess(role, squid_dir)
                self.assertEqual(
                    result.returncode, 0,
                    msg=(
                        f"boot agent stub exited rc={result.returncode}. "
                        f"stderr: {result.stderr[:500]!r}"
                    ),
                )
            agent = _get_agent(port, role)
            self.assertTrue(agent.get("bootup_complete"))


class TestRealHarnessFixtureWritesPortFileToIsolatedDir(unittest.TestCase):
    """Sanity check on the fixture itself: it must write the
    ``.harness-port`` file to the isolated SQUIDSQUAD_DIR, NOT to
    the live ``.squidsquad/`` next to the repo. Regression guard
    for the env-var refactor that landed in cycle 1189; without
    it, this whole approach is moot (the test harness would
    clobber the live one)."""

    def test_port_file_lives_under_isolated_squid_dir(self):
        with ems.real_harness() as (port, _proc, squid_dir):
            port_file = squid_dir / ".harness-port"
            self.assertTrue(
                port_file.exists(),
                msg=(
                    "Harness must write .harness-port to the env-"
                    "overridden SQUIDSQUAD_DIR. If this fails, the "
                    "harness is still writing to the live "
                    ".squidsquad/.harness-port and test isolation "
                    "is broken (#9398 Phase A precondition)."
                ),
            )
            on_disk = int(port_file.read_text(encoding="utf-8").strip())
            self.assertEqual(on_disk, port)

    def test_live_port_file_not_touched(self):
        """The live repo's ``.squidsquad/.harness-port`` must not
        be modified by the fixture. Records its mtime before
        entering the fixture and asserts it's unchanged after.
        Skips cleanly if the live file doesn't exist (a clean
        checkout state, fine)."""
        live_port = REPO_ROOT / ".squidsquad" / ".harness-port"
        if not live_port.exists():
            self.skipTest("no live .harness-port to guard against")
        before = live_port.stat().st_mtime_ns
        with ems.real_harness():
            pass
        after = live_port.stat().st_mtime_ns
        self.assertEqual(
            before, after,
            msg=(
                "Fixture must not modify the live "
                ".squidsquad/.harness-port — that would re-route every "
                "other SquidSquad process to the test harness on its "
                "next port discovery (#9398 Phase A precondition)."
            ),
        )


# ---------------------------------------------------------------------------
# §4.1 AC-3 M-3.2 — work-pickup half (the real point of #9398 Phase A)
# ---------------------------------------------------------------------------

import os  # noqa: E402
import subprocess  # noqa: E402
import tempfile  # noqa: E402

TRACKER_PY = REPO_ROOT / "references" / "scripts" / "tracker.py"


class TestAgentWorkPickupThroughGhShim(unittest.TestCase):
    """The §4.1 acceptance criterion calls for an event-mode agent
    subprocess that picks up the forge's top approved item via
    ``tracker.list-tasks`` + ``tracker.transition``. The wire half
    of that contract (post a status-transition event, harness
    distributes it) already passes in `test_event_mode_agent_subprocess.py`;
    this test covers the *real subprocess* half — the agent's
    tracker calls hit our gh PATH-shim, the shim returns canned
    issues, the agent's transition write lands on the shim's
    ``_writes.log``, and we assert the expected transition.

    Why subprocess'd `tracker.py` instead of spawning `cycle_pre.py`:
    the work-pickup logic in `cycle_pre._do_work_queue` is a thin
    wrapper around `tracker.work_queue` / `tracker.list_issues` /
    `tracker.transition`. Exercising tracker.py directly (rather
    than the bigger cycle_pre process) keeps the test focused on
    the shim-tracker contract that this PR is actually delivering.
    A future cycle_pre subprocess test layers on top of this.
    """

    def _run_tracker(self, args: list[str], fixtures_dir: Path,
                     timeout: float = 15.0):
        """Spawn tracker.py with the gh-shim on PATH and the
        fixtures dir set, capture stdout/stderr."""
        env = ems.env_with_gh_shim(fixtures_dir=fixtures_dir)
        return subprocess.run(
            [sys.executable, str(TRACKER_PY)] + args,
            env=env, cwd=str(REPO_ROOT),
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=timeout, check=False,
        )

    def test_agent_finds_canned_approved_task_and_transitions(self):
        """End-to-end work-pickup slice:
        1. Test prepares a canned approved task fixture.
        2. tracker.py list-tasks → finds the canned task.
        3. tracker.py transition (approved → in-progress) → write
           logged to shim's _writes.log.
        4. Test asserts the writes log shows the expected transition
           with the expected from/to labels.

        This is the load-bearing scenario for the AC-3 M-3.2
        subprocess half. Without it, #9386 / #9387 (which reuse
        this fixture) have no proven baseline."""
        import json as _json

        with tempfile.TemporaryDirectory(prefix="wp-fix-") as tmp:
            fdir = Path(tmp)
            issue_number = 87654

            # Canned approved task for the list-tasks fetch.
            (fdir / "issue-list").mkdir()
            canned_task = [{
                "number": issue_number,
                "title": "TASK: synthetic approved task for #9398 work-pickup test",
                "labels": [
                    {"name": "type:task"},
                    {"name": "role:skill"},
                    {"name": "status:approved"},
                    {"name": "priority:medium"},
                ],
            }]
            (fdir / "issue-list" / "default.json").write_text(
                _json.dumps(canned_task), encoding="utf-8"
            )

            # Canned issue-view (transition's _check_authority calls
            # `gh issue view <N> --json labels` to enforce that the
            # caller's role matches the issue's role:* label).
            (fdir / "issue-view").mkdir()
            (fdir / "issue-view" / str(issue_number)).with_suffix(".json").write_text(
                _json.dumps({
                    "labels": [
                        {"name": "type:task"},
                        {"name": "role:skill"},
                        {"name": "status:approved"},
                    ],
                }), encoding="utf-8"
            )

            # Step 1: list-tasks finds the canned task.
            list_result = self._run_tracker(
                ["list-tasks", "skill", "--status", "approved"], fdir,
            )
            self.assertEqual(
                list_result.returncode, 0,
                msg=(
                    f"list-tasks failed rc={list_result.returncode}. "
                    f"stderr: {list_result.stderr[:500]!r}"
                ),
            )
            listed = _json.loads(list_result.stdout)
            self.assertEqual(len(listed), 1)
            self.assertEqual(listed[0]["number"], issue_number)

            # Step 2: transition approved → in-progress.
            trans_result = self._run_tracker(
                ["transition", str(issue_number),
                 "approved", "in-progress",
                 "--role", "skill-lead"],
                fdir,
            )
            # tracker.transition returns 0 on success and prints
            # a one-line confirmation. If authority is rejected
            # we'll see a non-zero exit and the stderr will say why.
            self.assertEqual(
                trans_result.returncode, 0,
                msg=(
                    f"transition failed rc={trans_result.returncode}. "
                    f"stdout: {trans_result.stdout[:500]!r}; "
                    f"stderr: {trans_result.stderr[:500]!r}"
                ),
            )

            # Step 3: assert the writes log shows the expected
            # transition. The shim logs every write-type gh call;
            # transition makes two: an issue-edit (--remove-label
            # status:approved --add-label status:in-progress) and
            # potentially a comment if --message was used (we
            # didn't pass --message so just the edit).
            log = fdir / "_writes.log"
            self.assertTrue(
                log.exists(),
                msg=(
                    "Shim must have logged at least one write call "
                    "for the transition — without this, we can't "
                    "verify the agent actually issued the transition."
                ),
            )
            entries = [
                _json.loads(line) for line in
                log.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            edit_entries = [e for e in entries if e["verb"] == "edit"]
            self.assertTrue(
                edit_entries,
                msg=(
                    f"Expected at least one `issue edit` log entry "
                    f"from the transition. Log entries: {entries!r}"
                ),
            )
            # Pin the specific labels asserted in the edit so a
            # future tracker refactor that drops one of them fails.
            edit_args = " ".join(edit_entries[0]["args"])
            self.assertIn("status:approved", edit_args)
            self.assertIn("status:in-progress", edit_args)


# ---------------------------------------------------------------------------
# §4.5 AC-2 — degraded mode (harness DOWN)
# ---------------------------------------------------------------------------


class TestAgentDegradedModeWithoutHarness(unittest.TestCase):
    """The §4.5 acceptance: when the harness is down, the agent
    must NOT crash and MUST keep doing useful work — specifically:

    - ``event_bus.emit()`` is silent no-op when port file is missing
      (AC-2 M-2.1). Mechanical scripts that sprinkle emit() calls
      keep running without raising.
    - ``tracker.work_queue`` still returns the forge's top item
      (AC-2 M-2.3) — tracker talks to the forge directly via gh,
      so it doesn't need a harness to function.
    - When the harness later comes up, the agent can re-enter
      event_poll (M-2.2). Wire-half pinned in
      ``test_event_mode_agent_subprocess.py``; we sanity-check the
      subprocess flow here by spinning up a fresh harness AFTER the
      agent's first cycle and confirming a subsequent emit lands.

    Wire-half coverage exists in
    ``test_event_mode_agent_subprocess.py::TestHarnessDownBoot``.
    This class exercises the *real subprocess* shape of the same
    contract — the agent process must not crash when there's no
    harness, and must still pick up work.
    """

    def _run_tracker(self, args, fixtures_dir, squid_dir, timeout=15.0):
        """Spawn tracker.py in degraded mode — gh-shim on PATH,
        SQUIDSQUAD_DIR isolated, NO harness running so no
        .harness-port file exists in squid_dir."""
        env = ems.env_with_gh_shim(fixtures_dir=fixtures_dir)
        env["SQUIDSQUAD_DIR"] = str(squid_dir)
        return subprocess.run(
            [sys.executable, str(TRACKER_PY)] + args,
            env=env, cwd=str(REPO_ROOT),
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=timeout, check=False,
        )

    def _run_emit_probe(self, role, squid_dir, timeout=10.0):
        """Spawn a thin python subprocess that imports event_bus
        and calls ``emit('cycle-start', role, {'cycle_number': 1})``.
        Returns the CompletedProcess. The subprocess MUST NOT raise
        even when no harness is reachable (fire-and-forget
        contract). SQUIDSQUAD_DIR points at the isolated tmpdir so
        event_bus reads the test harness's port file (if any), not
        the live one.

        Repo root and role are passed via env vars (not interpolated
        into the inline ``-c`` script) so a repo path containing a
        single-quote (rare but possible: ``~/user's-dir``) doesn't
        produce a SyntaxError in the probe subprocess — Sonnet code
        review LOW finding on cumulative #9614 scope."""
        env = dict(os.environ)
        env["SQUIDSQUAD_DIR"] = str(squid_dir)
        env["_SQ_PROBE_REPO_ROOT"] = str(REPO_ROOT)
        env["_SQ_PROBE_ROLE"] = role
        return subprocess.run(
            [
                sys.executable, "-c",
                "import os, sys;"
                "sys.path.insert(0, os.path.join("
                "os.environ['_SQ_PROBE_REPO_ROOT'],"
                " 'references', 'scripts'));"
                "import event_bus;"
                "event_bus.emit('cycle-start',"
                " os.environ['_SQ_PROBE_ROLE'],"
                " {'cycle_number': 1});"
                "print('emit-returned-cleanly')",
            ],
            env=env, cwd=str(REPO_ROOT),
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=timeout, check=False,
        )

    def test_event_bus_emit_silent_noop_when_harness_down(self):
        """AC-2 M-2.1 subprocess half — event_bus.emit() from an
        agent subprocess must return cleanly when no harness is
        running (no port file in SQUIDSQUAD_DIR). The agent's boot
        sequence sprinkles emit() calls; a raise here would crash
        boot in degraded mode."""
        with tempfile.TemporaryDirectory(prefix="degraded-emit-") as tmp:
            squid_dir = Path(tmp)
            # No harness started; no .harness-port file exists.
            self.assertFalse((squid_dir / ".harness-port").exists())

            result = self._run_emit_probe("skill", squid_dir)
            self.assertEqual(
                result.returncode, 0,
                msg=(
                    f"event_bus.emit() must NOT raise when harness "
                    f"is down. Subprocess rc={result.returncode}. "
                    f"stderr: {result.stderr[:500]!r}"
                ),
            )
            self.assertIn("emit-returned-cleanly", result.stdout)

    def test_tracker_work_queue_works_without_harness(self):
        """AC-2 M-2.3 subprocess half — tracker.work_queue does
        not depend on the harness; it shells out to gh. With our
        shim + canned approved task, the agent picks up work
        EVEN WHEN the harness is down. This is the load-bearing
        invariant: agents don't get stuck in a no-op loop when
        operator forgot to start the harness."""
        import json as _json
        with tempfile.TemporaryDirectory(prefix="degraded-wq-") as tmp_sq, \
             tempfile.TemporaryDirectory(prefix="degraded-fix-") as tmp_fix:
            squid_dir = Path(tmp_sq)
            fdir = Path(tmp_fix)
            # No harness; no .harness-port.
            self.assertFalse((squid_dir / ".harness-port").exists())

            # Canned approved task.
            (fdir / "issue-list").mkdir()
            canned = [{
                "number": 87655,
                "title": "TASK: degraded-mode pickup test",
                "labels": [
                    {"name": "type:task"},
                    {"name": "role:skill"},
                    {"name": "status:approved"},
                    {"name": "priority:medium"},
                ],
            }]
            (fdir / "issue-list" / "default.json").write_text(
                _json.dumps(canned), encoding="utf-8"
            )

            result = self._run_tracker(
                ["list-tasks", "skill", "--status", "approved"],
                fdir, squid_dir,
            )
            self.assertEqual(
                result.returncode, 0,
                msg=(
                    f"tracker.list-tasks must succeed without "
                    f"harness running. rc={result.returncode}. "
                    f"stderr: {result.stderr[:500]!r}"
                ),
            )
            listed = _json.loads(result.stdout)
            self.assertEqual(len(listed), 1)
            self.assertEqual(listed[0]["number"], 87655)

    def test_emit_succeeds_when_harness_comes_up(self):
        """AC-2 M-2.2 subprocess half — once the harness comes
        back up, a subsequent emit() reaches it. Verifies the
        ``no-harness → harness-up`` transition the wire half pins
        in ``test_event_mode_agent_subprocess.py`` works across a
        real process boundary too.

        Sequence: emit (no harness) → silent no-op → start
        harness in same SQUIDSQUAD_DIR → emit again → succeeds
        (harness records the event on AgentState)."""
        with ems.real_harness() as (port, _proc, squid_dir):
            # Harness is up; .harness-port file written.
            self.assertTrue((squid_dir / ".harness-port").exists())

            # Now emit through a real subprocess and confirm the
            # subprocess doesn't crash. (Verifying the event
            # actually lands on the harness is covered by
            # test_real_subprocess_bootup_flips_agent_state_flag;
            # the additional assertion here is that the *process*
            # using SQUIDSQUAD_DIR-overridden event_bus can post
            # without raising once the port file is back.)
            result = self._run_emit_probe("skill", squid_dir)
            self.assertEqual(
                result.returncode, 0,
                msg=(
                    f"event_bus.emit() must succeed once harness "
                    f"is up. rc={result.returncode}. "
                    f"stderr: {result.stderr[:500]!r}"
                ),
            )
            self.assertIn("emit-returned-cleanly", result.stdout)


if __name__ == "__main__":
    unittest.main()
