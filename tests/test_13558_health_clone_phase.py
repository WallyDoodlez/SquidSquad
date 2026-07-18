"""Regression test for #13558 — GET /agents/{role}/health must read
current_phase from the agent's OWN clone
(<clone>/.squidsquad/<role>/current-state), not the harness-root
SQUIDSQUAD_DIR/<role>/. Sibling-clone agents (skill/qa/dm) write the file to
their own clone, so the harness-root read returned a stale/absent value —
the exact sibling half of #13345, which fixed context_pressure but
explicitly left current_phase out of scope.

The fix routes the endpoint through the new shared
HarnessState._read_agent_clone_file(role, agent, filename) helper, which
_read_agent_pressure (#13335/#13345) is also refactored onto so both fields
share one clone-resolution implementation.
"""
import asyncio
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import harness  # noqa: E402
from harness import AgentState  # noqa: E402


def _running_agent(role, clone):
    a = AgentState(role, clone)
    a.status = "running"
    a.bootup_complete = True
    return a


def _write_phase(clone, role, value):
    d = Path(clone) / ".squidsquad" / role
    d.mkdir(parents=True, exist_ok=True)
    (d / "current-state").write_text(value, encoding="utf-8")


class TestHealthReadsClonePhase13558(unittest.TestCase):
    def test_reads_from_clone_not_harness_root(self):
        with tempfile.TemporaryDirectory() as td:
            _write_phase(td, "skill", "verifying")
            agent = _running_agent("skill", str(td))
            with patch.object(harness.state, "get_agent", return_value=agent):
                result = asyncio.run(harness.get_agent_health("skill"))
            self.assertEqual(result["current_phase"], "verifying")

    def test_absent_clone_file_is_none(self):
        with tempfile.TemporaryDirectory() as td:
            agent = _running_agent("skill", str(td))  # no current-state file
            with patch.object(harness.state, "get_agent", return_value=agent):
                result = asyncio.run(harness.get_agent_health("skill"))
            self.assertIsNone(result["current_phase"])

    def test_no_agent_is_safe(self):
        with patch.object(harness.state, "get_agent", return_value=None), \
             patch("harness.boot_remote._get_clone_path",
                   side_effect=RuntimeError("no clone")):
            result = asyncio.run(harness.get_agent_health("skill"))
        self.assertIsNone(result["current_phase"])
        self.assertFalse(result["alive"])

    def test_harness_root_file_ignored_for_sibling_clone(self):
        """The #13345/#13558 root cause: a STALE harness-root current-state
        must NOT leak into the response for a sibling-clone agent — the
        agent's own clone is authoritative. Patches SQUIDSQUAD_DIR to an
        isolated temp dir (never touches this session's real
        .squidsquad/skill/current-state)."""
        with tempfile.TemporaryDirectory() as clone_dir, \
             tempfile.TemporaryDirectory() as harness_root:
            harness_root_state = Path(harness_root) / "skill"
            harness_root_state.mkdir(parents=True, exist_ok=True)
            (harness_root_state / "current-state").write_text(
                "STALE_HARNESS_ROOT_VALUE", encoding="utf-8")

            agent = _running_agent("skill", clone_dir)  # own clone: no file
            with patch.object(harness.state, "get_agent", return_value=agent), \
                 patch.object(harness, "SQUIDSQUAD_DIR", Path(harness_root)):
                result = asyncio.run(harness.get_agent_health("skill"))
            self.assertIsNone(
                result["current_phase"],
                "must read the agent's own clone, not the harness-root file "
                "(which held a stale value)",
            )


class TestReadAgentCloneFileHelper13558(unittest.TestCase):
    """The shared clone-resolution helper both context_pressure and
    current_phase now go through."""

    def test_reads_arbitrary_filename(self):
        with tempfile.TemporaryDirectory() as td:
            _write_phase(td, "skill", "shipping")
            agent = _running_agent("skill", str(td))
            text = harness.state._read_agent_clone_file(
                "skill", agent, "current-state")
            self.assertEqual(text, "shipping")

    def test_falls_back_to_get_clone_path_when_agent_has_no_clone_path(self):
        with tempfile.TemporaryDirectory() as td:
            _write_phase(td, "skill", "planning")
            agent = AgentState("skill", None)  # no clone_path on the agent
            with patch("harness.boot_remote._get_clone_path", return_value=td):
                text = harness.state._read_agent_clone_file(
                    "skill", agent, "current-state")
            self.assertEqual(text, "planning")

    def test_unresolvable_clone_is_none(self):
        agent = AgentState("skill", None)
        with patch("harness.boot_remote._get_clone_path",
                   side_effect=RuntimeError("no clone")):
            text = harness.state._read_agent_clone_file(
                "skill", agent, "current-state")
        self.assertIsNone(text)

    def test_context_pressure_still_int_parses_via_shared_helper(self):
        """Non-regression: _read_agent_pressure's int-parsing contract must
        survive being refactored onto the shared text helper."""
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / ".squidsquad" / "skill"
            d.mkdir(parents=True, exist_ok=True)
            (d / "context-pressure").write_text("55", encoding="utf-8")
            agent = _running_agent("skill", str(td))
            self.assertEqual(harness.state._read_agent_pressure("skill", agent), 55)


if __name__ == "__main__":
    unittest.main()
