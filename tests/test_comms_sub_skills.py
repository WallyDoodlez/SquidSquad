"""Tests for communication sub-skills — chat-etiquette, mention-protocol, consensus-protocol."""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SUB_SKILLS_DIR = REPO_ROOT / "references" / "sub-skills" / "common"


# ---------------------------------------------------------------------------
# Sub-skill existence and structure
# ---------------------------------------------------------------------------

class TestSubSkillFiles:
    @pytest.mark.parametrize("name", [
        "chat-etiquette",
        "mention-protocol",
        "consensus-protocol",
    ])
    def test_sub_skill_exists(self, name):
        path = SUB_SKILLS_DIR / f"{name}.md"
        assert path.exists(), f"{name}.md not found in {SUB_SKILLS_DIR}"

    @pytest.mark.parametrize("name", [
        "chat-etiquette",
        "mention-protocol",
        "consensus-protocol",
    ])
    def test_sub_skill_has_heading(self, name):
        """Each sub-skill starts with a ## heading."""
        content = (SUB_SKILLS_DIR / f"{name}.md").read_text(encoding="utf-8")
        assert content.startswith("## "), f"{name}.md must start with ## heading"

    @pytest.mark.parametrize("name", [
        "chat-etiquette",
        "mention-protocol",
        "consensus-protocol",
    ])
    def test_sub_skill_references_adapter(self, name):
        """Sub-skills reference the adapter interface, not platform APIs."""
        content = (SUB_SKILLS_DIR / f"{name}.md").read_text(encoding="utf-8")
        assert "comms_adapter" in content or "adapter" in content.lower(), \
            f"{name}.md must reference the adapter interface"

    @pytest.mark.parametrize("name", [
        "chat-etiquette",
        "mention-protocol",
        "consensus-protocol",
    ])
    def test_no_platform_specific_references(self, name):
        """Sub-skills must not reference specific platforms directly in rules."""
        content = (SUB_SKILLS_DIR / f"{name}.md").read_text(encoding="utf-8")
        # Platform names should only appear in comments or examples, not as rules
        # We check the content doesn't have "use Telegram" or "call Slack API" style directives
        for platform in ["telegram api", "slack api", "discord api"]:
            assert platform not in content.lower(), \
                f"{name}.md must not reference '{platform}' — use adapter interface"


# ---------------------------------------------------------------------------
# Deterministic rules (no "use your judgment")
# ---------------------------------------------------------------------------

class TestDeterministicRules:
    @pytest.mark.parametrize("name", [
        "chat-etiquette",
        "mention-protocol",
        "consensus-protocol",
    ])
    def test_no_judgment_clauses(self, name):
        """Sub-skills must have deterministic rules — no vague judgment clauses."""
        content = (SUB_SKILLS_DIR / f"{name}.md").read_text(encoding="utf-8")
        vague_phrases = ["use your judgment", "use your discretion", "as you see fit"]
        for phrase in vague_phrases:
            assert phrase not in content.lower(), \
                f"{name}.md contains vague clause '{phrase}' — rules must be deterministic"


# ---------------------------------------------------------------------------
# Chat etiquette specifics
# ---------------------------------------------------------------------------

class TestChatEtiquette:
    def test_has_thread_creation_rules(self):
        content = (SUB_SKILLS_DIR / "chat-etiquette.md").read_text(encoding="utf-8")
        assert "thread" in content.lower()
        assert "create" in content.lower() or "when to" in content.lower()

    def test_has_message_format_rules(self):
        content = (SUB_SKILLS_DIR / "chat-etiquette.md").read_text(encoding="utf-8")
        assert "format" in content.lower() or "prefix" in content.lower()

    def test_has_code_snippet_rules(self):
        content = (SUB_SKILLS_DIR / "chat-etiquette.md").read_text(encoding="utf-8")
        assert "code" in content.lower() or "snippet" in content.lower()


# ---------------------------------------------------------------------------
# Mention protocol specifics
# ---------------------------------------------------------------------------

class TestMentionProtocol:
    def test_has_escalation_tiers(self):
        content = (SUB_SKILLS_DIR / "mention-protocol.md").read_text(encoding="utf-8")
        assert "tier" in content.lower() or "escalation" in content.lower()

    def test_has_when_to_mention_human(self):
        content = (SUB_SKILLS_DIR / "mention-protocol.md").read_text(encoding="utf-8")
        assert "human" in content.lower()
        assert "mention" in content.lower()

    def test_has_noise_budget(self):
        content = (SUB_SKILLS_DIR / "mention-protocol.md").read_text(encoding="utf-8")
        assert "budget" in content.lower() or "limit" in content.lower()


# ---------------------------------------------------------------------------
# Consensus protocol specifics
# ---------------------------------------------------------------------------

class TestConsensusProtocol:
    def test_has_decision_flow(self):
        content = (SUB_SKILLS_DIR / "consensus-protocol.md").read_text(encoding="utf-8")
        assert "decision" in content.lower()
        assert "lock" in content.lower()

    def test_has_timeout_handling(self):
        content = (SUB_SKILLS_DIR / "consensus-protocol.md").read_text(encoding="utf-8")
        assert "timeout" in content.lower()

    def test_has_quorum(self):
        content = (SUB_SKILLS_DIR / "consensus-protocol.md").read_text(encoding="utf-8")
        assert "quorum" in content.lower() or "minimum" in content.lower()

    def test_has_voting_mechanism(self):
        content = (SUB_SKILLS_DIR / "consensus-protocol.md").read_text(encoding="utf-8")
        assert "agree" in content.lower()
        assert "disagree" in content.lower()


# ---------------------------------------------------------------------------
# Manifest registration
# ---------------------------------------------------------------------------

class TestManifestRegistration:
    def test_sub_skills_in_manifest(self):
        manifest = (REPO_ROOT / "references" / "sub-skills" / "manifest.md").read_text(encoding="utf-8")
        for name in ["chat-etiquette", "mention-protocol", "consensus-protocol"]:
            assert name in manifest, f"{name} not registered in manifest.md"
