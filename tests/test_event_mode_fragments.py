"""Content-coverage tests for the event-mode L1 base fragments (#8915).

Backs TEST-PLAN-8694.md AC-5 / AC-6 / AC-7 measurable refinements at the
file-level (not the composed-CLAUDE.md level — that wiring is a separate
follow-up cycle).

These tests check the fragments authored or rewritten under #8915.
`event-driven-workflow.md` was rewritten in cycle 1138 to drop forbidden
mode-conditional tokens + obsolete completion-API content and is now
included in the AC-5 sweep (forbidden-token check) and the wikilink-
resolution check, alongside the 5 fragments authored in cycle 1136. AC-7
(topic coverage) intentionally targets only the five topic-bearing
fragments, not the orientation page.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SUB_SKILLS = REPO_ROOT / "references" / "sub-skills"
COMMON_EVENTS = SUB_SKILLS / "common-events"

# Fragments authored/rewritten under #8915. Stored as paths relative to
# references/sub-skills/. AC-5 forbidden-token sweep + wikilink resolution
# apply to all of them. AC-6 + AC-7 topic checks target the common-events
# topic-bearing fragments only.
COMMON_EVENTS_FRAGMENTS = [
    # Cycle 1136 — common-events L1 base fragments. AC-5 prohibits
    # mode-conditional language inside these (they are the always-on
    # event-mode contract).
    "common-events/l1-base.md",
    "common-events/cursor-management.md",
    "common-events/forge-read-pattern.md",
    "common-events/idle-cooldown-loop.md",
    "common-events/comment-handling.md",
    # Cycle 1138 — legacy file rewritten to drop forbidden tokens + obsolete
    # completion-API content; now an orientation page redirecting to the 5
    # fragments above. AC-5 applies.
    "common-events/event-driven-workflow.md",
]

PER_ROLE_EVENTS_FRAGMENTS = [
    # Cycle 1139 — DM per-role events fragment for the PR-merge wait,
    # called out in CONTEXT.md §5.1. Per-role events fragments are
    # inherently event-mode-only and may legitimately reference event-mode
    # concepts — they are NOT subject to the AC-5 forbidden-token sweep
    # (which targets common fragments that must be mode-agnostic).
    "roles/dm/events/pr-merge-wait.md",
]

NEW_FRAGMENTS = COMMON_EVENTS_FRAGMENTS + PER_ROLE_EVENTS_FRAGMENTS


@pytest.fixture(scope="module")
def fragment_texts():
    return {
        rel: (SUB_SKILLS / rel).read_text(encoding="utf-8")
        for rel in NEW_FRAGMENTS
    }


class TestFragmentsExist:
    @pytest.mark.parametrize("name", NEW_FRAGMENTS)
    def test_fragment_file_exists(self, name):
        path = SUB_SKILLS / name
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

    @pytest.mark.parametrize("name", COMMON_EVENTS_FRAGMENTS)
    @pytest.mark.parametrize("token", FORBIDDEN)
    def test_common_events_fragment_has_no_forbidden_token(
        self, fragment_texts, name, token,
    ):
        """AC-5 applies to common-events fragments only — they must be
        mode-agnostic. Per-role events fragments may legitimately reference
        event-mode concepts since they are inherently event-mode-only."""
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
        text = fragment_texts["common-events/l1-base.md"]
        assert re.search(r"(?im)^\s*###?\s+Boot Sequence", text), (
            "l1-base.md must contain a 'Boot Sequence' section header"
        )


class TestAc7TopicCoverage:
    """AC-7 M-7.1: each topic from CONTEXT.md §5.1 Deliverables must have
    at least one section header (## or ###) in the new fragments."""

    @pytest.mark.parametrize("topic_regex,where", [
        # (case-insensitive regex matched against headers, fragment name)
        (r"boot sequence", "common-events/l1-base.md"),
        (r"how you listen|event poll", "common-events/l1-base.md"),
        (r"case b\b", "common-events/l1-base.md"),
        (r"case c\b", "common-events/l1-base.md"),
        (r"case d\b", "common-events/l1-base.md"),
        (r"case e\b", "common-events/l1-base.md"),
        (r"atomic update protocol", "common-events/cursor-management.md"),
        (r"per-event advance|per-batch", "common-events/cursor-management.md"),
        (r"gap scenarios", "common-events/cursor-management.md"),
        (r"forge-read pattern|forge-read", "common-events/forge-read-pattern.md"),
        (r"idle.*improvement.scan.*cool.?down|cool.?down loop",
         "common-events/idle-cooldown-loop.md"),
        (r"working-state schema", "common-events/idle-cooldown-loop.md"),
        (r"comment handling|the rule", "common-events/comment-handling.md"),
        (r"dm exception|end.?of.?task re.?read", "common-events/comment-handling.md"),
        (r"transition.?on.?handoff", "common-events/comment-handling.md"),
        # Cycle 1139 — DM per-role PR-merge wait fragment.
        (r"task is the wait|no sub-loop|end.?of.?task re.?read",
         "roles/dm/events/pr-merge-wait.md"),
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


class TestAc6M62ManifestWiring:
    """AC-6 M-6.2 (post-#9588): the event-mode L1 base fragment + its four
    supporting common-events fragments must reach the agent at runtime via
    the boot bootstrap, NOT via compose-time inlining.

    #9588 swapped the wiring mechanism: instead of every event-mode manifest
    listing all six common-events fragments and the template having matching
    `{{include:}}` directives, the manifest now contains `common/boot-bootstrap`
    only, and the bootstrap's content carries `Read references/sub-skills/
    common-events/<name>.md` directives that fire when the agent boots in
    event mode. The previous compose-time-inline contract (#8915) is the old
    contract; this class enforces the new one.
    """

    REQUIRED_COMMON_EVENTS = [
        "common-events/l1-base",
        "common-events/cursor-management",
        "common-events/forge-read-pattern",
        "common-events/idle-cooldown-loop",
        "common-events/comment-handling",
    ]
    # #10156: post-#6274.2 rename — dev→worker, qa→verifier. Directories
    # on disk are references/roles/{worker,pm,verifier,dm}/.
    ROLES = ["worker", "pm", "verifier", "dm"]

    @pytest.fixture(scope="class")
    def includes_by_role(self):
        import yaml
        roles_dir = REPO_ROOT / "references" / "roles"
        out = {}
        for role in self.ROLES:
            path = roles_dir / role / "includes-events.yml"
            assert path.exists(), f"missing manifest: {path}"
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            out[role] = data.get("includes", [])
        return out

    @pytest.fixture(scope="class")
    def bootstrap_text(self):
        path = SUB_SKILLS / "common" / "boot-bootstrap.md"
        assert path.exists(), (
            "common/boot-bootstrap.md must exist — #9588 made it the single "
            "loader for both polling and event-mode entry fragments."
        )
        return path.read_text(encoding="utf-8")

    @pytest.mark.parametrize("role", ROLES)
    def test_role_manifest_includes_boot_bootstrap(
        self, includes_by_role, role,
    ):
        """Manifests reference `common/boot-bootstrap` as the loader. The
        six legacy `common-events/*` entries are no longer present — they
        are Read at runtime by the bootstrap instead."""
        includes = includes_by_role[role]
        assert "common/boot-bootstrap" in includes, (
            f"references/roles/{role}/includes-events.yml must list "
            f"`common/boot-bootstrap` — #9588 made it the manifest entry "
            f"that gets the agent into event mode (or fallback polling)."
        )

    @pytest.mark.parametrize("required", REQUIRED_COMMON_EVENTS)
    def test_bootstrap_references_common_events_fragment(
        self, bootstrap_text, required,
    ):
        """The bootstrap fragment must Read each common-events fragment at
        runtime so a fresh event-mode agent loads the full event contract."""
        rel = f"references/sub-skills/{required}.md"
        assert rel in bootstrap_text, (
            f"boot-bootstrap.md must reference `{rel}` so event-mode agents "
            f"Read it at boot. Removing the runtime Read here breaks the "
            f"same wiring AC-6 M-6.2 was originally written to enforce."
        )

    def test_bootstrap_references_pr_merge_wait_for_dm(self, bootstrap_text):
        """DM's role-specific events extra is loaded by the bootstrap too."""
        rel = "references/sub-skills/roles/dm/events/pr-merge-wait.md"
        assert rel in bootstrap_text, (
            f"boot-bootstrap.md must reference `{rel}` in its DM-only "
            f"branch — it is the sole loader for the per-role events extra."
        )


class TestWikilinkResolution:
    """Wikilinks between the event-mode fragments must resolve to actual
    `.md` files in `common-events/` or any `roles/<role>/events/` subdir."""

    def test_all_wikilinks_resolve(self, fragment_texts):
        all_files = {p.stem for p in COMMON_EVENTS.glob("*.md")}
        for events_dir in SUB_SKILLS.glob("roles/*/events"):
            all_files.update(p.stem for p in events_dir.glob("*.md"))
        broken = []
        for name, text in fragment_texts.items():
            for target in re.findall(r"\[\[([^\]]+)\]\]", text):
                if target not in all_files:
                    broken.append((name, target))
        assert not broken, f"unresolved wikilinks: {broken}"
