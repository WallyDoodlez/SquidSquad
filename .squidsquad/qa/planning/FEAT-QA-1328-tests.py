"""
FEAT-QA-1328 — Verification skips blocked:human-action items.

Test plan derived from the feature implementation on branch squidsquad/skill/1328:
  - PM testing-and-verification.md (Steps 5 & 6)
  - QA verification.md (Steps 4 & 5)

Each TC maps to one aspect of the skip-blocked behaviour added by commit 7a85c0d2.
"""
import pytest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent.parent
PM_VERIFICATION = REPO / "references/sub-skills/pm-specific/testing-and-verification.md"
QA_VERIFICATION = REPO / "references/sub-skills/qa-specific/verification.md"


# ---------------------------------------------------------------------------
# TC-01  Source files exist
# ---------------------------------------------------------------------------

def test_tc_01_pm_verification_file_exists():
    """TC-01: PM testing-and-verification.md is present in the expected location."""
    assert PM_VERIFICATION.exists(), (
        f"PM verification sub-skill not found at {PM_VERIFICATION}"
    )


def test_tc_02_qa_verification_file_exists():
    """TC-02: QA verification.md is present in the expected location."""
    assert QA_VERIFICATION.exists(), (
        f"QA verification sub-skill not found at {QA_VERIFICATION}"
    )


# ---------------------------------------------------------------------------
# TC-03 / TC-04  PM Step 5 — verify fixed issues skips blocked items
# ---------------------------------------------------------------------------

def test_tc_03_pm_step5_has_blocked_check():
    """TC-03: PM Step 5 contains the blocked:human-action guard before it verifies anything."""
    text = PM_VERIFICATION.read_text(encoding="utf-8")
    step5_start = text.index("Step 5")
    step6_start = text.index("Step 6")
    step5_text = text[step5_start:step6_start]
    assert "blocked:human-action" in step5_text, (
        "PM Step 5 does not mention 'blocked:human-action'"
    )


def test_tc_04_pm_step5_skip_instruction():
    """TC-04: PM Step 5 blocked check tells the agent to skip the item, not change its status."""
    text = PM_VERIFICATION.read_text(encoding="utf-8")
    step5_start = text.index("Step 5")
    step6_start = text.index("Step 6")
    step5_text = text[step5_start:step6_start]
    # Must instruct agent to skip
    assert "skip" in step5_text.lower(), (
        "PM Step 5 blocked check does not contain a 'skip' instruction"
    )
    # Must NOT change its status
    assert "Do not change its status" in step5_text or "do not change its status" in step5_text.lower(), (
        "PM Step 5 blocked check does not say 'Do not change its status'"
    )


# ---------------------------------------------------------------------------
# TC-05 / TC-06  PM Step 6 — verify pending test tasks skips blocked items
# ---------------------------------------------------------------------------

def test_tc_05_pm_step6_has_blocked_check():
    """TC-05: PM Step 6 contains the blocked:human-action guard."""
    text = PM_VERIFICATION.read_text(encoding="utf-8")
    step6_start = text.index("Step 6 — Verify Pending Test Tasks")
    step6c_start = text.index("Step 6c")
    step6_text = text[step6_start:step6c_start]
    assert "blocked:human-action" in step6_text, (
        "PM Step 6 does not mention 'blocked:human-action'"
    )


def test_tc_06_pm_step6_skip_instruction():
    """TC-06: PM Step 6 blocked check tells the agent to skip and not change status."""
    text = PM_VERIFICATION.read_text(encoding="utf-8")
    step6_start = text.index("Step 6 — Verify Pending Test Tasks")
    step6c_start = text.index("Step 6c")
    step6_text = text[step6_start:step6c_start]
    assert "skip" in step6_text.lower(), (
        "PM Step 6 blocked check does not contain a 'skip' instruction"
    )
    assert "Do not change its status" in step6_text or "do not change its status" in step6_text.lower(), (
        "PM Step 6 blocked check does not say 'Do not change its status'"
    )


# ---------------------------------------------------------------------------
# TC-07  PM — at least two "Do not change its status" occurrences
# ---------------------------------------------------------------------------

def test_tc_07_pm_both_steps_have_no_status_change():
    """TC-07: PM verification has 'Do not change its status' in BOTH Step 5 and Step 6
    (one for issues, one for tasks)."""
    text = PM_VERIFICATION.read_text(encoding="utf-8")
    count = text.count("Do not change its status")
    assert count >= 2, (
        f"Expected at least 2 occurrences of 'Do not change its status' in PM verification "
        f"(one per step), found {count}"
    )


# ---------------------------------------------------------------------------
# TC-08 / TC-09  QA Step 4 — verify fixed issues skips blocked items
# ---------------------------------------------------------------------------

def test_tc_08_qa_step4_has_blocked_check():
    """TC-08: QA Step 4 contains the blocked:human-action guard."""
    text = QA_VERIFICATION.read_text(encoding="utf-8")
    step4_start = text.index("Step 4")
    step5_start = text.index("Step 5")
    step4_text = text[step4_start:step5_start]
    assert "blocked:human-action" in step4_text, (
        "QA Step 4 does not mention 'blocked:human-action'"
    )


def test_tc_09_qa_step4_skip_instruction():
    """TC-09: QA Step 4 blocked check instructs the agent to skip and not change status."""
    text = QA_VERIFICATION.read_text(encoding="utf-8")
    step4_start = text.index("Step 4")
    step5_start = text.index("Step 5")
    step4_text = text[step4_start:step5_start]
    assert "skip" in step4_text.lower(), (
        "QA Step 4 blocked check does not contain a 'skip' instruction"
    )
    assert "Do not change its status" in step4_text or "do not change its status" in step4_text.lower(), (
        "QA Step 4 blocked check does not say 'Do not change its status'"
    )


# ---------------------------------------------------------------------------
# TC-10 / TC-11  QA Step 5 — verify pending test tasks skips blocked items
# ---------------------------------------------------------------------------

def test_tc_10_qa_step5_has_blocked_check():
    """TC-10: QA Step 5 (Verify Pending Test Tasks) contains the blocked:human-action guard."""
    text = QA_VERIFICATION.read_text(encoding="utf-8")
    step5_start = text.index("Step 5 — Verify Pending Test Tasks")
    step5b_start = text.index("Step 5b")
    step5_text = text[step5_start:step5b_start]
    assert "blocked:human-action" in step5_text, (
        "QA Step 5 does not mention 'blocked:human-action'"
    )


def test_tc_11_qa_step5_skip_instruction():
    """TC-11: QA Step 5 blocked check instructs the agent to skip and not change status."""
    text = QA_VERIFICATION.read_text(encoding="utf-8")
    step5_start = text.index("Step 5 — Verify Pending Test Tasks")
    step5b_start = text.index("Step 5b")
    step5_text = text[step5_start:step5b_start]
    assert "skip" in step5_text.lower(), (
        "QA Step 5 blocked check does not contain a 'skip' instruction"
    )
    assert "Do not change its status" in step5_text or "do not change its status" in step5_text.lower(), (
        "QA Step 5 blocked check does not say 'Do not change its status'"
    )


# ---------------------------------------------------------------------------
# TC-12  QA — at least two "Do not change its status" occurrences
# ---------------------------------------------------------------------------

def test_tc_12_qa_both_steps_have_no_status_change():
    """TC-12: QA verification has 'Do not change its status' in BOTH Step 4 and Step 5
    (one for issues, one for tasks)."""
    text = QA_VERIFICATION.read_text(encoding="utf-8")
    count = text.count("Do not change its status")
    assert count >= 2, (
        f"Expected at least 2 occurrences of 'Do not change its status' in QA verification "
        f"(one per step), found {count}"
    )


# ---------------------------------------------------------------------------
# TC-13  Print marker present
# ---------------------------------------------------------------------------

def test_tc_13_pm_print_marker_for_blocked_skip():
    """TC-13: PM verification includes a log print marker for blocked-item skips,
    so humans can audit the skip in scrollback."""
    text = PM_VERIFICATION.read_text(encoding="utf-8")
    # The implementation should print a timestamped marker when skipping
    assert "Skipping #" in text or "blocked:human-action (waiting for human)" in text, (
        "PM verification does not include a print/log marker for blocked item skips"
    )


def test_tc_14_qa_print_marker_for_blocked_skip():
    """TC-14: QA verification includes a log print marker for blocked-item skips."""
    text = QA_VERIFICATION.read_text(encoding="utf-8")
    assert "Skipping #" in text or "blocked:human-action (waiting for human)" in text, (
        "QA verification does not include a print/log marker for blocked item skips"
    )


# ---------------------------------------------------------------------------
# TC-15  Regression — promoted test file exists in tests/
# ---------------------------------------------------------------------------

def test_tc_15_regression_test_file_exists_in_tests():
    """TC-15: A regression test file for feature #1328 has been promoted to tests/."""
    regression_file = REPO / "tests" / "test_feat_1328_blocked_skip.py"
    assert regression_file.exists(), (
        f"Regression test file not found at {regression_file}. "
        "The feature should have a test promoted to tests/."
    )


def test_tc_16_regression_test_file_is_non_empty():
    """TC-16: The promoted regression test file is non-empty and contains test functions."""
    regression_file = REPO / "tests" / "test_feat_1328_blocked_skip.py"
    if not regression_file.exists():
        pytest.skip("Regression file missing — covered by TC-15")
    content = regression_file.read_text(encoding="utf-8")
    assert "def test_" in content, (
        "Regression test file exists but contains no test functions"
    )
