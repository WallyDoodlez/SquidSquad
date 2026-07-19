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
    "common-events/event-mode-contract.md",
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
    inside `event-mode-contract.md`."""

    def test_no_l1_boot_fragment_anywhere(self):
        matches = list(REPO_ROOT.glob("references/sub-skills/**/l1-boot.md"))
        assert matches == [], (
            f"l1-boot.md must not exist; found: {matches}"
        )

    def test_event_mode_contract_contains_boot_sequence_header(self, fragment_texts):
        # AC-6 M-6.2: the boot sequence text appears inside the L1 base
        # fragment, not a standalone l1-boot.md.
        text = fragment_texts["common-events/event-mode-contract.md"]
        assert re.search(r"(?im)^\s*###?\s+Boot Sequence", text), (
            "event-mode-contract.md must contain a 'Boot Sequence' section header"
        )


class TestAc7TopicCoverage:
    """AC-7 M-7.1: each topic from CONTEXT.md §5.1 Deliverables must have
    at least one section header (## or ###) in the new fragments."""

    @pytest.mark.parametrize("topic_regex,where", [
        # (case-insensitive regex matched against headers, fragment name)
        (r"boot sequence", "common-events/event-mode-contract.md"),
        (r"how you listen|event poll", "common-events/event-mode-contract.md"),
        (r"case b\b", "common-events/event-mode-contract.md"),
        (r"case c\b", "common-events/event-mode-contract.md"),
        (r"case d\b", "common-events/event-mode-contract.md"),
        (r"case e\b", "common-events/event-mode-contract.md"),
        # #11330 D1-D4 supersede the pre-existing topic headers
        # ("Atomic Update Protocol", "Per-Event Advance, Not Per-Batch").
        # Post-#11328 the cursor is harness-owned in .event-state.json —
        # the agent has no atomic-write protocol of its own, and per-event
        # advance is the canonical (and only) model so there is no
        # per-batch contrast to maintain. The two assertions now pin the
        # new canonical headers covering the same semantic ground:
        #   - "How to advance the cursor — POST /events ack-cursor" (the
        #     mechanism that replaces the old agent-side atomic write)
        #   - "Where the cursor lives" (the harness-owned framing that
        #     replaces the agent-side .tmp + mv contract)
        (r"POST.*ack-cursor|how to advance", "common-events/cursor-management.md"),
        (r"where the cursor lives", "common-events/cursor-management.md"),
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
    """AC-6 M-6.2 (v2 wiring, rebound at #11503): the event-mode L1 base
    fragment + its supporting common-events fragments must reach the agent
    at runtime via the boot bootstrap, NOT via compose-time inlining.

    History of the wiring mechanism:
    - #9588 swapped per-manifest fragment lists for a single
      ``common/boot-bootstrap`` loader carrying runtime-load directives.
    - #11046 consolidated the v1 polling/event manifest split
      (``includes.yml`` + ``includes-events.yml``) into one mode-agnostic
      ``includes.yml`` per role.
    - v0.44.0 / v2 cutover (#11394) moved the boot-bootstrap body OUT of a
      standalone ``common/boot-bootstrap.md`` AND out of per-role
      ``includes.yml`` entirely: it is now authored in the shared base
      ``references/roles/instructions.md`` (composed into every role via
      the ``<!-- sub-skill: boot-bootstrap -->`` markers) and references
      each runtime fragment with a ``→ run sub-skill: <name>`` marker
      (catalog-resolved to ``common-events/<name>.md``) instead of a
      literal ``Read .../common-events/X.md`` path.

    This test rebinds to that v2 source + reference syntax (#11503 Group A).
    The wiring contract is unchanged: every role reaches event mode, and the
    bootstrap loads the full event contract at boot.
    """

    # Bare catalog names (v2): the boot block references these via
    # `→ run sub-skill: <name>` markers; the catalog resolves each to
    # references/sub-skills/common-events/<name>.md.
    REQUIRED_COMMON_EVENTS = [
        "event-mode-contract",
        "cursor-management",
        "forge-read-pattern",
        "idle-cooldown-loop",
        "comment-handling",
    ]

    SHARED_BASE = REPO_ROOT / "references" / "roles" / "instructions.md"

    @pytest.fixture(scope="class")
    def bootstrap_block(self):
        """The boot-bootstrap body lives in the shared base instructions
        (composed into every role), delimited by the sub-skill markers.
        Extract that block so the reference checks target bootstrap content,
        not the whole file."""
        assert self.SHARED_BASE.exists(), (
            f"shared base instructions missing: {self.SHARED_BASE}"
        )
        text = self.SHARED_BASE.read_text(encoding="utf-8")
        m = re.search(
            r"<!-- sub-skill: boot-bootstrap -->(.*?)"
            r"<!-- /sub-skill: boot-bootstrap -->",
            text, re.DOTALL,
        )
        assert m, (
            "references/roles/instructions.md must contain a "
            "`<!-- sub-skill: boot-bootstrap -->` block — it is the v2 home "
            "of the boot sequence that gets every role into event mode "
            "(or fallback polling)."
        )
        return m.group(1)

    def test_boot_bootstrap_authored_in_shared_base(self, bootstrap_block):
        """The boot-bootstrap block composes into every role from the shared
        base, so one presence check covers all roles (replaces the retired
        per-role includes.yml entry check)."""
        assert "step:cycle/boot" in bootstrap_block, (
            "boot-bootstrap block must define the step:cycle/boot sequence."
        )

    @pytest.mark.parametrize("required", REQUIRED_COMMON_EVENTS)
    def test_bootstrap_references_common_events_fragment(
        self, bootstrap_block, required,
    ):
        """The bootstrap block must load each common-events fragment at
        runtime via a `→ run sub-skill: <name>` marker so a fresh event-mode
        agent loads the full event contract at boot."""
        pat = re.compile(r"run sub-skill:\s*`?" + re.escape(required) + r"`?")
        assert pat.search(bootstrap_block), (
            f"boot-bootstrap block must reference `{required}` via a "
            f"`→ run sub-skill: {required}` marker so event-mode agents Read "
            f"it at boot. Removing it breaks the wiring AC-6 M-6.2 enforces."
        )

    def test_bootstrap_references_pr_merge_wait(self, bootstrap_block):
        """DM's role-specific events extra is loaded by the bootstrap too
        (referenced in the shared block in v2)."""
        pat = re.compile(r"run sub-skill:\s*`?roles/dm/events/pr-merge-wait`?")
        assert pat.search(bootstrap_block), (
            "boot-bootstrap block must reference "
            "`roles/dm/events/pr-merge-wait` via a `→ run sub-skill:` marker "
            "— it is the sole loader for the per-role events extra."
        )


class TestBootDrainDeploySignalDeferral:
    """#13569: a deploy-signal in the BOOT DRAIN must be DEFERRED until the
    agent's boot completes (post-drain boundary), then honored — never honored
    the moment it is reached mid-drain. Honoring mid-drain reboots the agent
    before boot completes ("agents reboot before boot completes" symptom).

    These assertions pin the behavioral contract. As of #13565, the full
    deferral procedure lives in the reactively-read `deploy-signal-handling.md`
    fragment (event-mode-contract.md keeps only the load-bearing invariants
    inline + a pointer), so `contract_text` covers both files. Prose is
    matched on stable, load-bearing tokens (not full sentences) to stay robust
    to wording changes that preserve the contract.
    """

    @pytest.fixture(scope="class")
    def contract_text(self, fragment_texts):
        deploy_signal_handling = (
            SUB_SKILLS / "common-events" / "deploy-signal-handling.md"
        ).read_text(encoding="utf-8")
        return (
            fragment_texts["common-events/event-mode-contract.md"]
            + "\n"
            + deploy_signal_handling
        )

    def test_carries_issue_marker(self, contract_text):
        assert "#13569" in contract_text, (
            "event-mode-contract.md must cite #13569 at the boot-drain "
            "deploy-signal deferral it introduced."
        )

    def test_boot_drain_signal_is_deferred_until_boot_completes(self, contract_text):
        # The boot-drain sub-bullet must state the signal is DEFERRED and tie
        # the deferral to boot COMPLETING (both tokens present in the contract).
        assert "DEFERRED" in contract_text, (
            "boot-drain deploy-signal must be marked DEFERRED, not honored "
            "where reached mid-drain."
        )
        assert re.search(r"boot\s+drain", contract_text, re.IGNORECASE), (
            "the deferral must be scoped to the boot drain."
        )
        assert re.search(r"until your boot completes|before your boot completes",
                         contract_text, re.IGNORECASE), (
            "the deferral must be anchored to boot completion (the #13569 "
            "guarantee: boot always completes before the deploy-reboot)."
        )

    def test_defers_to_post_drain_boundary_before_new_work(self, contract_text):
        # Honor happens at the post-drain boundary, BEFORE the idle loop and
        # BEFORE picking up any new work_queue item.
        assert "post-drain boundary" in contract_text, (
            "the deferred signal must be honored at the post-drain boundary."
        )
        assert re.search(r"before[^.]*picking up[^.]*work_queue|before[^.]*"
                         r"work_queue\(\)\s*item", contract_text, re.IGNORECASE), (
            "the honor must precede any new work_queue() pickup so no fresh "
            "post-boot work runs on possibly-stale instructions."
        )

    def test_steady_state_honor_still_requires_clean_main(self, contract_text):
        # The steady-state (post-boot) path is unchanged: honor only on main
        # with a clean tree at a between-task boundary.
        assert re.search(r"Steady-state \(post-boot\)", contract_text), (
            "the steady-state deploy-signal bullet must remain and stay "
            "distinct from the boot-drain deferral."
        )
        assert re.search(r"clean working tree", contract_text), (
            "steady-state honor must still require a clean working tree on main."
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
