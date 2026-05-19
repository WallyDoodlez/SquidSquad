"""Static hygiene checks for #4792 §5.9 / §5.10 — fragment edits and
recompose. Verifies the source fragment and composed CLAUDE.md files no
longer reference removed sentinels (`.health`, `.stop`, `.restart`,
`.stop-after-cycle`) and that the canonical strings introduced by §5.9
are present everywhere they need to be.
"""

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
LIFECYCLE_FRAGMENT = REPO / "references" / "sub-skills" / "common" / "agent-lifecycle.md"
PM_HEALTH_FRAGMENT = REPO / "references" / "sub-skills" / "roles" / "pm" / "health-check.md"
SHARED_INSTRUCTIONS = REPO / ".squidsquad" / "project" / "shared-instructions.md"

COMPOSED_CLAUDE_MD = [
    REPO / ".squidsquad" / role / "CLAUDE.md"
    for role in ("skill", "pm", "qa", "dm")
]

REMOVED_SENTINELS = (".health", ".stop", ".restart", ".stop-after-cycle")


class TestLifecycleFragment:
    """The shared agent-lifecycle sub-skill — primary edit target of §5.9."""

    def test_no_health_legacy_reference(self):
        text = LIFECYCLE_FRAGMENT.read_text(encoding="utf-8")
        assert ".health" not in text, (
            "`.health` legacy-fallback reference must be removed per CONTEXT-4792.md §5.9"
        )

    def test_canonical_liveness_phrase_present(self):
        text = LIFECYCLE_FRAGMENT.read_text(encoding="utf-8")
        assert "sole liveness signal" in text
        assert ".claude-pid" in text

    @pytest.mark.parametrize("removed", REMOVED_SENTINELS)
    def test_removed_sentinel_absent(self, removed):
        text = LIFECYCLE_FRAGMENT.read_text(encoding="utf-8")
        assert removed not in text, f"{removed!r} should be gone from agent-lifecycle.md"

    def test_lifecycle_interface_uses_squidsquad_cli(self):
        text = LIFECYCLE_FRAGMENT.read_text(encoding="utf-8")
        assert "squidsquad_cli.py start" in text
        assert "squidsquad_cli.py stop" in text
        assert "squidsquad_cli.py restart" in text

    def test_no_direct_start_team_invocation(self):
        """The runnable command block must not invoke `start_team.py` —
        operators should reach the harness via `squidsquad_cli`. A prose
        mention that `start_team.py` is a backward-compatible shim is fine."""
        text = LIFECYCLE_FRAGMENT.read_text(encoding="utf-8")
        assert "python references/scripts/start_team.py" not in text


class TestPmHealthCheckFragment:
    """PM health-check sub-skill — secondary edit target of §5.9."""

    def test_no_health_legacy_fallback_phrasing(self):
        text = PM_HEALTH_FRAGMENT.read_text(encoding="utf-8")
        assert "`.health` file (legacy fallback)" not in text
        assert ".health" not in text

    def test_mentions_claude_pid_or_status(self):
        text = PM_HEALTH_FRAGMENT.read_text(encoding="utf-8")
        # Either the .claude-pid file or the harness GET /status path should
        # be referenced as the source of truth.
        assert ".claude-pid" in text or "squidsquad_cli.py status" in text


class TestSharedInstructions:
    """L4 project shared-instructions — third copy of the agent-infra paragraph."""

    def test_no_health_legacy_reference(self):
        text = SHARED_INSTRUCTIONS.read_text(encoding="utf-8")
        assert ".health" not in text

    def test_canonical_liveness_phrase_present(self):
        text = SHARED_INSTRUCTIONS.read_text(encoding="utf-8")
        assert "sole liveness signal" in text
        assert ".claude-pid" in text

    def test_canonical_operator_entry_point(self):
        text = SHARED_INSTRUCTIONS.read_text(encoding="utf-8")
        assert "squidsquad_cli.py" in text


class TestComposedClaudeMd:
    """Composed CLAUDE.md files must mirror the cleaned fragments."""

    @pytest.mark.parametrize("composed", COMPOSED_CLAUDE_MD,
                             ids=lambda p: p.parent.name)
    def test_no_health_reference(self, composed):
        text = composed.read_text(encoding="utf-8")
        assert ".health" not in text, (
            f"{composed.parent.name}/CLAUDE.md still mentions .health — "
            "recompose pass is incomplete"
        )

    @pytest.mark.parametrize("composed", COMPOSED_CLAUDE_MD,
                             ids=lambda p: p.parent.name)
    def test_sole_liveness_signal_present(self, composed):
        text = composed.read_text(encoding="utf-8")
        assert "sole liveness signal" in text

    @pytest.mark.parametrize("composed", COMPOSED_CLAUDE_MD,
                             ids=lambda p: p.parent.name)
    def test_squidsquad_cli_canonical(self, composed):
        text = composed.read_text(encoding="utf-8")
        assert "squidsquad_cli.py start" in text


class TestComprehensionSpecExists:
    """The CQ spec for #4792 must exist and reference reachable source files."""

    def test_spec_file_exists(self):
        import json
        spec_path = REPO / "tests" / "comprehension" / "4792_spec.json"
        assert spec_path.exists()
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        assert spec["issue"] == 4792
        for rel in spec["files"]:
            assert (REPO / rel).exists(), f"spec references missing: {rel}"
        assert any("sole liveness signal" in q["question"].lower()
                   or "sole liveness signal" in q["expected"].lower()
                   for q in spec["questions"])
