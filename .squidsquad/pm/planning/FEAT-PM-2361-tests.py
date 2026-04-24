"""
QA tests for tc_coverage.py — TC coverage gate script.
Each test function corresponds to a TC in FEAT-PM-2361-TEST-PLAN.md.
"""

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = str(REPO_ROOT / "references" / "scripts" / "tc_coverage.py")
SQUID_DIR = REPO_ROOT / ".squidsquad"


def run_tc(args, cwd=None):
    """Run tc_coverage.py with given args, return CompletedProcess."""
    return subprocess.run(
        [sys.executable, SCRIPT] + args,
        capture_output=True,
        text=True,
        cwd=cwd or str(REPO_ROOT),
    )


def write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")


def _import_tc_coverage():
    """Import tc_coverage module with fresh reload."""
    scripts_dir = str(REPO_ROOT / "references" / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    import importlib
    import tc_coverage
    importlib.reload(tc_coverage)
    return tc_coverage


# ---------------------------------------------------------------------------
# TC-1: Happy path — full coverage, all PASS
# ---------------------------------------------------------------------------
def test_tc_01_happy_path_all_pass(tmp_path):
    plan = tmp_path / "TEST-PLAN.md"
    results = tmp_path / "QA-RESULTS.md"
    write_file(plan, """
# Test Plan
### TC-1: First
### TC-2: Second
### TC-3: Third
### TC-4: Fourth
### TC-5: Fifth
""")
    write_file(results, """
# QA Results
### TC-1: First
- **Result**: PASS
### TC-2: Second
- **Result**: PASS
### TC-3: Third
- **Result**: PASS
### TC-4: Fourth
- **Result**: PASS
### TC-5: Fifth
- **Result**: PASS
""")
    r = run_tc(["--test-plan", str(plan), "--qa-results", str(results)])
    assert r.returncode == 0, f"Expected exit 0, got {r.returncode}\nstdout: {r.stdout}\nstderr: {r.stderr}"
    assert "5/5" in r.stdout
    assert "100%" in r.stdout


# ---------------------------------------------------------------------------
# TC-2: Happy path — full coverage, mix of PASS and FAIL
# ---------------------------------------------------------------------------
def test_tc_02_happy_path_mixed_pass_fail(tmp_path):
    plan = tmp_path / "TEST-PLAN.md"
    results = tmp_path / "QA-RESULTS.md"
    write_file(plan, """
### TC-1: A
### TC-2: B
### TC-3: C
""")
    write_file(results, """
### TC-1: A
- **Result**: PASS
### TC-2: B
- **Result**: FAIL
### TC-3: C
- **Result**: PASS
""")
    r = run_tc(["--test-plan", str(plan), "--qa-results", str(results)])
    assert r.returncode == 0, f"Expected exit 0, got {r.returncode}\nstdout: {r.stdout}\nstderr: {r.stderr}"
    assert "3/3" in r.stdout
    assert "100%" in r.stdout


# ---------------------------------------------------------------------------
# TC-3: Gap detection — missing TCs in QA-RESULTS
# ---------------------------------------------------------------------------
def test_tc_03_gap_detection_missing_tcs(tmp_path):
    plan = tmp_path / "TEST-PLAN.md"
    results = tmp_path / "QA-RESULTS.md"
    write_file(plan, """
### TC-1: A
### TC-2: B
### TC-3: C
### TC-4: D
### TC-5: E
""")
    write_file(results, """
### TC-1: A
- **Result**: PASS
### TC-3: C
- **Result**: PASS
### TC-5: E
- **Result**: PASS
""")
    r = run_tc(["--test-plan", str(plan), "--qa-results", str(results)])
    assert r.returncode == 1, f"Expected exit 1, got {r.returncode}"
    combined = r.stdout + r.stderr
    assert "TC-2" in combined
    assert "TC-4" in combined
    assert "3/5" in r.stdout
    assert "60%" in r.stdout


# ---------------------------------------------------------------------------
# TC-4: Invalid result — "not applicable" rejected
# ---------------------------------------------------------------------------
def test_tc_04_invalid_result_not_applicable(tmp_path):
    plan = tmp_path / "TEST-PLAN.md"
    results = tmp_path / "QA-RESULTS.md"
    write_file(plan, """
### TC-1: A
### TC-2: B
""")
    write_file(results, """
### TC-1: A
- **Result**: PASS
### TC-2: B
- **Result**: not applicable
""")
    r = run_tc(["--test-plan", str(plan), "--qa-results", str(results)])
    assert r.returncode == 1, f"Expected exit 1, got {r.returncode}"
    combined = r.stdout + r.stderr
    assert "invalid" in combined.lower() or "INVALID" in combined
    assert "TC-2" in combined


# ---------------------------------------------------------------------------
# TC-5: Invalid result — "deferred" rejected
# ---------------------------------------------------------------------------
def test_tc_05_invalid_result_deferred(tmp_path):
    plan = tmp_path / "TEST-PLAN.md"
    results = tmp_path / "QA-RESULTS.md"
    write_file(plan, """
### TC-1: A
### TC-2: B
""")
    write_file(results, """
### TC-1: A
- **Result**: PASS
### TC-2: B
- **Result**: Deferred
""")
    r = run_tc(["--test-plan", str(plan), "--qa-results", str(results)])
    assert r.returncode == 1, f"Expected exit 1, got {r.returncode}"
    combined = r.stdout + r.stderr
    assert "TC-2" in combined
    assert "invalid" in combined.lower() or "INVALID" in combined


# ---------------------------------------------------------------------------
# TC-6: Tolerant parsing — TC-01 format (zero-padded)
# ---------------------------------------------------------------------------
def test_tc_06_tolerant_parsing_zero_padded(tmp_path):
    plan = tmp_path / "TEST-PLAN.md"
    results = tmp_path / "QA-RESULTS.md"
    write_file(plan, """
### TC-01: First
### TC-02: Second
""")
    write_file(results, """
### TC-01: First
- **Result**: PASS
### TC-02: Second
- **Result**: PASS
""")
    r = run_tc(["--test-plan", str(plan), "--qa-results", str(results)])
    assert r.returncode == 0, f"Expected exit 0, got {r.returncode}\nstdout: {r.stdout}\nstderr: {r.stderr}"
    assert "2/2" in r.stdout


# ---------------------------------------------------------------------------
# TC-7: Tolerant parsing — TC-1 (no zero-pad) format
# ---------------------------------------------------------------------------
def test_tc_07_tolerant_parsing_no_zero_pad(tmp_path):
    plan = tmp_path / "TEST-PLAN.md"
    results = tmp_path / "QA-RESULTS.md"
    write_file(plan, """
### TC-1: First
### TC-2: Second
""")
    write_file(results, """
### TC-1: First
- **Result**: PASS
### TC-2: Second
- **Result**: PASS
""")
    r = run_tc(["--test-plan", str(plan), "--qa-results", str(results)])
    assert r.returncode == 0, f"Expected exit 0, got {r.returncode}"


# ---------------------------------------------------------------------------
# TC-8: Tolerant parsing — "TC 01" (space instead of dash)
# ---------------------------------------------------------------------------
def test_tc_08_tolerant_parsing_space_separator(tmp_path):
    plan = tmp_path / "TEST-PLAN.md"
    results = tmp_path / "QA-RESULTS.md"
    write_file(plan, """
### TC 01: First
### TC 02: Second
""")
    write_file(results, """
### TC 01: First
- **Result**: PASS
### TC 02: Second
- **Result**: PASS
""")
    r = run_tc(["--test-plan", str(plan), "--qa-results", str(results)])
    assert r.returncode == 0, f"Expected exit 0, got {r.returncode}\nstdout: {r.stdout}\nstderr: {r.stderr}"


# ---------------------------------------------------------------------------
# TC-9: Tolerant parsing — cross-format matching
# ---------------------------------------------------------------------------
def test_tc_09_tolerant_parsing_cross_format(tmp_path):
    plan = tmp_path / "TEST-PLAN.md"
    results = tmp_path / "QA-RESULTS.md"
    write_file(plan, """
### TC-01: First
""")
    write_file(results, """
### TC-1: First
- **Result**: PASS
""")
    r = run_tc(["--test-plan", str(plan), "--qa-results", str(results)])
    assert r.returncode == 0, f"Expected exit 0, got {r.returncode}\nstdout: {r.stdout}\nstderr: {r.stderr}"
    assert "missing" not in (r.stdout + r.stderr).lower()


# ---------------------------------------------------------------------------
# TC-10: Auto-discovery by issue number
# ---------------------------------------------------------------------------
def test_tc_10_auto_discovery_by_issue():
    """Auto-discovery using --issue flag. FEAT-PM-2361-TEST-PLAN.md exists in the repo."""
    r = run_tc(["--issue", "2361"])
    combined = r.stdout + r.stderr
    # The test plan exists. If QA-RESULTS doesn't exist yet, exit 1 with
    # "Test plan found but no QA-RESULTS". Either way, "no test plan found" should NOT appear.
    assert "no test plan found" not in combined.lower(), \
        f"Should discover the test plan.\nstdout: {r.stdout}\nstderr: {r.stderr}"


# ---------------------------------------------------------------------------
# TC-11: Auto-discovery — multiple planning dirs, PM preferred
# ---------------------------------------------------------------------------
def test_tc_11_auto_discovery_pm_preferred(tmp_path):
    """Create both PM and skill planning dirs. PM should be preferred."""
    squid = tmp_path / ".squidsquad"
    pm_plan_dir = squid / "pm" / "planning"
    skill_plan_dir = squid / "skill" / "planning"
    pm_plan_dir.mkdir(parents=True)
    skill_plan_dir.mkdir(parents=True)

    write_file(pm_plan_dir / "FEAT-PM-2361-TEST-PLAN.md", "### TC-1: PM Plan\n")
    write_file(pm_plan_dir / "FEAT-PM-2361-QA-RESULTS.md", "### TC-1: PM Plan\n- **Result**: PASS\n")
    write_file(skill_plan_dir / "FEAT-SKILL-2361-TEST-PLAN.md", "### TC-1: Skill Plan\n### TC-2: Skill Extra\n")
    write_file(skill_plan_dir / "FEAT-SKILL-2361-QA-RESULTS.md", "### TC-1: Skill Plan\n- **Result**: PASS\n")

    mod = _import_tc_coverage()
    old_squid = mod.SQUID_DIR
    mod.SQUID_DIR = squid
    try:
        tp, qr = mod._discover_files(2361)
        assert tp is not None
        assert "pm" in str(tp), f"PM path should be preferred, got {tp}"
    finally:
        mod.SQUID_DIR = old_squid


# ---------------------------------------------------------------------------
# TC-12: Multiple revisions — picks highest -RN
# ---------------------------------------------------------------------------
def test_tc_12_multiple_revisions_highest(tmp_path):
    squid = tmp_path / ".squidsquad"
    pm_dir = squid / "pm" / "planning"
    pm_dir.mkdir(parents=True)

    write_file(pm_dir / "FEAT-PM-100-TEST-PLAN.md", "### TC-1: A\n")
    write_file(pm_dir / "FEAT-PM-100-QA-RESULTS.md", "### TC-1: A\n- **Result**: FAIL\n")
    write_file(pm_dir / "FEAT-PM-100-QA-RESULTS-R2.md", "### TC-1: A\n- **Result**: FAIL\n")
    write_file(pm_dir / "FEAT-PM-100-QA-RESULTS-R3.md", "### TC-1: A\n- **Result**: PASS\n")

    mod = _import_tc_coverage()
    old_squid = mod.SQUID_DIR
    mod.SQUID_DIR = squid
    try:
        tp, qr = mod._discover_files(100)
        assert qr is not None
        assert "R3" in qr.name, f"Expected R3 revision, got {qr.name}"
    finally:
        mod.SQUID_DIR = old_squid


# ---------------------------------------------------------------------------
# TC-13: Multiple revisions — base file used when no -RN exists
# ---------------------------------------------------------------------------
def test_tc_13_base_file_used_when_no_revisions(tmp_path):
    squid = tmp_path / ".squidsquad"
    pm_dir = squid / "pm" / "planning"
    pm_dir.mkdir(parents=True)

    write_file(pm_dir / "FEAT-PM-100-TEST-PLAN.md", "### TC-1: A\n")
    write_file(pm_dir / "FEAT-PM-100-QA-RESULTS.md", "### TC-1: A\n- **Result**: PASS\n")

    mod = _import_tc_coverage()
    old_squid = mod.SQUID_DIR
    mod.SQUID_DIR = squid
    try:
        tp, qr = mod._discover_files(100)
        assert qr is not None
        assert qr.name == "FEAT-PM-100-QA-RESULTS.md"
    finally:
        mod.SQUID_DIR = old_squid


# ---------------------------------------------------------------------------
# TC-14: No TEST-PLAN exists — gate skipped
# ---------------------------------------------------------------------------
def test_tc_14_no_test_plan_gate_skipped(tmp_path):
    squid = tmp_path / ".squidsquad"
    pm_dir = squid / "pm" / "planning"
    pm_dir.mkdir(parents=True)

    mod = _import_tc_coverage()
    old_squid = mod.SQUID_DIR
    mod.SQUID_DIR = squid
    try:
        tp, qr = mod._discover_files(9999)
        assert tp is None, "Should find no test plan"
    finally:
        mod.SQUID_DIR = old_squid

    # Also test via CLI (uses real repo — issue 99999 shouldn't exist)
    r = run_tc(["--issue", "99999"])
    assert r.returncode == 0
    combined = r.stdout + r.stderr
    assert "no test plan" in combined.lower() or "skipped" in combined.lower()


# ---------------------------------------------------------------------------
# TC-15: BLOCKED results — counted as covered but block shipping
# ---------------------------------------------------------------------------
def test_tc_15_blocked_results(tmp_path):
    plan = tmp_path / "TEST-PLAN.md"
    results = tmp_path / "QA-RESULTS.md"
    write_file(plan, """
### TC-1: A
### TC-2: B
### TC-3: C
""")
    write_file(results, """
### TC-1: A
- **Result**: PASS
### TC-2: B
- **Result**: BLOCKED
### TC-3: C
- **Result**: PASS
""")
    r = run_tc(["--test-plan", str(plan), "--qa-results", str(results)])
    assert r.returncode != 0, f"Expected non-zero exit, got {r.returncode}"
    assert r.returncode == 2, f"Expected exit 2 for BLOCKED, got {r.returncode}"
    assert "100%" in r.stdout
    assert "3/3" in r.stdout
    combined = r.stdout + r.stderr
    assert "BLOCKED" in combined


# ---------------------------------------------------------------------------
# TC-16: --force does NOT bypass TC coverage (tracker.py integration)
# ---------------------------------------------------------------------------
def test_tc_16_force_no_bypass():
    """TC-16 requires a real GitHub Issue environment. Mark HUMAN-REQUIRED."""
    pytest.skip("HUMAN-REQUIRED: requires real GitHub Issue for tracker.py integration")


# ---------------------------------------------------------------------------
# TC-17: tracker.py integration — pending-test to pending-ship blocked
# ---------------------------------------------------------------------------
def test_tc_17_tracker_pending_test_blocked():
    """TC-17 requires a real GitHub Issue environment. Mark HUMAN-REQUIRED."""
    pytest.skip("HUMAN-REQUIRED: requires real GitHub Issue for tracker.py integration")


# ---------------------------------------------------------------------------
# TC-18: tracker.py integration — pending-test to pending-ship allowed
# ---------------------------------------------------------------------------
def test_tc_18_tracker_pending_test_allowed():
    """TC-18 requires a real GitHub Issue environment. Mark HUMAN-REQUIRED."""
    pytest.skip("HUMAN-REQUIRED: requires real GitHub Issue for tracker.py integration")


# ---------------------------------------------------------------------------
# TC-19: Graceful degradation — tc_coverage.py missing
# ---------------------------------------------------------------------------
def test_tc_19_graceful_degradation_missing_script():
    """TC-19 requires tracker.py integration with a real issue. Mark HUMAN-REQUIRED."""
    pytest.skip("HUMAN-REQUIRED: requires real GitHub Issue for tracker.py integration")


# ---------------------------------------------------------------------------
# TC-20: Edge case — duplicate TC IDs in TEST-PLAN
# ---------------------------------------------------------------------------
def test_tc_20_duplicate_tc_ids_in_plan(tmp_path):
    plan = tmp_path / "TEST-PLAN.md"
    results = tmp_path / "QA-RESULTS.md"
    write_file(plan, """
### TC-1: First occurrence
### TC-1: Duplicate occurrence
""")
    write_file(results, """
### TC-1: Something
- **Result**: PASS
""")
    r = run_tc(["--test-plan", str(plan), "--qa-results", str(results)])
    assert r.returncode == 1, f"Expected exit 1, got {r.returncode}"
    combined = r.stdout + r.stderr
    assert "duplicate" in combined.lower()
    assert "TC-1" in combined


# ---------------------------------------------------------------------------
# TC-21: Edge case — extra TCs in QA-RESULTS not in TEST-PLAN
# ---------------------------------------------------------------------------
def test_tc_21_extra_tcs_in_results(tmp_path):
    plan = tmp_path / "TEST-PLAN.md"
    results = tmp_path / "QA-RESULTS.md"
    write_file(plan, """
### TC-1: A
### TC-2: B
""")
    write_file(results, """
### TC-1: A
- **Result**: PASS
### TC-2: B
- **Result**: PASS
### TC-3: C (extra)
- **Result**: PASS
""")
    r = run_tc(["--test-plan", str(plan), "--qa-results", str(results)])
    combined = r.stdout + r.stderr
    assert "TC-3" in combined, f"TC-3 should be flagged as extra.\nstdout: {r.stdout}\nstderr: {r.stderr}"
    assert "2/2" in r.stdout


# ---------------------------------------------------------------------------
# TC-22: Edge case — empty TEST-PLAN (no TCs)
# ---------------------------------------------------------------------------
def test_tc_22_empty_test_plan(tmp_path):
    plan = tmp_path / "TEST-PLAN.md"
    results = tmp_path / "QA-RESULTS.md"
    write_file(plan, """
# Test Plan
This plan has no test cases, only prose.
""")
    write_file(results, """
# QA Results
Nothing here either.
""")
    r = run_tc(["--test-plan", str(plan), "--qa-results", str(results)])
    assert r.returncode == 0, f"Expected exit 0, got {r.returncode}"
    assert "0" in r.stdout


# ---------------------------------------------------------------------------
# TC-23: Edge case — empty QA-RESULTS (no TCs)
# ---------------------------------------------------------------------------
def test_tc_23_empty_qa_results(tmp_path):
    plan = tmp_path / "TEST-PLAN.md"
    results = tmp_path / "QA-RESULTS.md"
    write_file(plan, """
### TC-1: A
### TC-2: B
### TC-3: C
""")
    write_file(results, """
# QA Results
No test case entries here.
""")
    r = run_tc(["--test-plan", str(plan), "--qa-results", str(results)])
    assert r.returncode == 1, f"Expected exit 1, got {r.returncode}"
    assert "0/3" in r.stdout or "0%" in r.stdout
    combined = r.stdout + r.stderr
    assert "TC-1" in combined
    assert "TC-2" in combined
    assert "TC-3" in combined


# ---------------------------------------------------------------------------
# TC-24: --debug flag prints unmatched lines
# ---------------------------------------------------------------------------
def test_tc_24_debug_flag(tmp_path):
    plan = tmp_path / "TEST-PLAN.md"
    results = tmp_path / "QA-RESULTS.md"
    write_file(plan, """
### TC-1: A
""")
    write_file(results, """
# QA Results Header
Some prose that is not a TC marker.
### TC-1: A
- **Result**: PASS
Another unmatched line here.
""")
    r = run_tc(["--test-plan", str(plan), "--qa-results", str(results), "--debug"])
    assert r.returncode == 0
    combined = r.stdout + r.stderr
    assert "unmatched" in combined.lower() or "debug" in combined.lower()
    assert "Some prose" in combined or "prose" in combined.lower()


# ---------------------------------------------------------------------------
# TC-25: Prose references to TC numbers NOT counted as markers
# ---------------------------------------------------------------------------
def test_tc_25_prose_references_not_counted(tmp_path):
    plan = tmp_path / "TEST-PLAN.md"
    results = tmp_path / "QA-RESULTS.md"
    write_file(plan, """
### TC-1: First
### TC-2: Second
""")
    write_file(results, """
### TC-1: First
- **Result**: PASS

This paragraph references see TC-2 for details but has no heading for TC-2.
""")
    r = run_tc(["--test-plan", str(plan), "--qa-results", str(results)])
    assert r.returncode == 1, f"Expected exit 1 (TC-2 missing), got {r.returncode}"
    combined = r.stdout + r.stderr
    assert "TC-2" in combined


# ---------------------------------------------------------------------------
# TC-26: Table-row TC format recognized
# ---------------------------------------------------------------------------
def test_tc_26_table_row_format(tmp_path):
    plan = tmp_path / "TEST-PLAN.md"
    results = tmp_path / "QA-RESULTS.md"
    write_file(plan, """
### TC-1: First
""")
    write_file(results, """
| TC-1 | PASS | notes |
""")
    r = run_tc(["--test-plan", str(plan), "--qa-results", str(results)])
    assert r.returncode == 0, f"Expected exit 0, got {r.returncode}\nstdout: {r.stdout}\nstderr: {r.stderr}"


# ---------------------------------------------------------------------------
# Smoke Tests
# ---------------------------------------------------------------------------
class TestSmokeTests:
    def test_smoke_help(self):
        """--help runs without error and shows usage."""
        r = run_tc(["--help"])
        assert r.returncode == 0
        assert "usage" in r.stdout.lower() or "test-plan" in r.stdout.lower()

    def test_smoke_nonexistent_issue(self):
        """--issue 9999 (nonexistent) exits cleanly."""
        r = run_tc(["--issue", "9999"])
        assert r.returncode == 0
        combined = r.stdout + r.stderr
        assert "no test plan" in combined.lower() or "skipped" in combined.lower()

    def test_smoke_unit_tests_exist(self):
        """Check if tests/test_tc_coverage.py exists and passes."""
        test_file = REPO_ROOT / "tests" / "test_tc_coverage.py"
        if not test_file.exists():
            pytest.skip("tests/test_tc_coverage.py does not exist")
        r = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_file), "-v"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        assert r.returncode == 0, f"Unit tests failed:\n{r.stdout}\n{r.stderr}"
