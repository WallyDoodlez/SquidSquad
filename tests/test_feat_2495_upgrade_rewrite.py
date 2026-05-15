"""
FEAT-QA-2495 — Rewrite /squidsquad-upgrade
Test plan execution for FEAT-PM-2495-TEST-PLAN.md

Note: .claude/commands/squidsquad-upgrade.md is gitignored by design — it is generated
per-install from SKILL.md. The tracked source of truth is SKILL.md's upgrade section.
TC-2 checks SKILL.md's upgrade section for the same content when the command file is absent.
"""

import re
import subprocess
from pathlib import Path

# Repo root
REPO = Path(__file__).resolve().parents[1]
SKILL_MD = REPO / "SKILL.md"
UPGRADE_CMD = REPO / ".claude" / "commands" / "squidsquad-upgrade.md"

OBSOLETE_TERMS = [
    "agent-instructions.md",
    r"\.squidsquad/templates/",
    "Tracker Schema",
]

# These placeholders are obsolete when used as MANUAL substitution instructions.
# They are allowed to appear when explaining that compose.py handles them automatically.
# We check for the manual-substitution anti-pattern separately.
MANUAL_SUBSTITUTION_PATTERN = re.compile(
    r"(replace|substitute|sed|manually|fill in|edit).{0,80}\[ROLE[_A-Z]*\]",
    flags=re.IGNORECASE | re.DOTALL,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_skill_upgrade_section() -> str:
    """Return the text of the ## Upgrade Instructions section from SKILL.md."""
    text = SKILL_MD.read_text(encoding="utf-8")
    # Find from ## Upgrade Instructions to the next top-level ##
    match = re.search(
        r"^## Upgrade Instructions\b.*?(?=^## |\Z)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match, "## Upgrade Instructions section not found in SKILL.md"
    return match.group(0)


def _upgrade_source_text() -> tuple[str, str]:
    """
    Return (source_label, text) for the upgrade instructions.
    Prefers .claude/commands/squidsquad-upgrade.md when it exists;
    falls back to SKILL.md upgrade section.
    """
    if UPGRADE_CMD.exists():
        return "squidsquad-upgrade.md", UPGRADE_CMD.read_text(encoding="utf-8")
    return "SKILL.md (upgrade section)", _read_skill_upgrade_section()


# ---------------------------------------------------------------------------
# TC-1: SKILL.md upgrade section rewritten — no obsolete references
# ---------------------------------------------------------------------------

def test_tc_01_skill_md_rewritten():
    """
    TC-1: SKILL.md upgrade section must not contain any obsolete architecture
    references (agent-instructions.md, manual [ROLE] substitution, old template dir,
    parallel subagent fan-out).
    """
    upgrade_text = _read_skill_upgrade_section()

    for term in OBSOLETE_TERMS:
        matches = re.findall(term, upgrade_text)
        assert not matches, (
            f"SKILL.md upgrade section still references obsolete term '{term}'. "
            f"Found: {matches}"
        )

    # [ROLE] etc. may appear when explaining compose.py handles them automatically,
    # but must NOT appear as manual-substitution instructions.
    manual_sub = MANUAL_SUBSTITUTION_PATTERN.search(upgrade_text)
    assert not manual_sub, (
        f"SKILL.md upgrade section still instructs manual [ROLE] substitution: "
        f"{manual_sub.group(0)[:120]!r}"
    )


# ---------------------------------------------------------------------------
# TC-2: Upgrade skill file rewritten — no obsolete references
# ---------------------------------------------------------------------------

def test_tc_02_skill_file_rewritten():
    """
    TC-2: The upgrade instructions source (squidsquad-upgrade.md if present,
    otherwise SKILL.md upgrade section) must not reference obsolete terms.
    """
    label, text = _upgrade_source_text()

    for term in OBSOLETE_TERMS:
        matches = re.findall(term, text)
        assert not matches, (
            f"{label} still references obsolete term '{term}'. Found: {matches}"
        )

    # Must NOT reference agent-instructions.md as a template source
    assert "agent-instructions.md" not in text, (
        f"{label}: still references agent-instructions.md as a template source"
    )

    # [ROLE] etc. may appear when explaining compose.py handles them automatically,
    # but must NOT appear as manual-substitution instructions.
    manual_sub = MANUAL_SUBSTITUTION_PATTERN.search(text)
    assert not manual_sub, (
        f"{label}: still instructs manual [ROLE] substitution: "
        f"{manual_sub.group(0)[:120]!r}"
    )


# ---------------------------------------------------------------------------
# TC-3: SKILL.md and skill file agree — same key steps present in both
# ---------------------------------------------------------------------------

def test_tc_03_skill_md_and_skill_file_agree():
    """
    TC-3: Key upgrade steps must appear in both SKILL.md (upgrade section)
    and squidsquad-upgrade.md (or the same section when file is absent).
    When the file is absent, we verify the steps appear in SKILL.md itself.
    """
    skill_upgrade = _read_skill_upgrade_section()

    key_steps = [
        "compose.py deploy-all",
        "SOUL.md",
        "ensure-labels",
    ]

    if UPGRADE_CMD.exists():
        cmd_text = UPGRADE_CMD.read_text(encoding="utf-8")
        # Both files must mention each key step
        for step in key_steps:
            assert step in skill_upgrade, (
                f"SKILL.md upgrade section is missing key step: '{step}'"
            )
            assert step in cmd_text, (
                f"squidsquad-upgrade.md is missing key step: '{step}'"
            )
    else:
        # File is gitignored — verify all key steps are in SKILL.md upgrade section
        for step in key_steps:
            assert step in skill_upgrade, (
                f"SKILL.md upgrade section is missing key step: '{step}' "
                f"(.claude/commands/squidsquad-upgrade.md not present — SKILL.md is source of truth)"
            )


# ---------------------------------------------------------------------------
# TC-4: compose.py deploy-all is the template regeneration method
# ---------------------------------------------------------------------------

def test_tc_04_compose_deploy_all_is_primary():
    """
    TC-4: Both upgrade sources must reference 'compose.py deploy-all' as the
    primary template regeneration command.
    """
    skill_upgrade = _read_skill_upgrade_section()
    assert "compose.py deploy-all" in skill_upgrade, (
        "SKILL.md upgrade section does not mention 'compose.py deploy-all'"
    )

    label, text = _upgrade_source_text()
    assert "compose.py deploy-all" in text, (
        f"{label} does not mention 'compose.py deploy-all'"
    )


# ---------------------------------------------------------------------------
# TC-5: SOUL.md preservation documented
# ---------------------------------------------------------------------------

def test_tc_05_soul_md_preservation_documented():
    """
    TC-5: SKILL.md upgrade section must explicitly state that SOUL.md
    customizations are preserved across upgrades.
    """
    upgrade_text = _read_skill_upgrade_section()

    assert "SOUL.md" in upgrade_text, (
        "SKILL.md upgrade section does not mention SOUL.md"
    )

    # Check that preservation semantics appear near SOUL.md mention
    soul_context = re.search(
        r"SOUL\.md.{0,200}",
        upgrade_text,
        flags=re.DOTALL,
    )
    assert soul_context, "Cannot find SOUL.md context in upgrade section"

    soul_snippet = soul_context.group(0).lower()
    preservation_words = ["preserv", "never overwrit", "customiz", "missing"]
    found = any(w in soul_snippet for w in preservation_words)
    assert found, (
        f"SOUL.md mention in upgrade section does not describe preservation. "
        f"Snippet: {soul_context.group(0)[:200]}"
    )


# ---------------------------------------------------------------------------
# TC-6: Config v1→v2 patching documented — mentions config patching with defaults
# ---------------------------------------------------------------------------

def test_tc_06_config_v1_v2_patching():
    """
    TC-6: The upgrade section must describe config v1→v2 patching:
    - mentions Architecture Version 2
    - instructs adding missing sections with defaults
    - instructs NOT deleting existing v1 sections
    """
    upgrade_text = _read_skill_upgrade_section()

    assert "Architecture Version" in upgrade_text, (
        "SKILL.md upgrade section does not mention 'Architecture Version'"
    )

    # Must mention setting it to 2
    assert re.search(r"Architecture Version.*?2", upgrade_text, flags=re.DOTALL), (
        "SKILL.md upgrade section does not set Architecture Version to 2"
    )

    # Must instruct adding missing sections (not deleting v1 sections)
    lower = upgrade_text.lower()
    assert "default" in lower, (
        "SKILL.md upgrade section does not mention defaults when patching config"
    )

    # Must explicitly say NOT to delete existing v1 sections.
    # Pattern: negation word within 30 chars before (delete|remove) applied to v1 sections.
    no_delete_instruction = re.search(
        r"(do not|don.t|never|not)\s+(delete|remove|touch)\s+(existing\s+)?v1\s+section",
        upgrade_text,
        flags=re.IGNORECASE,
    )
    assert no_delete_instruction, (
        "SKILL.md upgrade section does not explicitly say not to delete existing v1 sections"
    )

    # Confirm there is no unconditional delete instruction (without negation)
    # Find all (delete|remove) v1 section occurrences and check each is negated
    for m in re.finditer(r"(delete|remove)\s+(existing\s+)?v1\s+section", upgrade_text, flags=re.IGNORECASE):
        # Look back 50 chars for a negation
        before = upgrade_text[max(0, m.start()-50):m.start()]
        has_negation = bool(re.search(r"(not|never|do not|don.t|no)", before, flags=re.IGNORECASE))
        assert has_negation, (
            f"SKILL.md upgrade section contains an un-negated delete v1 section instruction: "
            f"'{upgrade_text[max(0,m.start()-50):m.end()]}'"
        )


# ---------------------------------------------------------------------------
# TC-7: No-install-spec fallback documented
# ---------------------------------------------------------------------------

def test_tc_07_no_install_spec_fallback():
    """
    TC-7: Upgrade instructions must describe the fallback when
    .install-spec.json does not exist.
    """
    upgrade_text = _read_skill_upgrade_section()

    has_install_spec = "install-spec" in upgrade_text or ".install-spec.json" in upgrade_text
    assert has_install_spec, (
        "SKILL.md upgrade section does not mention .install-spec.json or install-spec fallback"
    )

    # Must mention deriving agents from config.md when install-spec is absent
    has_fallback = re.search(
        r"(does not exist|absent|not present|pre-install-spec|without it).{0,200}(config\.md|Dev Agents)",
        upgrade_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    assert has_fallback, (
        "SKILL.md upgrade section does not describe the no-install-spec fallback "
        "(derive agent list from config.md Dev Agents)"
    )


# ---------------------------------------------------------------------------
# TC-8: wizard.py ensure-labels included as an upgrade step
# ---------------------------------------------------------------------------

def test_tc_08_ensure_labels_included():
    """
    TC-8: Both upgrade sources must mention 'ensure-labels' as an upgrade step.
    """
    skill_upgrade = _read_skill_upgrade_section()
    assert "ensure-labels" in skill_upgrade, (
        "SKILL.md upgrade section does not include wizard.py ensure-labels step"
    )

    label, text = _upgrade_source_text()
    assert "ensure-labels" in text, (
        f"{label} does not include wizard.py ensure-labels step"
    )


# ---------------------------------------------------------------------------
# TC-9: Clone isolation documented
# ---------------------------------------------------------------------------

def test_tc_09_clone_isolation_documented():
    """
    TC-9: Upgrade instructions must note that agents in sibling clones get the
    updated CLAUDE.md on their next git pull, not immediately.
    """
    upgrade_text = _read_skill_upgrade_section()

    has_clone_note = re.search(
        r"(clone|sibling).{0,200}(git pull|next.*pull|pull.*next)",
        upgrade_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    assert has_clone_note, (
        "SKILL.md upgrade section does not note clone isolation "
        "(agents get updated CLAUDE.md on next git pull)"
    )


# ---------------------------------------------------------------------------
# TC-10: Tracker Schema check removed
# ---------------------------------------------------------------------------

def test_tc_10_tracker_schema_check_removed():
    """
    TC-10: Neither the upgrade skill file nor the SKILL.md upgrade section
    should reference 'Tracker Schema'.
    """
    skill_upgrade = _read_skill_upgrade_section()
    assert "Tracker Schema" not in skill_upgrade, (
        "SKILL.md upgrade section still references 'Tracker Schema' (obsolete field)"
    )

    label, text = _upgrade_source_text()
    assert "Tracker Schema" not in text, (
        f"{label} still references 'Tracker Schema' (obsolete field)"
    )


# ---------------------------------------------------------------------------
# TC-11: Upgrade commit must not stage .claude/ (#7879)
# ---------------------------------------------------------------------------

def test_tc_11_no_claude_dir_in_commit():
    """
    TC-11 (#7879): The upgrade commit step must only stage .squidsquad/,
    not .claude/. Staging .claude/ silently bundles unrelated user edits
    (settings, memory files) into the upgrade commit.
    """
    upgrade_text = _read_skill_upgrade_section()

    # Find all git add commands in the upgrade section
    git_adds = re.findall(r"git add\b.*", upgrade_text)
    assert git_adds, "SKILL.md upgrade section has no git add command"

    for cmd in git_adds:
        assert ".claude" not in cmd, (
            f"SKILL.md upgrade section stages .claude/ in commit: '{cmd}'. "
            f"Only .squidsquad/ should be staged — .claude/ may contain unrelated user edits."
        )

    label, text = _upgrade_source_text()
    git_adds = re.findall(r"git add\b.*", text)
    assert git_adds, f"{label} has no git add command"

    for cmd in git_adds:
        assert ".claude" not in cmd, (
            f"{label} stages .claude/ in commit: '{cmd}'. "
            f"Only .squidsquad/ should be staged."
        )
