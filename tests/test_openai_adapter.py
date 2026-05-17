"""Behavioral tests for providers/openai/adapter.py — call() tool-use loop.

Tests cover: single-turn call, multi-turn tool-use loop, max_iterations cap,
missing API key, base_url routing, and malformed tool call JSON warning.
"""

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import pytest

# Add scripts dir to path for imports
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))


# ---------------------------------------------------------------------------
# Helpers — build mock OpenAI response objects
# ---------------------------------------------------------------------------

def _make_message(content=None, tool_calls=None):
    """Build a mock ChatCompletionMessage."""
    msg = SimpleNamespace(content=content, tool_calls=tool_calls)
    return msg


def _make_tool_call(tc_id, name, arguments):
    """Build a mock tool call object."""
    return SimpleNamespace(
        id=tc_id,
        function=SimpleNamespace(name=name, arguments=arguments),
    )


def _make_response(content=None, tool_calls=None):
    """Build a mock ChatCompletion response."""
    msg = _make_message(content=content, tool_calls=tool_calls)
    choice = SimpleNamespace(message=msg)
    return SimpleNamespace(choices=[choice])


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clean_module_cache():
    """Ensure fresh import of adapter for each test."""
    for key in list(sys.modules):
        if "providers.openai.adapter" in key or key == "providers.openai.adapter":
            del sys.modules[key]
    yield
    for key in list(sys.modules):
        if "providers.openai.adapter" in key or key == "providers.openai.adapter":
            del sys.modules[key]


@pytest.fixture
def mock_openai():
    """Patch openai import and return a controllable mock client."""
    mock_module = MagicMock()
    mock_client = MagicMock()
    mock_module.OpenAI.return_value = mock_client

    with patch.dict(sys.modules, {"openai": mock_module}):
        yield mock_module, mock_client


@pytest.fixture
def env_api_key(monkeypatch):
    """Set OPENAI_API_KEY in environment."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")


@pytest.fixture
def adapter(mock_openai, env_api_key):
    """Import adapter with mocked openai and API key set."""
    # Ensure shared_fs is not importable so adapter falls back to os.environ
    with patch.dict(sys.modules, {"shared_fs": None}):
        from providers.openai import adapter
        return adapter


# ---------------------------------------------------------------------------
# Tests — Single-turn call (no tools)
# ---------------------------------------------------------------------------

class TestSingleTurnCall:
    """call() with no tool calls returns the text response."""

    def test_returns_text_content(self, adapter, mock_openai):
        _, client = mock_openai
        client.chat.completions.create.return_value = _make_response(
            content="Hello, world!"
        )

        result = adapter.call(
            model="gpt-4",
            system_prompt="You are helpful.",
            user_prompt="Say hello.",
            tools=None,
            tool_handler=lambda n, a: "",
        )

        assert result == "Hello, world!"

    def test_returns_empty_string_when_content_is_none(self, adapter, mock_openai):
        _, client = mock_openai
        client.chat.completions.create.return_value = _make_response(content=None)

        result = adapter.call(
            model="gpt-4",
            system_prompt="sys",
            user_prompt="usr",
            tools=None,
            tool_handler=lambda n, a: "",
        )

        assert result == ""

    def test_sends_system_and_user_messages(self, adapter, mock_openai):
        _, client = mock_openai
        client.chat.completions.create.return_value = _make_response(content="ok")

        adapter.call(
            model="gpt-4",
            system_prompt="Be terse.",
            user_prompt="What is 2+2?",
            tools=None,
            tool_handler=lambda n, a: "",
        )

        call_kwargs = client.chat.completions.create.call_args[1]
        messages = call_kwargs["messages"]
        assert messages[0] == {"role": "system", "content": "Be terse."}
        assert messages[1] == {"role": "user", "content": "What is 2+2?"}

    def test_no_tools_kwarg_when_tools_is_none(self, adapter, mock_openai):
        _, client = mock_openai
        client.chat.completions.create.return_value = _make_response(content="ok")

        adapter.call(
            model="gpt-4",
            system_prompt="sys",
            user_prompt="usr",
            tools=None,
            tool_handler=lambda n, a: "",
        )

        call_kwargs = client.chat.completions.create.call_args[1]
        assert "tools" not in call_kwargs
        assert "tool_choice" not in call_kwargs


# ---------------------------------------------------------------------------
# Tests — Multi-turn tool-use loop
# ---------------------------------------------------------------------------

class TestMultiTurnToolUse:
    """call() with tool calls loops until a text-only response."""

    def test_single_tool_call_round(self, adapter, mock_openai):
        _, client = mock_openai

        tool_response = _make_response(tool_calls=[
            _make_tool_call("tc_1", "get_weather", '{"city": "NYC"}'),
        ])
        final_response = _make_response(content="It's sunny in NYC.")

        client.chat.completions.create.side_effect = [tool_response, final_response]

        handler = MagicMock(return_value="72°F, sunny")

        result = adapter.call(
            model="gpt-4",
            system_prompt="sys",
            user_prompt="Weather in NYC?",
            tools=[{"type": "function", "function": {"name": "get_weather"}}],
            tool_handler=handler,
        )

        assert result == "It's sunny in NYC."
        handler.assert_called_once_with("get_weather", {"city": "NYC"})

    def test_multiple_tool_calls_in_one_response(self, adapter, mock_openai):
        _, client = mock_openai

        tool_response = _make_response(tool_calls=[
            _make_tool_call("tc_1", "fn_a", '{"x": 1}'),
            _make_tool_call("tc_2", "fn_b", '{"y": 2}'),
        ])
        final_response = _make_response(content="Done.")

        client.chat.completions.create.side_effect = [tool_response, final_response]

        calls_log = []

        def handler(name, args):
            calls_log.append((name, args))
            return f"result_{name}"

        result = adapter.call(
            model="gpt-4",
            system_prompt="sys",
            user_prompt="usr",
            tools=[{"type": "function", "function": {"name": "fn_a"}}],
            tool_handler=handler,
        )

        assert result == "Done."
        assert calls_log == [("fn_a", {"x": 1}), ("fn_b", {"y": 2})]

    def test_two_round_tool_use(self, adapter, mock_openai):
        _, client = mock_openai

        round1 = _make_response(tool_calls=[
            _make_tool_call("tc_1", "search", '{"q": "python"}'),
        ])
        round2 = _make_response(tool_calls=[
            _make_tool_call("tc_2", "read", '{"url": "docs.python.org"}'),
        ])
        final = _make_response(content="Python is a language.")

        client.chat.completions.create.side_effect = [round1, round2, final]

        result = adapter.call(
            model="gpt-4",
            system_prompt="sys",
            user_prompt="usr",
            tools=[{"type": "function", "function": {"name": "search"}}],
            tool_handler=lambda n, a: "ok",
        )

        assert result == "Python is a language."
        assert client.chat.completions.create.call_count == 3

    def test_tool_results_appended_to_messages(self, adapter, mock_openai):
        _, client = mock_openai

        tool_response = _make_response(tool_calls=[
            _make_tool_call("tc_42", "calc", '{"expr": "2+2"}'),
        ])
        final_response = _make_response(content="4")

        client.chat.completions.create.side_effect = [tool_response, final_response]

        adapter.call(
            model="gpt-4",
            system_prompt="sys",
            user_prompt="usr",
            tools=[{"type": "function", "function": {"name": "calc"}}],
            tool_handler=lambda n, a: "4",
        )

        # Second call should include tool result message
        second_call_kwargs = client.chat.completions.create.call_args_list[1][1]
        messages = second_call_kwargs["messages"]
        tool_msg = [m for m in messages if isinstance(m, dict) and m.get("role") == "tool"]
        assert len(tool_msg) == 1
        assert tool_msg[0]["tool_call_id"] == "tc_42"
        assert tool_msg[0]["content"] == "4"


# ---------------------------------------------------------------------------
# Tests — Max iterations safety cap
# ---------------------------------------------------------------------------

class TestMaxIterationsCap:
    """call() raises RuntimeError after 50 tool-use iterations."""

    def test_raises_after_50_iterations(self, adapter, mock_openai):
        _, client = mock_openai

        # Every response has tool calls — never terminates
        endless_tool_response = _make_response(tool_calls=[
            _make_tool_call("tc_loop", "noop", "{}"),
        ])
        client.chat.completions.create.return_value = endless_tool_response

        with pytest.raises(RuntimeError, match="max iterations.*50"):
            adapter.call(
                model="gpt-4",
                system_prompt="sys",
                user_prompt="usr",
                tools=[{"type": "function", "function": {"name": "noop"}}],
                tool_handler=lambda n, a: "ok",
            )

        assert client.chat.completions.create.call_count == 50


# ---------------------------------------------------------------------------
# Tests — Missing API key
# ---------------------------------------------------------------------------

class TestMissingAPIKey:
    """call() raises RuntimeError when API key is not set."""

    def test_raises_when_no_api_key(self, mock_openai, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        with patch.dict(sys.modules, {"shared_fs": None}):
            from providers.openai import adapter

            with pytest.raises(RuntimeError, match="OPENAI_API_KEY.*not found"):
                adapter.call(
                    model="gpt-4",
                    system_prompt="sys",
                    user_prompt="usr",
                    tools=None,
                    tool_handler=lambda n, a: "",
                )

    def test_raises_for_custom_api_key_env(self, mock_openai, monkeypatch):
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

        with patch.dict(sys.modules, {"shared_fs": None}):
            from providers.openai import adapter

            with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY.*not found"):
                adapter.call(
                    model="deepseek-r1",
                    system_prompt="sys",
                    user_prompt="usr",
                    tools=None,
                    tool_handler=lambda n, a: "",
                    api_key_env="DEEPSEEK_API_KEY",
                )


# ---------------------------------------------------------------------------
# Tests — base_url routing
# ---------------------------------------------------------------------------

class TestBaseURLRouting:
    """call() passes base_url to OpenAI client when specified."""

    def test_base_url_passed_to_client(self, adapter, mock_openai):
        mock_module, client = mock_openai
        client.chat.completions.create.return_value = _make_response(content="ok")

        adapter.call(
            model="deepseek-r1",
            system_prompt="sys",
            user_prompt="usr",
            tools=None,
            tool_handler=lambda n, a: "",
            base_url="https://api.deepseek.com/v1",
        )

        constructor_kwargs = mock_module.OpenAI.call_args[1]
        assert constructor_kwargs["base_url"] == "https://api.deepseek.com/v1"

    def test_no_base_url_when_not_specified(self, adapter, mock_openai):
        mock_module, client = mock_openai
        client.chat.completions.create.return_value = _make_response(content="ok")

        adapter.call(
            model="gpt-4",
            system_prompt="sys",
            user_prompt="usr",
            tools=None,
            tool_handler=lambda n, a: "",
        )

        constructor_kwargs = mock_module.OpenAI.call_args[1]
        assert "base_url" not in constructor_kwargs

    def test_custom_api_key_env_used(self, adapter, mock_openai, monkeypatch):
        mock_module, client = mock_openai
        client.chat.completions.create.return_value = _make_response(content="ok")
        monkeypatch.setenv("DEEPSEEK_API_KEY", "ds-key-456")

        # Re-import to pick up the new env var
        for key in list(sys.modules):
            if "providers.openai.adapter" in key:
                del sys.modules[key]

        with patch.dict(sys.modules, {"shared_fs": None}):
            from providers.openai import adapter as fresh_adapter

            fresh_adapter.call(
                model="deepseek-r1",
                system_prompt="sys",
                user_prompt="usr",
                tools=None,
                tool_handler=lambda n, a: "",
                api_key_env="DEEPSEEK_API_KEY",
            )

        constructor_kwargs = mock_module.OpenAI.call_args[1]
        assert constructor_kwargs["api_key"] == "ds-key-456"


# ---------------------------------------------------------------------------
# Tests — Malformed tool call JSON
# ---------------------------------------------------------------------------

class TestMalformedToolCallJSON:
    """call() warns on malformed JSON and falls back to empty dict."""

    def test_warns_and_falls_back_on_bad_json(self, adapter, mock_openai, capsys):
        _, client = mock_openai

        tool_response = _make_response(tool_calls=[
            _make_tool_call("tc_bad", "broken_fn", "not valid json{{{"),
        ])
        final_response = _make_response(content="recovered")

        client.chat.completions.create.side_effect = [tool_response, final_response]

        calls_log = []

        def handler(name, args):
            calls_log.append((name, args))
            return "ok"

        result = adapter.call(
            model="gpt-4",
            system_prompt="sys",
            user_prompt="usr",
            tools=[{"type": "function", "function": {"name": "broken_fn"}}],
            tool_handler=handler,
        )

        assert result == "recovered"
        # Handler was called with empty dict fallback
        assert calls_log == [("broken_fn", {})]
        # Warning printed to stderr
        captured = capsys.readouterr()
        assert "WARNING" in captured.err
        assert "broken_fn" in captured.err


# ---------------------------------------------------------------------------
# Tests — API error handling
# ---------------------------------------------------------------------------

class TestAPIErrorHandling:
    """call() wraps API exceptions in RuntimeError."""

    def test_wraps_api_exception(self, adapter, mock_openai):
        _, client = mock_openai
        client.chat.completions.create.side_effect = Exception("connection refused")

        with pytest.raises(RuntimeError, match="OpenAI API error.*connection refused"):
            adapter.call(
                model="gpt-4",
                system_prompt="sys",
                user_prompt="usr",
                tools=None,
                tool_handler=lambda n, a: "",
            )
