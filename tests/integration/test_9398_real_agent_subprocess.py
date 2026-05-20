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


if __name__ == "__main__":
    unittest.main()
