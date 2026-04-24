"""Tests for references/scripts/tc_coverage.py — TC coverage gate (#2361)."""

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import tc_coverage


# --- parse_tc_ids ---


class TestParseTcIds:
    """TC ID extraction from TEST-PLAN and QA-RESULTS markdown."""

    def test_heading_dash_format(self):
        text = "### TC-1: Happy path\n### TC-2: Edge case\n"
        assert tc_coverage.parse_tc_ids(text) == [1, 2]

    def test_heading_zero_padded(self):
        text = "### TC-01: First\n### TC-02: Second\n"
        assert tc_coverage.parse_tc_ids(text) == [1, 2]

    def test_heading_space_format(self):
        text = "### TC 01: Space separated\n### TC 02: Another\n"
        assert tc_coverage.parse_tc_ids(text) == [1, 2]

    def test_table_row_format(self):
        text = "| TC-1 | PASS | notes |\n| TC-2 | FAIL | notes |\n"
        assert tc_coverage.parse_tc_ids(text) == [1, 2]

    def test_cross_format_normalization(self):
        """TC-01 and TC-1 both normalize to 1."""
        text = "### TC-01: Zero padded\n### TC-1: No padding\n"
        ids = tc_coverage.parse_tc_ids(text)
        assert ids == [1, 1]  # Both normalize to 1 — duplicate detection happens elsewhere

    def test_prose_reference_not_matched(self):
        """Prose like 'see TC-2 for details' should NOT be extracted."""
        text = "### TC-1: Title\nSee TC-2 for details in the related section.\n"
        assert tc_coverage.parse_tc_ids(text) == [1]

    def test_empty_text(self):
        assert tc_coverage.parse_tc_ids("") == []

    def test_no_tcs(self):
        text = "# Test Plan\n\nSome prose without any TC markers.\n"
        assert tc_coverage.parse_tc_ids(text) == []


# --- parse_tc_results ---


class TestParseTcResults:
    """TC result extraction from QA-RESULTS markdown."""

    def test_pass_result(self):
        text = "### TC-1: Happy path\n- **Result**: PASS\n"
        results = tc_coverage.parse_tc_results(text)
        assert results == {1: "PASS"}

    def test_fail_result(self):
        text = "### TC-1: Title\n- **Result**: FAIL\n- **Notes**: broken\n"
        results = tc_coverage.parse_tc_results(text)
        assert results == {1: "FAIL"}

    def test_blocked_result(self):
        text = "### TC-1: Title\n- **Result**: BLOCKED\n"
        results = tc_coverage.parse_tc_results(text)
        assert results == {1: "BLOCKED"}

    def test_invalid_not_applicable(self):
        text = "### TC-1: Title\n- **Result**: Not Applicable\n"
        results = tc_coverage.parse_tc_results(text)
        assert results == {1: "INVALID"}

    def test_invalid_na(self):
        text = "### TC-1: Title\n- **Result**: N/A\n"
        results = tc_coverage.parse_tc_results(text)
        assert results == {1: "INVALID"}

    def test_invalid_deferred(self):
        text = "### TC-1: Title\n- **Result**: Deferred\n"
        results = tc_coverage.parse_tc_results(text)
        assert results == {1: "INVALID"}

    def test_table_row_result(self):
        text = "| TC-1 | PASS | notes |\n"
        results = tc_coverage.parse_tc_results(text)
        assert results == {1: "PASS"}

    def test_multiple_results(self):
        text = (
            "### TC-1: A\n- **Result**: PASS\n\n"
            "### TC-2: B\n- **Result**: FAIL\n\n"
            "### TC-3: C\n- **Result**: BLOCKED\n"
        )
        results = tc_coverage.parse_tc_results(text)
        assert results == {1: "PASS", 2: "FAIL", 3: "BLOCKED"}


# --- check_coverage ---


class TestCheckCoverage:
    """Full coverage check logic."""

    def _write_files(self, tmp_path, plan_text, results_text):
        plan = tmp_path / "TEST-PLAN.md"
        results = tmp_path / "QA-RESULTS.md"
        plan.write_text(plan_text, encoding="utf-8")
        results.write_text(results_text, encoding="utf-8")
        return str(plan), str(results)

    def test_full_coverage_all_pass(self, tmp_path):
        """TC-1: Full coverage, all PASS → exit 0."""
        plan = "### TC-1: A\n### TC-2: B\n### TC-3: C\n### TC-4: D\n### TC-5: E\n"
        results = (
            "### TC-1: A\n- **Result**: PASS\n\n"
            "### TC-2: B\n- **Result**: PASS\n\n"
            "### TC-3: C\n- **Result**: PASS\n\n"
            "### TC-4: D\n- **Result**: PASS\n\n"
            "### TC-5: E\n- **Result**: PASS\n"
        )
        p, r = self._write_files(tmp_path, plan, results)
        assert tc_coverage.check_coverage(p, r) == 0

    def test_full_coverage_mixed_results(self, tmp_path):
        """TC-2: Full coverage with FAIL → still exit 0 (coverage = presence)."""
        plan = "### TC-1: A\n### TC-2: B\n### TC-3: C\n"
        results = (
            "### TC-1: A\n- **Result**: PASS\n\n"
            "### TC-2: B\n- **Result**: FAIL\n\n"
            "### TC-3: C\n- **Result**: PASS\n"
        )
        p, r = self._write_files(tmp_path, plan, results)
        assert tc_coverage.check_coverage(p, r) == 0

    def test_missing_tcs(self, tmp_path):
        """TC-3: Missing TCs → exit 1."""
        plan = "### TC-1: A\n### TC-2: B\n### TC-3: C\n### TC-4: D\n### TC-5: E\n"
        results = (
            "### TC-1: A\n- **Result**: PASS\n\n"
            "### TC-3: C\n- **Result**: PASS\n\n"
            "### TC-5: E\n- **Result**: PASS\n"
        )
        p, r = self._write_files(tmp_path, plan, results)
        assert tc_coverage.check_coverage(p, r) == 1

    def test_invalid_not_applicable(self, tmp_path):
        """TC-4: 'not applicable' rejected → exit 1."""
        plan = "### TC-1: A\n### TC-2: B\n"
        results = (
            "### TC-1: A\n- **Result**: PASS\n\n"
            "### TC-2: B\n- **Result**: not applicable\n"
        )
        p, r = self._write_files(tmp_path, plan, results)
        assert tc_coverage.check_coverage(p, r) == 1

    def test_invalid_deferred(self, tmp_path):
        """TC-5: 'deferred' rejected → exit 1."""
        plan = "### TC-1: A\n### TC-2: B\n"
        results = (
            "### TC-1: A\n- **Result**: PASS\n\n"
            "### TC-2: B\n- **Result**: Deferred\n"
        )
        p, r = self._write_files(tmp_path, plan, results)
        assert tc_coverage.check_coverage(p, r) == 1

    def test_tolerant_zero_padded(self, tmp_path):
        """TC-6: Zero-padded format matched."""
        plan = "### TC-01: A\n### TC-02: B\n"
        results = (
            "### TC-01: A\n- **Result**: PASS\n\n"
            "### TC-02: B\n- **Result**: PASS\n"
        )
        p, r = self._write_files(tmp_path, plan, results)
        assert tc_coverage.check_coverage(p, r) == 0

    def test_tolerant_no_zero_pad(self, tmp_path):
        """TC-7: No-zero-pad format matched."""
        plan = "### TC-1: A\n### TC-2: B\n"
        results = (
            "### TC-1: A\n- **Result**: PASS\n\n"
            "### TC-2: B\n- **Result**: PASS\n"
        )
        p, r = self._write_files(tmp_path, plan, results)
        assert tc_coverage.check_coverage(p, r) == 0

    def test_tolerant_space_format(self, tmp_path):
        """TC-8: Space-separated format."""
        plan = "### TC 01: A\n"
        results = "### TC 01: A\n- **Result**: PASS\n"
        p, r = self._write_files(tmp_path, plan, results)
        assert tc_coverage.check_coverage(p, r) == 0

    def test_cross_format_matching(self, tmp_path):
        """TC-9: Plan uses TC-01, results use TC-1 — both normalize."""
        plan = "### TC-01: A\n"
        results = "### TC-1: A\n- **Result**: PASS\n"
        p, r = self._write_files(tmp_path, plan, results)
        assert tc_coverage.check_coverage(p, r) == 0

    def test_blocked_results_exit_2(self, tmp_path):
        """TC-15: BLOCKED counted as covered but exit 2."""
        plan = "### TC-1: A\n### TC-2: B\n### TC-3: C\n"
        results = (
            "### TC-1: A\n- **Result**: PASS\n\n"
            "### TC-2: B\n- **Result**: BLOCKED\n\n"
            "### TC-3: C\n- **Result**: PASS\n"
        )
        p, r = self._write_files(tmp_path, plan, results)
        assert tc_coverage.check_coverage(p, r) == 2

    def test_duplicate_tc_in_plan(self, tmp_path):
        """TC-20: Duplicate TC IDs in plan → exit 1."""
        plan = "### TC-1: First\n### TC-1: Duplicate\n"
        results = "### TC-1: First\n- **Result**: PASS\n"
        p, r = self._write_files(tmp_path, plan, results)
        assert tc_coverage.check_coverage(p, r) == 1

    def test_extra_tcs_in_results(self, tmp_path):
        """TC-21: Extra TCs in results → exit 1."""
        plan = "### TC-1: A\n### TC-2: B\n"
        results = (
            "### TC-1: A\n- **Result**: PASS\n\n"
            "### TC-2: B\n- **Result**: PASS\n\n"
            "### TC-3: C\n- **Result**: PASS\n"
        )
        p, r = self._write_files(tmp_path, plan, results)
        assert tc_coverage.check_coverage(p, r) == 1

    def test_empty_plan(self, tmp_path):
        """TC-22: Empty plan (no TCs) → exit 0."""
        plan = "# Test Plan\n\nSome prose.\n"
        results = "# QA Results\n"
        p, r = self._write_files(tmp_path, plan, results)
        assert tc_coverage.check_coverage(p, r) == 0

    def test_empty_results(self, tmp_path):
        """TC-23: Empty results with TCs in plan → exit 1."""
        plan = "### TC-1: A\n### TC-2: B\n### TC-3: C\n"
        results = "# QA Results\n\nNo entries yet.\n"
        p, r = self._write_files(tmp_path, plan, results)
        assert tc_coverage.check_coverage(p, r) == 1

    def test_prose_reference_not_counted(self, tmp_path):
        """TC-25: Prose mention of TC-2 should not count as a marker."""
        plan = "### TC-1: A\n### TC-2: B\n"
        results = (
            "### TC-1: A\n- **Result**: PASS\n\n"
            "See TC-2 for details in the related section.\n"
        )
        p, r = self._write_files(tmp_path, plan, results)
        assert tc_coverage.check_coverage(p, r) == 1

    def test_table_row_recognized(self, tmp_path):
        """TC-26: Table row format recognized."""
        plan = "### TC-1: A\n"
        results = "| TC-1 | PASS | notes |\n"
        p, r = self._write_files(tmp_path, plan, results)
        assert tc_coverage.check_coverage(p, r) == 0

    def test_debug_flag(self, tmp_path, capsys):
        """TC-24: --debug prints unmatched lines."""
        plan = "### TC-1: A\n"
        results = "### TC-1: A\n- **Result**: PASS\nSome random prose line.\n"
        p, r = self._write_files(tmp_path, plan, results)
        tc_coverage.check_coverage(p, r, debug=True)
        captured = capsys.readouterr()
        assert "random prose" in captured.err


# --- Auto-discovery ---


class TestAutoDiscovery:
    """File auto-discovery by issue number."""

    def _setup_planning(self, tmp_path, role, issue, files):
        """Create planning dir structure under tmp_path/.squidsquad/."""
        planning = tmp_path / ".squidsquad" / role / "planning"
        planning.mkdir(parents=True, exist_ok=True)
        for fname, content in files.items():
            (planning / fname).write_text(content, encoding="utf-8")
        return planning

    def test_discovers_pm_planning(self, tmp_path, monkeypatch):
        """TC-10: Auto-discovers files from PM planning dir."""
        self._setup_planning(tmp_path, "pm", 2361, {
            "FEAT-PM-2361-TEST-PLAN.md": "### TC-1: A\n",
            "FEAT-PM-2361-QA-RESULTS.md": "### TC-1: A\n- **Result**: PASS\n",
        })
        monkeypatch.setattr(tc_coverage, "SQUID_DIR", tmp_path / ".squidsquad")

        tp, qr = tc_coverage._discover_files(2361)
        assert tp is not None
        assert "PM-2361-TEST-PLAN" in tp.name
        assert qr is not None

    def test_pm_preferred_over_skill(self, tmp_path, monkeypatch):
        """TC-11: PM planning dir preferred over skill."""
        self._setup_planning(tmp_path, "pm", 2361, {
            "FEAT-PM-2361-TEST-PLAN.md": "### TC-1: PM\n",
        })
        self._setup_planning(tmp_path, "skill", 2361, {
            "FEAT-SKILL-2361-TEST-PLAN.md": "### TC-1: Skill\n",
        })
        monkeypatch.setattr(tc_coverage, "SQUID_DIR", tmp_path / ".squidsquad")

        tp, _ = tc_coverage._discover_files(2361)
        assert tp is not None
        assert "PM" in tp.name

    def test_highest_revision_picked(self, tmp_path, monkeypatch):
        """TC-12: Highest -RN revision selected."""
        self._setup_planning(tmp_path, "pm", 100, {
            "FEAT-PM-100-TEST-PLAN.md": "### TC-1: A\n",
            "FEAT-PM-100-QA-RESULTS.md": "### TC-1: A\n- **Result**: FAIL\n",
            "FEAT-PM-100-QA-RESULTS-R2.md": "### TC-1: A\n- **Result**: FAIL\n",
            "FEAT-PM-100-QA-RESULTS-R3.md": "### TC-1: A\n- **Result**: PASS\n",
        })
        monkeypatch.setattr(tc_coverage, "SQUID_DIR", tmp_path / ".squidsquad")

        _, qr = tc_coverage._discover_files(100)
        assert qr is not None
        assert "R3" in qr.name

    def test_base_file_when_no_revisions(self, tmp_path, monkeypatch):
        """TC-13: Base file used when no -RN exists."""
        self._setup_planning(tmp_path, "pm", 100, {
            "FEAT-PM-100-TEST-PLAN.md": "### TC-1: A\n",
            "FEAT-PM-100-QA-RESULTS.md": "### TC-1: A\n- **Result**: PASS\n",
        })
        monkeypatch.setattr(tc_coverage, "SQUID_DIR", tmp_path / ".squidsquad")

        _, qr = tc_coverage._discover_files(100)
        assert qr is not None
        assert "R" not in qr.name.split("RESULTS")[1]

    def test_no_test_plan_returns_none(self, tmp_path, monkeypatch):
        """TC-14: No test plan → None."""
        monkeypatch.setattr(tc_coverage, "SQUID_DIR", tmp_path / ".squidsquad")
        (tmp_path / ".squidsquad" / "pm" / "planning").mkdir(parents=True)

        tp, qr = tc_coverage._discover_files(9999)
        assert tp is None
