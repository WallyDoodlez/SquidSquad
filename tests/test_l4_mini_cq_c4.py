"""Tests for references/scripts/l4_mini_cq.py (#10653, PRD-C C4)."""

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import l4_mini_cq  # noqa: E402


# ---------------------------------------------------------------------------
# AC1: format_confirmation — canonical message shape
# ---------------------------------------------------------------------------

def test_format_confirmation_step_targeted_op():
    msg = l4_mini_cq.format_confirmation(
        op_type="insert-before step:cycle/file-bug",
        target="",  # step-targeted ops carry the target inside op_type for this AC's shape
        slot="instructions",
        role_class="pm",
    )
    assert msg == "Adding `insert-before step:cycle/file-bug` under `instructions` of `pm` — OK?"


def test_format_confirmation_append_no_target():
    msg = l4_mini_cq.format_confirmation(
        op_type="append", target="", slot="instructions", role_class="worker",
    )
    assert msg == "Adding `append` under `instructions` of `worker` — OK?"


def test_format_confirmation_whole_slot_replace():
    msg = l4_mini_cq.format_confirmation(
        op_type="replace", target="", slot="responsibility", role_class="dm",
    )
    assert msg == "Adding `replace` under `responsibility` of `dm` — OK?"


def test_format_confirmation_with_target_string():
    """If the caller passes the target as a separate string, it gets appended."""
    msg = l4_mini_cq.format_confirmation(
        op_type="insert-after",
        target="step:cycle/work",
        slot="instructions",
        role_class="verifier",
    )
    assert msg == "Adding `insert-after step:cycle/work` under `instructions` of `verifier` — OK?"


def test_format_confirmation_strips_whitespace():
    msg = l4_mini_cq.format_confirmation(
        op_type="  append  ",
        target="",
        slot="\tinstructions\t",
        role_class=" pm \n",
    )
    assert msg == "Adding `append` under `instructions` of `pm` — OK?"


# ---------------------------------------------------------------------------
# AC2: approval parser — positive recognition (case + whitespace tolerant)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("reply", [
    "yes", "Yes", "YES", "  yes  ", "yes!", "yes.",
    "y", "Y",
    "ok", "OK", "Ok", " ok ", "ok.",
    "okay", "OKAY",
    "go", "GO",
    "go ahead",
    "do it", "do that",
    "confirm", "confirmed",
    "approve", "approved", "APPROVED",
    "sure", "yep", "yeah", "yup",
    "lgtm", "LGTM", "looks good", "looks good to me",
    "ship it",
])
def test_classify_reply_recognizes_approvals(reply):
    assert l4_mini_cq.classify_reply(reply) == "approve"


@pytest.mark.parametrize("reply", [
    "yes please",
    "ok cool",
    "go ahead now",
    "sure thing",
    "yes that's right",
    "ok do it",
])
def test_classify_reply_recognizes_multi_word_approvals(reply):
    assert l4_mini_cq.classify_reply(reply) == "approve"


# ---------------------------------------------------------------------------
# AC3: negative path
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("reply", [
    "no", "No", "NO", " no ",
    "nope", "nah",
    "cancel", "CANCEL", "abort", "stop",
    "never mind", "nevermind",
    "wait",
    "no thanks",
    "no don't",
])
def test_classify_reply_recognizes_rejections(reply):
    assert l4_mini_cq.classify_reply(reply) == "reject"


# ---------------------------------------------------------------------------
# AC4: ambiguous path
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("reply", [
    "",  # empty
    "   ",  # whitespace only
    "what does that mean?",
    "can you explain the target?",
    "hmm",
    "maybe",
    "I'm not sure",
    "yes but actually no",  # mixed signal — head match would falsely approve
    "well it depends",
    "what about the other step?",
    "show me the diff first",
    None,  # explicit None
])
def test_classify_reply_returns_ambiguous_for_unclear(reply):
    assert l4_mini_cq.classify_reply(reply) == "ambiguous"


def test_classify_reply_conservative_on_mixed_signals():
    """Conservative classifier: 'yes but no' is ambiguous, NOT approve.

    Catches the failure mode where a head-word matcher would treat any
    reply starting with 'yes' as approval.
    """
    assert l4_mini_cq.classify_reply("yes but no") == "ambiguous"
    assert l4_mini_cq.classify_reply("yes but actually no") == "ambiguous"


def test_classify_reply_punctuation_tolerant():
    assert l4_mini_cq.classify_reply("yes!!!") == "approve"
    assert l4_mini_cq.classify_reply("...ok.") == "approve"
    assert l4_mini_cq.classify_reply("no?") == "reject"


# ---------------------------------------------------------------------------
# Parser semantics — boundaries
# ---------------------------------------------------------------------------

def test_classify_reply_returns_string_literals():
    """The result is exactly one of three string literals callers branch on."""
    for sample in ("yes", "no", "what?"):
        result = l4_mini_cq.classify_reply(sample)
        assert result in ("approve", "reject", "ambiguous")


def test_classify_reply_does_not_match_inside_longer_word():
    """`yesterday` shouldn't approve; `nope` IS reject but `nopey` shouldn't."""
    assert l4_mini_cq.classify_reply("yesterday I said yes") == "ambiguous"
    # `nope` matches; `nopey` is not a known token → ambiguous.
    assert l4_mini_cq.classify_reply("nopey") == "ambiguous"


def test_format_confirmation_uses_em_dash_before_ok():
    msg = l4_mini_cq.format_confirmation("append", "", "soul", "pm")
    assert "— OK?" in msg
    # NOT a regular hyphen
    assert "- OK?" not in msg
