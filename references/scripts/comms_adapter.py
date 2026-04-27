#!/usr/bin/env python3
"""SquidSquad communication adapter — platform-agnostic messaging interface.

Defines the abstract interface that all communication adapters (Telegram, Slack,
Discord, file-based, etc.) must implement. Agents use this to send messages,
create threads, and poll for responses without knowing the underlying platform.

Usage:
    from comms_adapter import get_adapter, Message
    adapter = get_adapter()  # reads config.md for provider
    adapter.send_message("general", "Hello from skill-lead")
    messages = adapter.read_messages("general", since=timestamp)

Config schema (in config.md):
    ## Communication
    - **Provider**: telegram | slack | discord | file | none
    - **Credentials Ref**: TELEGRAM_BOT_TOKEN  (key in ~/.squidsquad/secrets)
    - **Default Channel**: general
    - **Agent Channels**: skill:dev-chat, pm:pm-chat, qa:qa-chat
    - **Human Channel**: human
"""

import re
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
CONFIG_MD = REPO_ROOT / ".squidsquad" / "config.md"


# ---------------------------------------------------------------------------
# Message protocol
# ---------------------------------------------------------------------------

@dataclass
class Message:
    """Standardized message format for inter-agent communication.

    All messages follow this structure regardless of the underlying platform.
    The adapter converts to/from platform-native format.
    """
    sender: str               # Role identifier: "skill-lead", "pm-lead", "human"
    channel: str              # Channel/group name: "general", "dev-chat", etc.
    text: str                 # Message body (plain text or markdown)
    timestamp: float = 0.0    # Unix epoch when the message was sent
    thread_id: Optional[str] = None   # Thread/topic ID for threaded replies
    message_id: Optional[str] = None  # Platform-specific message ID
    metadata: dict = field(default_factory=dict)  # Extra platform-specific data

    def format_prefix(self) -> str:
        """Format the standard agent prefix for display."""
        ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(self.timestamp))
        return f"[{ts}] **{self.sender}**"


# ---------------------------------------------------------------------------
# Thread types
# ---------------------------------------------------------------------------

THREAD_TYPES = {
    "decision": "Consensus needed before acting",
    "question": "Quick question — answer expected",
    "escalation": "Needs human input to proceed",
    "fyi": "Informational — no response needed",
}


# ---------------------------------------------------------------------------
# Abstract adapter interface
# ---------------------------------------------------------------------------

class CommsAdapter(ABC):
    """Abstract base class for communication platform adapters.

    All communication adapters must implement these methods. The interface
    is designed to be platform-agnostic — Telegram, Slack, Discord, and
    file-based adapters all implement the same contract.
    """

    @abstractmethod
    def send_message(
        self,
        channel: str,
        text: str,
        thread_id: Optional[str] = None,
        sender: str = "",
    ) -> Optional[Message]:
        """Send a message to a channel.

        Args:
            channel: Channel/group name (e.g., "general", "dev-chat")
            text: Message body (plain text or markdown)
            thread_id: Optional thread ID for threaded replies
            sender: Role identifier of the sender (e.g., "skill-lead")

        Returns:
            The sent Message with platform-assigned message_id, or None on failure.
        """

    @abstractmethod
    def create_thread(
        self,
        channel: str,
        title: str,
        thread_type: str = "question",
        sender: str = "",
    ) -> Optional[str]:
        """Create a new thread/topic in a channel.

        Args:
            channel: Channel to create the thread in
            title: Thread title/subject
            thread_type: One of THREAD_TYPES keys
            sender: Role identifier of the creator

        Returns:
            The thread ID string, or None on failure.
        """

    @abstractmethod
    def read_messages(
        self,
        channel: str,
        since: Optional[float] = None,
        thread_id: Optional[str] = None,
        limit: int = 50,
    ) -> list[Message]:
        """Read messages from a channel, optionally filtered by time and thread.

        Args:
            channel: Channel to read from
            since: Unix epoch — only return messages after this time
            thread_id: If set, only return messages in this thread
            limit: Maximum number of messages to return

        Returns:
            List of Message objects, oldest first.
        """

    @abstractmethod
    def mention_user(self, user_id: str) -> str:
        """Format a user/role mention for the platform.

        Args:
            user_id: Role identifier (e.g., "pm-lead") or platform user ID

        Returns:
            Platform-formatted mention string (e.g., "@pm-lead", "<@U123>")
        """

    @abstractmethod
    def create_channel(self, name: str, description: str = "") -> bool:
        """Create a new channel/group.

        Args:
            name: Channel name (will be normalized by the platform)
            description: Optional channel description

        Returns:
            True if created (or already exists), False on failure.
        """

    @abstractmethod
    def upload_file(
        self,
        channel: str,
        path: str,
        caption: str = "",
        thread_id: Optional[str] = None,
    ) -> bool:
        """Upload a file to a channel.

        Args:
            channel: Channel to upload to
            path: Local file path
            caption: Optional caption/description
            thread_id: Optional thread to attach the file to

        Returns:
            True on success, False on failure.
        """

    @abstractmethod
    def check_connection(self) -> tuple[bool, str]:
        """Verify connectivity to the communication platform.

        Returns:
            (ok, message) — True if connected, with a status message.
        """


# ---------------------------------------------------------------------------
# Null adapter (no-op when comms not configured)
# ---------------------------------------------------------------------------

class NullAdapter(CommsAdapter):
    """No-op adapter used when communication is not configured.

    All operations silently succeed but do nothing. This allows agents
    to call comms methods without checking if comms are enabled.
    """

    def send_message(self, channel, text, thread_id=None, sender=""):
        return None

    def create_thread(self, channel, title, thread_type="question", sender=""):
        return None

    def read_messages(self, channel, since=None, thread_id=None, limit=50):
        return []

    def mention_user(self, user_id):
        return f"@{user_id}"

    def create_channel(self, name, description=""):
        return True

    def upload_file(self, channel, path, caption="", thread_id=None):
        return False

    def check_connection(self):
        return False, "Communication not configured (NullAdapter)"


# ---------------------------------------------------------------------------
# Config parsing
# ---------------------------------------------------------------------------

def _read_comms_config() -> dict:
    """Read Communication section from config.md.

    Returns dict with keys: provider, credentials_ref, default_channel,
    agent_channels, human_channel.
    """
    defaults = {
        "provider": "none",
        "credentials_ref": "",
        "default_channel": "general",
        "agent_channels": {},
        "human_channel": "human",
    }

    if not CONFIG_MD.exists():
        return defaults

    try:
        text = CONFIG_MD.read_text(encoding="utf-8")
        section_match = re.search(
            r"## Communication\s*\n(.*?)(?=\n## |\Z)", text, re.DOTALL
        )
        if not section_match:
            return defaults

        section = section_match.group(1)
        result = dict(defaults)

        m = re.search(r"\*\*Provider\*\*:\s*(.+)", section)
        if m:
            result["provider"] = m.group(1).strip().lower()

        m = re.search(r"\*\*Credentials Ref\*\*:\s*(.+)", section)
        if m:
            result["credentials_ref"] = m.group(1).strip()

        m = re.search(r"\*\*Default Channel\*\*:\s*(.+)", section)
        if m:
            result["default_channel"] = m.group(1).strip()

        m = re.search(r"\*\*Human Channel\*\*:\s*(.+)", section)
        if m:
            result["human_channel"] = m.group(1).strip()

        m = re.search(r"\*\*Agent Channels\*\*:\s*(.+)", section)
        if m:
            raw = m.group(1).strip()
            channels = {}
            for pair in raw.split(","):
                pair = pair.strip()
                if ":" in pair:
                    role, ch = pair.split(":", 1)
                    channels[role.strip()] = ch.strip()
            result["agent_channels"] = channels

        return result
    except Exception:
        return defaults


# ---------------------------------------------------------------------------
# Adapter registry and factory
# ---------------------------------------------------------------------------

_ADAPTER_REGISTRY: dict[str, type[CommsAdapter]] = {}


def register_adapter(provider: str, adapter_class: type[CommsAdapter]):
    """Register a communication adapter for a provider name."""
    _ADAPTER_REGISTRY[provider.lower()] = adapter_class


def get_adapter(config: Optional[dict] = None) -> CommsAdapter:
    """Get the communication adapter for the configured provider.

    Reads config.md Communication section. Returns NullAdapter if
    provider is "none" or not configured.
    """
    if config is None:
        config = _read_comms_config()

    provider = config.get("provider", "none").lower()

    if provider == "none" or not provider:
        return NullAdapter()

    adapter_class = _ADAPTER_REGISTRY.get(provider)
    if adapter_class is None:
        print(
            f"[comms] Unknown provider '{provider}'. "
            f"Available: {', '.join(_ADAPTER_REGISTRY.keys()) or 'none'}. "
            f"Using NullAdapter.",
            file=sys.stderr,
        )
        return NullAdapter()

    return adapter_class(config)


# ---------------------------------------------------------------------------
# CLI (for testing)
# ---------------------------------------------------------------------------

def main():
    """Simple CLI for testing comms adapter."""
    args = sys.argv[1:]
    if not args or args[0] in ("--help", "-h"):
        print(__doc__)
        return 0

    if args[0] == "check":
        adapter = get_adapter()
        ok, msg = adapter.check_connection()
        print(f"{'OK' if ok else 'FAIL'}: {msg}")
        return 0 if ok else 1

    if args[0] == "config":
        import json
        config = _read_comms_config()
        print(json.dumps(config, indent=2))
        return 0

    print(f"Unknown command: {args[0]}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
