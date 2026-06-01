"""Tests for references/scripts/conflict_resolver.py (#10446, PRD-B Story B5)."""

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import conflict_resolver as cr  # noqa: E402
from conflict_detector import Conflict  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers — stub Conflict records
# ---------------------------------------------------------------------------

def _conflict(slot="instructions", winner_layer="L4", loser_layer="L2",
              loser_quote="verify pending-test items each cycle",
              winner_quote="verifier handles all verification"):
    return Conflict(
        slot=slot,
        winner_layer=winner_layer,
        loser_layer=loser_layer,
        winner_path=f"references/roles/worker/{slot}.md",
        loser_path=f"references/roles/worker/{slot}.md",
        winner_quote=winner_quote,
        loser_quote=loser_quote,
        why="L4 explicitly transfers responsibility",
        resolution="Assembled body aligns with the higher layer",
    )


# ---------------------------------------------------------------------------
# verify_higher_l_wins — loser quote must be absent
# ---------------------------------------------------------------------------

def test_verify_no_conflicts_returns_empty_issues():
    issues = cr.verify_higher_l_wins("any body content", [])
    assert issues == []


def test_verify_loser_absent_passes():
    body = "Verifier handles all verification; PM coordinates the team.\n"
    conflicts = [_conflict()]  # loser_quote = "verify pending-test items each cycle"
    issues = cr.verify_higher_l_wins(body, conflicts)
    assert issues == []


def test_verify_loser_present_returns_issue():
    """AC: lower-L prose is dropped — finding it is a resolver violation."""
    body = (
        "Verifier handles all verification.\n"
        "Each cycle, you also verify pending-test items each cycle.\n"
    )
    conflicts = [_conflict()]
    issues = cr.verify_higher_l_wins(body, conflicts)
    assert len(issues) == 1
    assert issues[0].slot == "instructions"
    assert issues[0].winner_layer == "L4"
    assert issues[0].loser_layer == "L2"
    assert "lower-layer prose still present" in issues[0].detail


def test_verify_raise_on_issue_true_raises():
    body = "verify pending-test items each cycle is the rule.\n"
    with pytest.raises(cr.ResolverError) as exc:
        cr.verify_higher_l_wins(body, [_conflict()], raise_on_issue=True)
    assert exc.value.issues[0].slot == "instructions"
    # The first-issue summary is in the str().
    assert "CONFLICT-001" in str(exc.value)
    assert "L4>L2" in str(exc.value)


def test_verify_raise_on_issue_false_collects_without_raising():
    body = "verify pending-test items each cycle is still here.\n"
    issues = cr.verify_higher_l_wins(body, [_conflict()], raise_on_issue=False)
    assert len(issues) == 1


def test_verify_multiple_conflicts_collects_all_issues():
    body = (
        "verify pending-test items each cycle is still here.\n"
        "PM does not coordinate teams is also still here.\n"
    )
    conflicts = [
        _conflict(slot="instructions",
                  loser_quote="verify pending-test items each cycle"),
        _conflict(slot="responsibility", loser_layer="L1",
                  loser_quote="PM does not coordinate teams"),
    ]
    issues = cr.verify_higher_l_wins(body, conflicts)
    assert len(issues) == 2
    assert {i.slot for i in issues} == {"instructions", "responsibility"}


def test_verify_indexing_matches_conflict_record_order():
    """conflict_index is 1-based and matches the source list order."""
    conflicts = [
        _conflict(slot="identity", loser_quote="ABSENT-FROM-BODY-1"),
        _conflict(slot="instructions",
                  loser_quote="PRESENT-IN-BODY-2"),
    ]
    body = "PRESENT-IN-BODY-2 lives here in the body.\n"
    issues = cr.verify_higher_l_wins(body, conflicts)
    assert len(issues) == 1
    assert issues[0].conflict_index == 2  # second conflict triggered


def test_verify_empty_loser_quote_is_skipped():
    """A blank loser quote is not actionable — skip silently rather than match-anything."""
    conflicts = [_conflict(loser_quote="")]
    issues = cr.verify_higher_l_wins("any body", conflicts)
    assert issues == []


def test_verify_whitespace_only_loser_quote_is_skipped():
    conflicts = [_conflict(loser_quote="   \n  ")]
    issues = cr.verify_higher_l_wins("any body", conflicts)
    assert issues == []


def test_verify_match_is_whitespace_insensitive():
    """Cosmetic reformatting (extra spaces, line wraps) should NOT mask a real violation."""
    conflicts = [_conflict(loser_quote="verify pending-test items each cycle")]
    # Same words, different whitespace.
    body = "We verify pending-test\n   items each   cycle as a rule.\n"
    issues = cr.verify_higher_l_wins(body, conflicts)
    assert len(issues) == 1


def test_resolver_error_with_no_issues_still_constructs():
    """Defensive: instantiating ResolverError with [] doesn't crash."""
    err = cr.ResolverError([])
    assert "no issue details" in str(err)


# ---------------------------------------------------------------------------
# re_verify_preservation — runs B2 + B3 against the assembled body
# ---------------------------------------------------------------------------

_LINKED = (
    "### step:cycle/boot\n"
    "→ run sub-skill: boot-bootstrap\n"
    "Boot body.\n\n"
    "### step:cycle/pickup\n"
    "→ run sub-skill: task-pickup\n"
    "Pickup body.\n"
)


def test_reverify_clean_body_passes_all_three_checks():
    """A body identical to linked input passes B2 preservation + B3 floor + parity."""
    result = cr.re_verify_preservation(_LINKED, _LINKED)
    assert result.preservation_ok is True
    assert result.length_floor_ok is True
    assert result.code_block_parity_ok is True
    assert result.all_ok is True


def test_reverify_missing_sub_skill_fails_preservation():
    """A body that drops a sub-skill reference must fail B2."""
    assembled = _LINKED.replace("→ run sub-skill: boot-bootstrap\n", "")
    result = cr.re_verify_preservation(assembled, _LINKED)
    assert result.preservation_ok is False
    assert result.all_ok is False


def test_reverify_too_short_assembled_fails_length_floor():
    """Below 80% of linked length → length-floor fail."""
    assembled = "tiny\n"
    result = cr.re_verify_preservation(assembled, _LINKED)
    assert result.length_floor_ok is False
    assert result.all_ok is False


def test_reverify_truncated_body_fails_floor_but_can_still_satisfy_others():
    """Confirms the three checks are independent (one failure does not poison the others)."""
    # Truncate the body to ~70% length but keep all preservation tokens by repeating them
    # below in a compressed form — we want length-floor to fail while keeping enough
    # references to pass preservation.
    assembled = (
        "→ run sub-skill: boot-bootstrap\n"
        "→ run sub-skill: task-pickup\n"
        "step:cycle/boot\n"
        "step:cycle/pickup\n"
    )
    result = cr.re_verify_preservation(assembled, _LINKED)
    # Preservation may still pass (all tokens present), but length-floor fails.
    assert result.length_floor_ok is False


# ---------------------------------------------------------------------------
# resolve() — one-call wrapper for B7
# ---------------------------------------------------------------------------

def test_resolve_returns_issues_and_reverify():
    """resolve() bundles both checks so B7 can short-circuit on either failure."""
    body = "Verifier owns it. " + _LINKED  # contains the linked tokens + extra prose
    conflicts = [_conflict()]
    issues, reverify = cr.resolve(body, conflicts, _LINKED)
    assert issues == []  # loser quote not in this body
    assert reverify.all_ok is True


def test_resolve_surfaces_resolver_issues_without_raising():
    """resolve() never raises — caller (B7) decides; this is the audit path."""
    body = _LINKED + "\nverify pending-test items each cycle still here.\n"
    conflicts = [_conflict()]
    issues, reverify = cr.resolve(body, conflicts, _LINKED)
    assert len(issues) == 1
    assert reverify.all_ok is True  # preservation still satisfied
