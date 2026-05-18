"""Content-coverage tests for the event-mode L1 base fragments (#8915).

Backs TEST-PLAN-8694.md AC-5 / AC-6 / AC-7 measurable refinements at the
file-level (not the composed-CLAUDE.md level — that wiring is a separate
follow-up cycle).

These tests are deliberately narrow: they only check the fragments authored
in this PR. Pre-existing files in `common-events/` (e.g. the legacy
`event-driven-workflow.md` that PM flagged for removal) are excluded.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
COMMON_EVENTS = REPO_ROOT / "references" / "sub-skills" / "common-events"

# Fragments authored under #8915 cycle 1136. Each must exist, be non-empty,
# and obey the AC-5 / AC-6 / AC-7 rules.
NEW_FRAGMENTS = [
    "l1-base.md",
    "cursor-management.md",
    "forge-read-pattern.md",
    "idle-cooldown-loop.md",
    "comment-handling.md",
]


@pytest.fixture(scope="module")
def fragment_texts():
    return {
        name: (COMMON_EVENTS / name).read_text(encoding="utf-8")
        for name in NEW_FRAGMENTS
    }


class TestFragmentsExist:
    @pytest.mark.parametrize("name", NEW_FRAGMENTS)
    def test_fragment_file_exists(self, name):
        path = COMMON_EVENTS / name
        assert path.exists(), f"missing fragment: {path}"
        assert path.read_text(encoding="utf-8").strip(), (
            f"fragment {name} is empty"
        )


class TestAc5NoModeConditional:
    """AC-5 M-5.1, M-5.2: no mode-conditional language inside the new
    fragments. Forbidden tokens: `event-driven:`, `if /loop`, `cycle_pre`,
    `cycle_post`, `30-minute`, `/loop` (these belong to the loop-mode
    fragment tree only).
    """

    FORBIDDEN = [
        "event-driven:",
        "if /loop",
        "cycle_pre",
        "cycle_post",
        "30-minute",
        "/loop",
    ]

    @pytest.mark.parametrize("name", NEW_FRAGMENTS)
    @pytest.mark.parametrize("token", FORBIDDEN)
    def test_fragment_has_no_forbidden_token(self, fragment_texts, name,
                                              token):
        text = fragment_texts[name]
        assert token not in text, (
            f"{name} contains forbidden mode-conditional token: {token!r}"
        )


class TestAc6NoStandaloneBootFragment:
    """AC-6 M-6.1: no `l1-boot.md` file exists; the boot sequence lives
    inside `l1-base.md`."""

    def test_no_l1_boot_fragment_anywhere(self):
        matches = list(REPO_ROOT.glob("references/sub-skills/**/l1-boot.md"))
        assert matches == [], (
            f"l1-boot.md must not exist; found: {matches}"
        )

    def test_l1_base_contains_boot_sequence_header(self, fragment_texts):
        # AC-6 M-6.2: the boot sequence text appears inside the L1 base
        # fragment, not a standalone l1-boot.md.
        text = fragment_texts["l1-base.md"]
        assert re.search(r"(?im)^\s*###?\s+Boot Sequence", text), (
            "l1-base.md must contain a 'Boot Sequence' section header"
        )


class TestAc7TopicCoverage:
    """AC-7 M-7.1: each topic from CONTEXT.md §5.1 Deliverables must have
    at least one section header (## or ###) in the new fragments."""

    @pytest.mark.parametrize("topic_regex,where", [
        # (case-insensitive regex matched against headers, fragment name)
        (r"boot sequence", "l1-base.md"),
        (r"how you listen|event poll", "l1-base.md"),
        (r"case b\b", "l1-base.md"),
        (r"case c\b", "l1-base.md"),
        (r"case d\b", "l1-base.md"),
        (r"case e\b", "l1-base.md"),
        (r"atomic update protocol", "cursor-management.md"),
        (r"per-event advance|per-batch", "cursor-management.md"),
        (r"gap scenarios", "cursor-management.md"),
        (r"forge-read pattern|forge-read", "forge-read-pattern.md"),
        (r"idle.*improvement.scan.*cool.?down|cool.?down loop",
         "idle-cooldown-loop.md"),
        (r"working-state schema", "idle-cooldown-loop.md"),
        (r"comment handling|the rule", "comment-handling.md"),
        (r"dm exception|end.?of.?task re.?read", "comment-handling.md"),
        (r"transition.?on.?handoff", "comment-handling.md"),
    ])
    def test_topic_has_header(self, fragment_texts, topic_regex, where):
        text = fragment_texts[where]
        headers = re.findall(r"^#{1,6}\s+(.+)$", text, flags=re.MULTILINE)
        match = next((h for h in headers
                      if re.search(topic_regex, h, re.IGNORECASE)), None)
        assert match is not None, (
            f"{where} missing header matching /{topic_regex}/; "
            f"have: {headers}"
        )


class TestWikilinkResolution:
    """Wikilinks between the new fragments must resolve to actual files
    in `common-events/` (or be documented as forward references)."""

    def test_all_wikilinks_resolve(self, fragment_texts):
        all_files = {p.stem for p in COMMON_EVENTS.glob("*.md")}
        broken = []
        for name, text in fragment_texts.items():
            for target in re.findall(r"\[\[([^\]]+)\]\]", text):
                if target not in all_files:
                    broken.append((name, target))
        assert not broken, f"unresolved wikilinks: {broken}"
