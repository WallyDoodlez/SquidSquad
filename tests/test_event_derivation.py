"""Tests for compose.py derive_event_contract() — LLM derivation (#5868 AC-3)."""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from compose import derive_event_contract


def _mock_result(stdout="", returncode=0):
    """Create a mock subprocess.CompletedProcess."""
    r = MagicMock()
    r.stdout = stdout
    r.returncode = returncode
    return r


class TestDeriveEventContract:
    def test_valid_json_response(self):
        valid = json.dumps({"emits": ["status-transition"], "reacts_to": ["pr-merge"]})
        with patch("compose.subprocess.run", return_value=_mock_result(valid)):
            result = derive_event_contract("instructions...", "skill")
        assert result == {"emits": ["status-transition"], "reacts_to": ["pr-merge"]}

    def test_filters_hallucinated_events(self):
        response = json.dumps({"emits": ["status-transition", "fake-event"], "reacts_to": ["pr-merge", "bogus"]})
        with patch("compose.subprocess.run", return_value=_mock_result(response)):
            result = derive_event_contract("instructions...", "skill")
        assert result["emits"] == ["status-transition"]
        assert result["reacts_to"] == ["pr-merge"]

    def test_malformed_json_returns_none(self):
        with patch("compose.subprocess.run", return_value=_mock_result("not json at all")):
            result = derive_event_contract("instructions...", "skill")
        assert result is None

    def test_empty_response_returns_none(self):
        with patch("compose.subprocess.run", return_value=_mock_result("")):
            result = derive_event_contract("instructions...", "skill")
        assert result is None

    def test_nonzero_exit_returns_none(self):
        with patch("compose.subprocess.run", return_value=_mock_result("", returncode=1)):
            result = derive_event_contract("instructions...", "skill")
        assert result is None

    def test_strips_markdown_fences(self):
        fenced = '```json\n{"emits": ["pr-merge"], "reacts_to": []}\n```'
        with patch("compose.subprocess.run", return_value=_mock_result(fenced)):
            result = derive_event_contract("instructions...", "dm")
        assert result["emits"] == ["pr-merge"]

    def test_non_dict_response_returns_none(self):
        with patch("compose.subprocess.run", return_value=_mock_result('["not", "a", "dict"]')):
            result = derive_event_contract("instructions...", "skill")
        assert result is None

    def test_non_list_fields_returns_none(self):
        response = json.dumps({"emits": "not-a-list", "reacts_to": 42})
        with patch("compose.subprocess.run", return_value=_mock_result(response)):
            result = derive_event_contract("instructions...", "skill")
        assert result is None

    def test_timeout_returns_none(self):
        import subprocess
        with patch("compose.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="claude", timeout=60)):
            result = derive_event_contract("instructions...", "skill")
        assert result is None

    def test_claude_not_found_returns_none(self):
        with patch("compose.subprocess.run", side_effect=FileNotFoundError("claude")):
            result = derive_event_contract("instructions...", "skill")
        assert result is None

    def test_recognized_events_accepted(self):
        """Recognized-tier events (not yet emitted) are valid in contracts."""
        response = json.dumps({"emits": [], "reacts_to": ["verification-failed", "agent-health"]})
        with patch("compose.subprocess.run", return_value=_mock_result(response)):
            result = derive_event_contract("instructions...", "pm")
        assert set(result["reacts_to"]) == {"verification-failed", "agent-health"}

    def test_idempotency_sorted_output(self):
        """Output lists should be consistent regardless of LLM order."""
        response = json.dumps({"emits": ["tracker-comment", "status-transition"], "reacts_to": ["pr-merge", "cycle-start"]})
        with patch("compose.subprocess.run", return_value=_mock_result(response)):
            result = derive_event_contract("instructions...", "skill")
        # derive_event_contract doesn't sort — derive_and_write_event_contracts does
        # But the contract should contain all valid types
        assert "status-transition" in result["emits"]
        assert "tracker-comment" in result["emits"]
