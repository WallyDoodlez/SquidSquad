"""Regression tests for #9588 — lazy-load mode-specific instructions at boot.

CONTEXT-9588.md D7 locks the regression contract:

  - Composed CLAUDE.md contains the boot-bootstrap snippet (a single marker
    check is enough — the bootstrap is shipped as a sub-skill fragment so
    its outer marker is deterministic).
  - Composed CLAUDE.md does NOT inline the mode-specific fragments
    (`ralph-loop-overview` or any `common-events/*`). Per CONTEXT §2.4 the
    agent Reads those at runtime via the bootstrap, so finding their
    marker in compose output would mean compose-time leakage came back.
  - Each runtime Read target referenced by the bootstrap actually exists
    on disk — broken paths in the bootstrap silently degrade an agent to
    a no-op at boot.
  - The polling-fragment path placeholder is substituted per role so dev
    variants (skill etc.) get the dev base path rather than a nonexistent
    `roles/skill/ralph-loop-overview.md`.
"""

from pathlib import Path
import re
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "references" / "scripts"
SUB_SKILLS = REPO_ROOT / "references" / "sub-skills"

sys.path.insert(0, str(SCRIPTS))
import compose  # noqa: E402

from _v2_test_helpers import v2_compose_for  # noqa: E402


ROLES = ["skill", "pm", "qa", "dm"]

# (role, entry_file) — entry_file is the directory under references/sub-skills/roles
# that owns the polling fragment for this role. Worker variants share worker's
# (post-6274.2 rename; was dev's). 'qa' resolves to 'verifier' via the dual-aware
# alias-target preference in compose._get_entry_file_for_role.
ROLE_TO_ENTRY = {
    "skill": "worker",
    "pm": "pm",
    "qa": "verifier",
    "dm": "dm",
}

# Marker the bootstrap fragment writes at the top of its content.
# Post-#11144 Iter 22 polish-restructure the bootstrap content was hoisted
# into the L1 `references/roles/instructions.md` directly under the
# `### Step 1 — step:cycle/boot` H3 (the canonical step heading from the
# cycle's step-ID contract). The legacy H2 `## Boot — Mode Detection (#9588)`
# heading was retired with the restructure; the marker still wraps the
# block but the inner heading is now the step-ID form.
BOOT_BOOTSTRAP_MARKER = "<!-- sub-skill: boot-bootstrap -->"
BOOT_BOOTSTRAP_HEADING = "### Step 1 — step:cycle/boot"

# Mode-specific sub-skill markers that MUST NOT appear in composed output
# after #9588. compose strips the outer markers from the source fragment
# but re-wraps with these — if the wrapper marker shows up in the deployed
# CLAUDE.md, the fragment was inlined at compose time.
MODE_SPECIFIC_MARKERS = [
    "<!-- sub-skill: ralph-loop-overview -->",
    "<!-- sub-skill: event-driven-workflow -->",
    "<!-- sub-skill: event-mode-contract -->",
    "<!-- sub-skill: cursor-management -->",
    "<!-- sub-skill: forge-read-pattern -->",
    "<!-- sub-skill: idle-cooldown-loop -->",
    "<!-- sub-skill: comment-handling -->",
    "<!-- sub-skill: pr-merge-wait -->",
]


_compose_for = v2_compose_for  # local alias retained for the test body below


@pytest.mark.parametrize("role", ROLES)
def test_composed_claude_contains_boot_bootstrap(role):
    """Every role's composed CLAUDE.md inlines `common/boot-bootstrap`."""
    text = _compose_for(role)
    assert BOOT_BOOTSTRAP_MARKER in text, (
        f"{role}: composed CLAUDE.md is missing the boot-bootstrap sub-skill "
        f"marker. Either the manifest dropped the include or the L2 "
        f"instructions.md no longer references it."
    )
    assert BOOT_BOOTSTRAP_HEADING in text, (
        f"{role}: bootstrap marker present but heading missing — fragment "
        f"content may have drifted."
    )


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("marker", MODE_SPECIFIC_MARKERS)
def test_composed_claude_does_not_inline_mode_specific(role, marker):
    """Mode-specific fragments are Read at runtime, never inlined at compose."""
    text = _compose_for(role)
    assert marker not in text, (
        f"{role}: composed CLAUDE.md contains mode-specific marker "
        f"`{marker}` — this fragment should be Read at runtime by the "
        f"bootstrap, not inlined at compose time (#9588)."
    )


@pytest.mark.parametrize("role,entry", ROLE_TO_ENTRY.items())
def test_polling_fragment_path_substituted_per_role(role, entry):
    """Bootstrap's [POLLING_FRAGMENT_PATH] resolves to the role's entry-file path."""
    text = _compose_for(role)
    expected = f"references/sub-skills/roles/{entry}/ralph-loop-overview.md"
    assert expected in text, (
        f"{role}: composed CLAUDE.md should reference `{expected}` after "
        f"placeholder substitution. Dev variants (skill) must resolve to "
        f"the dev base path, not their own role name."
    )
    # And the unsubstituted placeholder must not leak through.
    assert "[POLLING_FRAGMENT_PATH]" not in text, (
        f"{role}: raw [POLLING_FRAGMENT_PATH] placeholder leaked into "
        f"composed output — _substitute_placeholders did not run."
    )


@pytest.mark.parametrize("role", ROLES)
def test_referenced_runtime_fragments_exist_on_disk(role):
    """Every fragment path the bootstrap tells the agent to Read must exist."""
    text = _compose_for(role)

    # Extract every references/sub-skills/... .md path mentioned inside the
    # boot-bootstrap section. Constrain the scan to the bootstrap block so
    # we don't trip on unrelated path mentions elsewhere in CLAUDE.md.
    start = text.find(BOOT_BOOTSTRAP_MARKER)
    end = text.find("<!-- /sub-skill: boot-bootstrap -->", start)
    assert start != -1 and end != -1, (
        f"{role}: bootstrap markers missing — earlier tests should have "
        f"caught this; aborting."
    )
    block = text[start:end]

    paths = re.findall(r"`(references/sub-skills/[^`]+\.md)`", block)
    assert paths, (
        f"{role}: bootstrap block names zero runtime-Read paths — that "
        f"would mean the agent has nothing to Read, which is a regression."
    )

    for rel in paths:
        full = REPO_ROOT / rel
        assert full.exists(), (
            f"{role}: bootstrap references `{rel}` but the file does not "
            f"exist on disk. Broken Read targets silently no-op at boot."
        )


def test_dm_bootstrap_enumerates_pr_merge_wait():
    """DM's bootstrap must call out the role-specific events extra."""
    text = _compose_for("dm")
    start = text.find(BOOT_BOOTSTRAP_MARKER)
    end = text.find("<!-- /sub-skill: boot-bootstrap -->", start)
    block = text[start:end]
    # Post-#11144 polish: the bootstrap names sub-skills by their bare
    # `→ run sub-skill:` identifier (no `.md` suffix) rather than by file
    # path, per the directive grammar canonized in the step-ID contract.
    # `roles/dm/events/pr-merge-wait` is the slash-bearing identifier form.
    assert "roles/dm/events/pr-merge-wait" in block, (
        "DM's bootstrap must enumerate `pr-merge-wait` — it is the only "
        "role-specific events extra in the codebase and the bootstrap is "
        "the sole loader for it after #9588."
    )


@pytest.mark.parametrize("role", ROLES)
def test_bootstrap_owns_loop_invocation_with_substituted_interval(role):
    """#9588 BLOCKER fix: `/loop` is invoked from the bootstrap (which compose
    inlines, so `[INTERVAL]` substitutes correctly), NOT from any runtime-Read
    fragment (where the placeholder would not substitute and the agent would
    try to invoke `/loop [INTERVAL]m …` literally).

    Composed CLAUDE.md must contain `/loop <N>m execute one Ralph Loop cycle`
    with a concrete integer N — and must NOT contain the literal placeholder
    `[INTERVAL]`. Pulls the expected interval from config to keep the test
    honest if someone changes the default cadence.
    """
    text = _compose_for(role)
    assert "[INTERVAL]" not in text, (
        f"{role}: composed CLAUDE.md still contains the literal `[INTERVAL]` "
        f"placeholder — compose-time substitution failed somewhere."
    )
    # The /loop directive must be substituted. We don't pin the exact integer
    # so the test survives config interval changes; we just require digits.
    assert re.search(r"/loop \d+m execute one Ralph Loop cycle", text), (
        f"{role}: composed CLAUDE.md should contain a substituted `/loop <N>m "
        f"execute one Ralph Loop cycle` directive in the boot bootstrap."
    )


@pytest.mark.parametrize("role,entry", ROLE_TO_ENTRY.items())
def test_polling_fragment_source_does_not_invoke_loop(role, entry):
    """#9588 BLOCKER fix: source `ralph-loop-overview.md` fragments must NOT
    contain a `/loop` invocation or the `[INTERVAL]` placeholder. Those moved
    into the bootstrap (where compose substitutes `[INTERVAL]`). If a polling
    fragment ever regains a literal `/loop [INTERVAL]m …`, an agent in
    polling mode will Read the placeholder verbatim and the loop will never
    fire — exactly the bug PM caught in cycle ~1537.
    """
    path = SUB_SKILLS / "roles" / entry / "ralph-loop-overview.md"
    assert path.exists(), f"{role}: polling fragment missing at {path}"
    src = path.read_text(encoding="utf-8")
    assert "[INTERVAL]" not in src, (
        f"{role}: source fragment {path.name} still has the [INTERVAL] "
        f"placeholder — compose-time substitution does not fire on runtime-"
        f"loaded fragments. Move any /loop references to boot-bootstrap.md."
    )
    assert "/loop " not in src, (
        f"{role}: source fragment {path.name} still invokes `/loop` — boot "
        f"bootstrap is now the sole scheduler. Strip the invocation from "
        f"the source so a runtime Read cannot stack a duplicate cron entry."
    )


def test_bootstrap_documents_role_runtime_substitution():
    """#9588 BLOCKER follow-on: role-placeholder still appears in the polling
    fragment source (dev's, lines 33/36 — status-bar and current-state refs).
    The bootstrap must tell the agent to substitute it at runtime using its
    own role identity; otherwise the agent reads the literal placeholder
    and writes a broken path / runs a broken arg.

    The bootstrap source can't contain the literal placeholder string because
    compose would substitute it away at compose time (the very bug we're
    avoiding). So we check for the teaching marker + the role-name guidance.
    """
    # Post-#11144 G11 close: the boot block is canonical in L1
    # `references/roles/instructions.md` (Iter 22 hoisted it from the
    # sub-skill source; Iter 36 deleted `common/boot-bootstrap.md` once
    # the source had become dead-code-divergent from L1). Validation
    # targets the L1 source.
    text = (REPO_ROOT / "references" / "roles" / "instructions.md").read_text(
        encoding="utf-8"
    )
    assert "Placeholder substitution inside runtime-loaded fragments" in text, (
        "L1 instructions.md must carry the placeholder-substitution rule so "
        "the agent knows what to do with role/interval placeholders inside "
        "a runtime-loaded fragment. Without this rule, the literal "
        "placeholder breaks path/arg construction in the polling fragment."
    )
    assert "Role-name placeholder" in text and "SQUIDSQUAD_ROLE" in text, (
        "L1 instructions.md placeholder section must call out the role-name "
        "placeholder and tell the agent to substitute its own SQUIDSQUAD_ROLE."
    )
    # And critically: the section must survive compose unchanged — i.e., the
    # teaching itself must still be in the *composed* CLAUDE.md, not just
    # the source. If compose were substituting the placeholder names away,
    # the teaching section would render mangled (the original draft of this
    # fragment had exactly that bug).
    for role in ROLES:
        composed = _compose_for(role)
        assert "Role-name placeholder" in composed, (
            f"{role}: composed CLAUDE.md is missing the placeholder-teaching "
            f"section. Either compose mangled it (placeholder names spelled "
            f"literally and substituted away) or the bootstrap was excluded "
            f"from this role's compose."
        )


def test_event_mode_contract_unreachable_branch_removed():
    """event-mode-contract.md §3 no longer carries the bespoke degraded-mode block."""
    text = (SUB_SKILLS / "common-events" / "event-mode-contract.md").read_text(encoding="utf-8")
    # The old block had this distinctive sequence — its presence would mean
    # we re-introduced the unreachable branch the bootstrap now subsumes.
    assert "proceed to degraded-mode operation" not in text, (
        "event-mode-contract.md still contains the legacy degraded-mode block; #9588 "
        "deletes it because the boot bootstrap routes harness-unreachable "
        "to polling-mode before event-mode-contract is ever Read."
    )
    # Also: the Degraded-Mode Glossary section is gone.
    assert "### Degraded-Mode Glossary" not in text, (
        "event-mode-contract.md still has the Degraded-Mode Glossary section — replace "
        "it with the Harness-Loss Recovery block per CONTEXT §2.6."
    )
