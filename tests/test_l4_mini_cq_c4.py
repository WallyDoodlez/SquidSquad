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
# #10753 W3 — approval-prefix + politeness/intensifier suffix
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("reply", [
    # The three the audit specifically called out.
    "do it now",
    "ship it please",
    "y please",
    # Generalized: any approval prefix + non-rejection suffix should
    # approve. Tests below pin the behaviour at multiple prefix lengths.
    "yes please",
    "ok thanks",
    "go ahead now",
    "go for it please",
    "looks good to me thanks",
    "lgtm please",
    "approve please",
    "ship now",
    "do that please",
    "sure thing please",
])
def test_classify_reply_approval_prefix_with_polite_suffix(reply):
    """Pre-fix: the head-only allowlist treated every one of these as
    ambiguous despite each being a clear approval. Gate 2 would
    re-prompt or abandon — hurting throughput on the very interaction
    Gate 2 exists to validate."""
    assert l4_mini_cq.classify_reply(reply) == "approve"


@pytest.mark.parametrize("reply", [
    # Approval prefix BUT a negation in the rest demotes to ambiguous.
    "yes but no",
    "ok but actually stop",
    "do it but wait",
    "ship it but cancel",
    "go ahead but abort",
])
def test_classify_reply_approval_prefix_plus_negation_is_ambiguous(reply):
    """The relaxation in W3 must NOT swallow mixed-signal replies. A
    negation anywhere in the rest demotes the match to ambiguous —
    the conservative bias from the original implementation stays."""
    assert l4_mini_cq.classify_reply(reply) == "ambiguous"


@pytest.mark.parametrize("reply", [
    # Words that LOOK like they might be approval prefixes but
    # aren't in _APPROVAL_TOKENS — the relaxation must not promote
    # arbitrary first-word matches.
    "maybe later",
    "tomorrow please",
    "let's see",
    "show me first",
])
def test_classify_reply_non_approval_prefix_stays_ambiguous(reply):
    assert l4_mini_cq.classify_reply(reply) == "ambiguous"


# ---------------------------------------------------------------------------
# DS-10753 review F1 + F2 — false-positive risks from missing rejection
# tokens. The W3 relaxation matched a 1-4 word approval prefix; without
# "away" / "back" / "not" / "never" in _REJECTION_TOKENS, dismissals and
# questioning replies like "go away" or "y not" would incorrectly
# classify as approve.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("reply", [
    # DS-10753 F1: "go away" / "go back" — dismissals, NOT approvals.
    # "go" matches as a one-word approval prefix; the dismissal word in
    # the rest must demote to ambiguous.
    "go away",
    "go back",
    # DS-10753 F2: "y not" reads as "why not?" — a question, not an
    # approval. "do it not" / "ok never" same pattern. Each is the
    # exact failure mode the audit's "false approvals worse than
    # re-prompts" caveat targets.
    "y not",
    "do it not",
    "ok never",
    "yes not really",
    "sure never mind",
])
def test_classify_reply_dismissal_and_negation_after_approval_prefix_is_not_approve(
    reply,
):
    # Per the docstring: false approvals are worse than a re-prompt
    # because they commit an L4 write the human didn't intend. Each
    # of these replies must demote to ambiguous OR classify as reject
    # — but it must NEVER approve.
    assert l4_mini_cq.classify_reply(reply) != "approve"


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
