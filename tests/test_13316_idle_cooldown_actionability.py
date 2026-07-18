"""Regression test for #13316 — idle-cooldown-loop.md's `drained` contract
was defined as strict `work_queue()` emptiness, but `work_queue()` returns
`approved` tasks regardless of whether they are autonomously pickable. An
approved task can be persistently human-gated or blocked on an unmet
dependency ("gated" is not a tracker status, so it was invisible to the
binary emptiness check) — a strict reading forces `absorb-work` on an item
that can't actually be picked up, starving idle-scan forever.

The fix redefines `drained` as "no autonomously-actionable item" (computed
by the agent reading each returned item), not raw queue non-emptiness.
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
IDLE_COOLDOWN_FILE = (
    REPO_ROOT / "references" / "sub-skills" / "common-events" / "idle-cooldown-loop.md"
)


@pytest.fixture
def idle_cooldown_text():
    assert IDLE_COOLDOWN_FILE.exists(), f"idle-cooldown-loop.md missing: {IDLE_COOLDOWN_FILE}"
    return IDLE_COOLDOWN_FILE.read_text(encoding="utf-8")


class TestDrainedIsActionabilityNotEmptiness:
    def test_step_b_drained_definition_mentions_actionable(self, idle_cooldown_text):
        idx = idle_cooldown_text.index("**Step B")
        section = idle_cooldown_text[idx:idx + 1500]
        assert "autonomously-actionable" in section

    def test_step_b_no_longer_defines_drained_as_bare_emptiness(self, idle_cooldown_text):
        # The old, strict definition must be gone -- not merely supplemented.
        assert "`drained=true` iff `work_queue()` returned empty" not in idle_cooldown_text

    def test_gated_or_dependency_blocked_explicitly_excluded(self, idle_cooldown_text):
        idx = idle_cooldown_text.index("**Step B")
        section = idle_cooldown_text[idx:idx + 1500]
        assert "gated" in section.lower()
        assert "dependency" in section.lower()

    def test_step_a_entry_condition_also_reframed(self, idle_cooldown_text):
        idx = idle_cooldown_text.index("**Step A")
        section = idle_cooldown_text[idx:idx + 300]
        assert "autonomously-actionable" in section

    def test_intro_paragraph_also_reframed(self, idle_cooldown_text):
        # The loop's top-level entry statement (before Step A/B) must match
        # the same actionability framing, not just the Step A/B details.
        intro = idle_cooldown_text[:idle_cooldown_text.index("### Two wake sources")]
        assert "autonomously-actionable" in intro

    def test_absorb_work_description_reframed(self, idle_cooldown_text):
        idx = idle_cooldown_text.index("`absorb-work`")
        section = idle_cooldown_text[idx:idx + 300]
        assert "actionable" in section.lower()
