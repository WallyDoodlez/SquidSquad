"""Tests for #3644 — OpenAI adapter logs warning on malformed tool call JSON.

Verifies the adapter prints a warning to stderr instead of silently
substituting {} on JSONDecodeError.
"""
import pytest
from pathlib import Path

REPO = Path(__file__).parent.parent
ADAPTER = REPO / "references/scripts/providers/openai/adapter.py"


class TestOpenAIAdapterJSONWarning:
    """OpenAI adapter warns on malformed tool call args."""

    @pytest.fixture
    def source(self):
        return ADAPTER.read_text(encoding="utf-8")

    def test_warns_on_json_decode_error(self, source):
        """JSONDecodeError handler prints a warning, not silent."""
        # Find the except JSONDecodeError block
        idx = source.index("JSONDecodeError")
        block = source[idx:idx + 300]
        assert "stderr" in block or "WARNING" in block, \
            "JSONDecodeError handler should log to stderr"

    def test_includes_function_name_in_warning(self, source):
        """Warning includes the function name for diagnostics."""
        idx = source.index("JSONDecodeError")
        block = source[idx:idx + 300]
        assert "fn_name" in block

    def test_includes_raw_args_in_warning(self, source):
        """Warning includes the raw argument string."""
        idx = source.index("JSONDecodeError")
        block = source[idx:idx + 300]
        assert "arguments" in block

    def test_still_falls_back_to_empty_dict(self, source):
        """After warning, still falls back to {} to avoid crash."""
        idx = source.index("JSONDecodeError")
        block = source[idx:idx + 300]
        assert "fn_args = {}" in block
