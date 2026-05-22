"""#9925 regression tests — L1+L2+L3+L4 responsibility-layering machinery.

Covers AC4 (compose-time roster + L2 content), AC6 (memory absorption
lineage tags), AC7 (L3 stub files), AC8 (L4 stub files in both seed
and live locations), AC9 (L4 prefix-filtered inclusion), AC10 (byte-
identical re-runs with agent_compose disabled), AC11 (degraded modes).
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import compose  # noqa: E402


# ---------------------------------------------------------------------------
# AC4 — composed CLAUDE.md contains L1 awareness + roster + L2 content
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("role", ["pm", "qa", "dm", "skill"])
def test_ac4_composed_contains_l1_awareness_and_l2(role):
    """For each of pm/qa/dm/dev (skill is the dev variant), the composed
    output must contain the L1 awareness instruction, the roster header,
    and the role's own L2 'What this role does' header (#9925 AC4).
    """
    composed = compose.compose_role(role)
    assert "Know each other's responsibilities" in composed, (
        f"L1 awareness instruction missing from composed {role}"
    )
    assert "## Your Teammates' Responsibilities" in composed, (
        f"L1 roster header missing from composed {role}"
    )
    assert "What this role does" in composed, (
        f"L2 'What this role does' header missing from composed {role}"
    )
    assert "What this role does NOT do" in composed, (
        f"L2 'What this role does NOT do' section missing from composed {role}"
    )


def test_ac4_roster_has_exactly_active_roles():
    """AC4: for the current install (`Dev Agents: skill` + mandatory
    PM/QA/DM), the roster MUST contain exactly 4 entries — one per
    pm/qa/dm/dev. Roles whose manifest exists but are NOT active in
    config.md must NOT appear (F4 lock).
    """
    composed = compose.compose_role("pm")
    # Each rendered entry uses a `### <DisplayName>` header inside the
    # 'Your Teammates' Responsibilities' block. Slice the roster section
    # and count its level-3 headers.
    start = composed.find("## Your Teammates' Responsibilities")
    assert start != -1
    # Roster ends at the next h2 (or the L1 closing marker).
    end_candidates = [
        composed.find("\n## ", start + 5),
        composed.find("<!-- /sub-skill: agent-boundaries -->", start),
    ]
    end = min(c for c in end_candidates if c != -1)
    roster_block = composed[start:end]
    h3_count = roster_block.count("\n### ")
    assert h3_count == 4, (
        f"AC4: expected exactly 4 roster entries (one per pm/qa/dm/dev), "
        f"saw {h3_count}. Roster block:\n{roster_block}"
    )


# ---------------------------------------------------------------------------
# AC6 — memory absorption lineage tags present in predicted L2 files
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("source,filename", [
    # PM L2 absorptions
    ("feedback_dont_do_qa_job", "references/sub-skills/roles/pm/responsibility.md"),
    ("feedback_bugs_behavior_only", "references/sub-skills/roles/pm/responsibility.md"),
    ("feedback_auto_approve_bugs", "references/sub-skills/roles/pm/responsibility.md"),
    ("feedback_dm_optional", "references/sub-skills/roles/pm/responsibility.md"),
    # QA L2 absorptions
    ("feedback_no_ship_failed_tc", "references/sub-skills/roles/qa/responsibility.md"),
    ("feedback_no_ship_with_gaps", "references/sub-skills/roles/qa/responsibility.md"),
    # DM L2 absorptions
    ("feedback_dm_optional", "references/sub-skills/roles/dm/responsibility.md"),
    ("feedback_no_ship_failed_tc", "references/sub-skills/roles/dm/responsibility.md"),
    ("feedback_no_ship_with_gaps", "references/sub-skills/roles/dm/responsibility.md"),
    # Cross-role test_workflow_separation
    ("feedback_test_workflow_separation", "references/sub-skills/roles/pm/responsibility.md"),
    ("feedback_test_workflow_separation", "references/sub-skills/roles/qa/responsibility.md"),
    ("feedback_test_workflow_separation", "references/sub-skills/roles/dm/responsibility.md"),
    ("feedback_test_workflow_separation", "references/sub-skills/roles/dev/responsibility.md"),
])
def test_ac6_memory_absorption_lineage_tag(source, filename):
    """AC6: each memory entry from D5 is absorbed into the indicated L2
    file with an HTML-comment lineage tag `<!-- absorbed from <name> -->`.
    """
    path = REPO / filename
    assert path.exists(), f"L2 file missing: {filename}"
    content = path.read_text(encoding="utf-8")
    assert f"<!-- absorbed from {source} -->" in content, (
        f"AC6: lineage tag for {source} not found in {filename}"
    )


# ---------------------------------------------------------------------------
# AC7 — 20 L3 stub files exist with the locked template content
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("role", ["dev", "dm", "pm", "qa"])
@pytest.mark.parametrize("variant", ["android", "fullstack", "ios", "skill", "web"])
def test_ac7_l3_stub_exists_and_matches_template(role, variant):
    """AC7: all 20 L3 stub files exist and match the D6a template
    (literal string match for 'No variant-specific responsibility
    narrowing'). None are wired into includes_yml's additional_includes.
    """
    stub = REPO / "references" / "roles" / role / variant / "responsibility.md"
    assert stub.exists(), f"L3 stub missing: {stub}"
    content = stub.read_text(encoding="utf-8")
    assert "No variant-specific responsibility narrowing" in content, (
        f"AC7: L3 stub at {stub} doesn't match the locked template"
    )


# ---------------------------------------------------------------------------
# AC8 — 5 L4 stub files in BOTH seed (references/) and live (.squidsquad/)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("prefix", ["pm", "qa", "dm", "dev", "shared"])
def test_ac8_l4_seed_stub_exists(prefix):
    """AC8 (seed half): seed templates at references/sub-skills/project/."""
    seed = REPO / "references" / "sub-skills" / "project" / f"{prefix}-responsibility.md"
    assert seed.exists(), f"L4 seed stub missing: {seed}"
    content = seed.read_text(encoding="utf-8")
    assert "Install-specific responsibility additions" in content


@pytest.mark.parametrize("prefix", ["pm", "qa", "dm", "dev", "shared"])
def test_ac8_l4_live_stub_exists(prefix):
    """AC8 (live half): live stubs at .squidsquad/project/."""
    live = REPO / ".squidsquad" / "project" / f"{prefix}-responsibility.md"
    assert live.exists(), f"L4 live stub missing: {live}"
    content = live.read_text(encoding="utf-8")
    assert "Install-specific responsibility additions" in content


# ---------------------------------------------------------------------------
# AC9 — L4 prefix-filtered inclusion in composed output
# ---------------------------------------------------------------------------


def test_ac9_pm_compose_includes_pm_and_shared_l4_not_others():
    """AC9: composed PM CLAUDE.md must include the PM L4 stub and the
    shared L4 stub, but NOT the qa/dm/dev L4 stubs (filename-prefix
    routing per D6b).
    """
    composed = compose.compose_role("pm")
    # The L4 stubs all contain the literal "Install-specific
    # responsibility additions" string. We need to count occurrences to
    # validate that the PM compose pulled in 2 (pm + shared) — not 5.
    occurrences = composed.count("Install-specific responsibility additions")
    assert occurrences == 2, (
        f"AC9: PM compose must include exactly 2 L4 stubs (pm + shared), "
        f"saw {occurrences} occurrences of the L4 template phrase. "
        "Filename-prefix routing per D6b should filter out qa/dm/dev."
    )


# ---------------------------------------------------------------------------
# AC10 — byte-identical re-runs with agent_compose disabled
# ---------------------------------------------------------------------------


def test_ac10_byte_identical_recompose_agent_compose_off():
    """AC10: with `agent_compose: no` (or absent), running compose_role
    twice produces byte-identical output. Locked precondition per v4-F3
    — `agent_compose: yes` invokes a non-deterministic LLM polish that
    legitimately breaks byte-identity.
    """
    with patch.object(compose, "_is_agent_compose_enabled", return_value=False):
        a = compose.compose_role("pm")
        b = compose.compose_role("pm")
    assert a == b, "AC10: compose_role('pm') is non-deterministic with agent_compose disabled"


# ---------------------------------------------------------------------------
# AC11 — degraded modes
# ---------------------------------------------------------------------------


def test_ac11_missing_display_name_raises_systemexit(capsys):
    """AC11: a role manifest missing the required `display_name` field
    must produce a build error with exit code != 0.
    """
    # Build a fake manifest dict without display_name by mocking the
    # cache read for one of the active roles.
    def fake_read_manifest(role_id):
        if role_id == "pm":
            return {"id": "pm", "tagline": "x", "description": "y"}  # no display_name
        # Pass through to real read for others by clearing cache once
        return compose._read_role_manifest.__wrapped__(role_id) if hasattr(
            compose._read_role_manifest, "__wrapped__"
        ) else compose._ROLE_MANIFEST_CACHE.get(role_id)

    # Simpler: directly seed the cache so PM has no display_name.
    compose._ROLE_MANIFEST_CACHE.clear()
    try:
        compose._ROLE_MANIFEST_CACHE["pm"] = {
            "id": "pm", "tagline": "x", "description": "y",
        }
        with pytest.raises(SystemExit) as exc_info:
            compose._render_role_roster()
        assert exc_info.value.code != 0, (
            "AC11: missing display_name must exit with non-zero status"
        )
    finally:
        compose._ROLE_MANIFEST_CACHE.clear()


def test_ac11_missing_marker_emits_warning_and_continues(capsys):
    """AC11/D8: if `{{role-roster}}` marker is absent from composed
    content, compose emits a stderr warning and continues (does NOT
    crash). This covers the agent-boundaries-not-included edge case.
    """
    out = compose._inject_role_roster("hello world\n", "pm")
    assert out == "hello world\n", "no marker → content unchanged"
    captured = capsys.readouterr()
    assert "WARNING" in captured.err
    assert "role-roster" in captured.err


def test_ac11_missing_tagline_or_description_warns_but_succeeds(capsys):
    """AC11/D8: missing tagline OR description in a manifest produces a
    warning but does NOT crash. Both fields are optional in the
    degraded path."""
    compose._ROLE_MANIFEST_CACHE.clear()
    try:
        compose._ROLE_MANIFEST_CACHE["pm"] = {
            "id": "pm", "display_name": "PM",  # no tagline/description
        }
        # Don't actually go through the full sweep — just render the roster
        # and ensure it doesn't raise.
        block = compose._render_role_roster()
        assert "PM" in block
    finally:
        compose._ROLE_MANIFEST_CACHE.clear()
    captured = capsys.readouterr()
    # At least one of the two missing-field warnings should fire (since
    # the cached PM has neither tagline nor description).
    assert "WARNING" in captured.err
