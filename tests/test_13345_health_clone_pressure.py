"""Regression test for #13345 — GET /agents/{role}/health must read
context-pressure from the agent's OWN clone
(<clone>/.squidsquad/<role>/context-pressure), not the harness-root
SQUIDSQUAD_DIR/<role>/. Sibling-clone agents (skill/qa/dm) write the file to
their own clone, so the harness-root read returned a stale/absent value.

The fix routes the endpoint through HarnessState._read_agent_pressure — the same
clone-relative read #13335's enforcement path uses — so the reported number
matches what is actually enforced.
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


def _write_pressure(clone, role, value):
    d = Path(clone) / ".squidsquad" / role
    d.mkdir(parents=True, exist_ok=True)
    (d / "context-pressure").write_text(str(value), encoding="utf-8")


class TestHealthReadsClonePressure13345(unittest.TestCase):
    def test_reads_from_clone_not_harness_root(self):
        with tempfile.TemporaryDirectory() as td:
            _write_pressure(td, "skill", "72")
            agent = _running_agent("skill", str(td))
            with patch.object(harness.state, "get_agent", return_value=agent):
                result = asyncio.run(harness.get_agent_health("skill"))
            self.assertEqual(result["context_pressure"], 72)

    def test_absent_clone_file_is_none(self):
        with tempfile.TemporaryDirectory() as td:
            agent = _running_agent("skill", str(td))  # no context-pressure file
            with patch.object(harness.state, "get_agent", return_value=agent):
                result = asyncio.run(harness.get_agent_health("skill"))
            self.assertIsNone(result["context_pressure"])

    def test_malformed_clone_file_is_none(self):
        with tempfile.TemporaryDirectory() as td:
            _write_pressure(td, "skill", "high")
            agent = _running_agent("skill", str(td))
            with patch.object(harness.state, "get_agent", return_value=agent):
                result = asyncio.run(harness.get_agent_health("skill"))
            self.assertIsNone(result["context_pressure"])

    def test_no_agent_is_safe(self):
        with patch.object(harness.state, "get_agent", return_value=None), \
             patch("harness.boot_remote._get_clone_path",
                   side_effect=RuntimeError("no clone")):
            result = asyncio.run(harness.get_agent_health("skill"))
        self.assertIsNone(result["context_pressure"])
        self.assertFalse(result["alive"])


if __name__ == "__main__":
    unittest.main()
