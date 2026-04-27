"""Tests for references/scripts/comms_adapter.py — communication adapter interface."""

import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import comms_adapter


# ---------------------------------------------------------------------------
# Message protocol
# ---------------------------------------------------------------------------

class TestMessage:
    def test_creates_message(self):
        msg = comms_adapter.Message(
            sender="skill-lead",
            channel="general",
            text="Hello",
            timestamp=time.time(),
        )
        assert msg.sender == "skill-lead"
        assert msg.channel == "general"
        assert msg.text == "Hello"

    def test_default_fields(self):
        msg = comms_adapter.Message(sender="pm", channel="ch", text="hi")
        assert msg.thread_id is None
        assert msg.message_id is None
        assert msg.metadata == {}
        assert msg.timestamp == 0.0

    def test_format_prefix(self):
        msg = comms_adapter.Message(
            sender="qa-lead",
            channel="general",
            text="test",
            timestamp=1777205526.0,
        )
        prefix = msg.format_prefix()
        assert "qa-lead" in prefix
        assert "**" in prefix  # Bold formatting


# ---------------------------------------------------------------------------
# NullAdapter (no-op)
# ---------------------------------------------------------------------------

class TestNullAdapter:
    def test_send_returns_none(self):
        adapter = comms_adapter.NullAdapter()
        assert adapter.send_message("ch", "hi") is None

    def test_create_thread_returns_none(self):
        adapter = comms_adapter.NullAdapter()
        assert adapter.create_thread("ch", "title") is None

    def test_read_returns_empty(self):
        adapter = comms_adapter.NullAdapter()
        assert adapter.read_messages("ch") == []

    def test_mention_formats_at_prefix(self):
        adapter = comms_adapter.NullAdapter()
        assert adapter.mention_user("pm-lead") == "@pm-lead"

    def test_create_channel_returns_true(self):
        adapter = comms_adapter.NullAdapter()
        assert adapter.create_channel("test") is True

    def test_upload_returns_false(self):
        adapter = comms_adapter.NullAdapter()
        assert adapter.upload_file("ch", "/tmp/file.txt") is False

    def test_check_connection_returns_false(self):
        adapter = comms_adapter.NullAdapter()
        ok, msg = adapter.check_connection()
        assert ok is False
        assert "NullAdapter" in msg


# ---------------------------------------------------------------------------
# Interface contract (mock adapter)
# ---------------------------------------------------------------------------

class MockAdapter(comms_adapter.CommsAdapter):
    """Concrete adapter for testing the interface contract."""

    def __init__(self, config=None):
        self.sent = []
        self.threads = {}
        self.channels = set()

    def send_message(self, channel, text, thread_id=None, sender=""):
        msg = comms_adapter.Message(
            sender=sender,
            channel=channel,
            text=text,
            timestamp=time.time(),
            thread_id=thread_id,
            message_id=f"msg-{len(self.sent)}",
        )
        self.sent.append(msg)
        return msg

    def create_thread(self, channel, title, thread_type="question", sender=""):
        tid = f"thread-{len(self.threads)}"
        self.threads[tid] = {"channel": channel, "title": title, "type": thread_type}
        return tid

    def read_messages(self, channel, since=None, thread_id=None, limit=50):
        msgs = [m for m in self.sent if m.channel == channel]
        if thread_id:
            msgs = [m for m in msgs if m.thread_id == thread_id]
        if since:
            msgs = [m for m in msgs if m.timestamp > since]
        return msgs[:limit]

    def mention_user(self, user_id):
        return f"@{user_id}"

    def create_channel(self, name, description=""):
        self.channels.add(name)
        return True

    def upload_file(self, channel, path, caption="", thread_id=None):
        return True

    def check_connection(self):
        return True, "MockAdapter connected"


class TestMockAdapterContract:
    """Validates the interface contract using a concrete mock adapter."""

    def test_send_returns_message(self):
        adapter = MockAdapter()
        msg = adapter.send_message("general", "test", sender="skill-lead")
        assert isinstance(msg, comms_adapter.Message)
        assert msg.text == "test"
        assert msg.message_id is not None

    def test_create_thread_returns_id(self):
        adapter = MockAdapter()
        tid = adapter.create_thread("general", "Discussion", thread_type="decision")
        assert tid is not None
        assert isinstance(tid, str)

    def test_threaded_reply(self):
        adapter = MockAdapter()
        tid = adapter.create_thread("dev", "Bug discussion")
        adapter.send_message("dev", "I found a bug", thread_id=tid, sender="skill-lead")
        adapter.send_message("dev", "Can you elaborate?", thread_id=tid, sender="pm-lead")
        msgs = adapter.read_messages("dev", thread_id=tid)
        assert len(msgs) == 2
        assert msgs[0].sender == "skill-lead"
        assert msgs[1].sender == "pm-lead"

    def test_read_filters_by_channel(self):
        adapter = MockAdapter()
        adapter.send_message("general", "msg1", sender="pm")
        adapter.send_message("dev-chat", "msg2", sender="skill")
        assert len(adapter.read_messages("general")) == 1
        assert len(adapter.read_messages("dev-chat")) == 1

    def test_create_channel(self):
        adapter = MockAdapter()
        assert adapter.create_channel("new-channel", "test channel") is True
        assert "new-channel" in adapter.channels

    def test_check_connection(self):
        adapter = MockAdapter()
        ok, msg = adapter.check_connection()
        assert ok is True


# ---------------------------------------------------------------------------
# Config parsing
# ---------------------------------------------------------------------------

class TestReadCommsConfig:
    def test_defaults_when_no_config(self, tmp_path):
        with patch.object(comms_adapter, "CONFIG_MD", tmp_path / "nonexistent"):
            config = comms_adapter._read_comms_config()
        assert config["provider"] == "none"
        assert config["default_channel"] == "general"

    def test_parses_full_config(self, tmp_path):
        config_file = tmp_path / "config.md"
        config_file.write_text(
            "# Config\n\n## Communication\n\n"
            "- **Provider**: telegram\n"
            "- **Credentials Ref**: TELEGRAM_BOT_TOKEN\n"
            "- **Default Channel**: squad-general\n"
            "- **Agent Channels**: skill:dev-chat, pm:pm-chat\n"
            "- **Human Channel**: human-dm\n\n"
            "## Other Section\n",
            encoding="utf-8",
        )
        with patch.object(comms_adapter, "CONFIG_MD", config_file):
            config = comms_adapter._read_comms_config()
        assert config["provider"] == "telegram"
        assert config["credentials_ref"] == "TELEGRAM_BOT_TOKEN"
        assert config["default_channel"] == "squad-general"
        assert config["agent_channels"] == {"skill": "dev-chat", "pm": "pm-chat"}
        assert config["human_channel"] == "human-dm"

    def test_missing_section_returns_defaults(self, tmp_path):
        config_file = tmp_path / "config.md"
        config_file.write_text("# Config\n\n## Other\n- stuff\n", encoding="utf-8")
        with patch.object(comms_adapter, "CONFIG_MD", config_file):
            config = comms_adapter._read_comms_config()
        assert config["provider"] == "none"


# ---------------------------------------------------------------------------
# Adapter registry
# ---------------------------------------------------------------------------

class TestAdapterRegistry:
    def test_register_and_get(self):
        comms_adapter.register_adapter("mock", MockAdapter)
        adapter = comms_adapter.get_adapter({"provider": "mock"})
        assert isinstance(adapter, MockAdapter)
        # Cleanup
        del comms_adapter._ADAPTER_REGISTRY["mock"]

    def test_none_provider_returns_null(self):
        adapter = comms_adapter.get_adapter({"provider": "none"})
        assert isinstance(adapter, comms_adapter.NullAdapter)

    def test_unknown_provider_returns_null(self):
        adapter = comms_adapter.get_adapter({"provider": "unknownplatform"})
        assert isinstance(adapter, comms_adapter.NullAdapter)

    def test_empty_provider_returns_null(self):
        adapter = comms_adapter.get_adapter({"provider": ""})
        assert isinstance(adapter, comms_adapter.NullAdapter)


# ---------------------------------------------------------------------------
# Thread types
# ---------------------------------------------------------------------------

class TestThreadTypes:
    def test_all_types_have_descriptions(self):
        for key, desc in comms_adapter.THREAD_TYPES.items():
            assert isinstance(key, str)
            assert isinstance(desc, str)
            assert len(desc) > 0

    def test_required_types_exist(self):
        assert "decision" in comms_adapter.THREAD_TYPES
        assert "question" in comms_adapter.THREAD_TYPES
        assert "escalation" in comms_adapter.THREAD_TYPES
        assert "fyi" in comms_adapter.THREAD_TYPES
