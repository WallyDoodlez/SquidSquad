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

    def test_heading_title_with_invalid_word_not_matched(self):
        """Heading title containing 'not-applicable' must not trigger INVALID (#2469)."""
        text = "### TC-4: Rejects not-applicable as invalid\n- **Result**: PASS\n"
        results = tc_coverage.parse_tc_results(text)
        assert results == {4: "PASS"}

    def test_heading_title_with_deferred_not_matched(self):
        """Heading title containing 'deferred' must not trigger INVALID (#2469)."""
        text = "### TC-5: Deferred results are rejected\n- **Result**: PASS\n"
        results = tc_coverage.parse_tc_results(text)
        assert results == {5: "PASS"}


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

    def test_heading_title_with_invalid_words_not_false_positive(self, tmp_path):
        """Heading titles mentioning invalid tokens must not cause false INVALID (#2469)."""
        plan = "### TC-1: A\n### TC-4: Rejects not-applicable as invalid\n### TC-5: Deferred rejected\n"
        results = (
            "### TC-1: A\n- **Result**: PASS\n\n"
            "### TC-4: Rejects not-applicable as invalid\n- **Result**: PASS\n\n"
            "### TC-5: Deferred rejected\n- **Result**: PASS\n"
        )
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


class TestAutoDiscoveryCurrentConvention13737:
    """#13737: the #9184 convention is TEST-PLAN-<N>.md / QA-RESULTS-<N>.md
    (number last, no dashes sandwiching it, no role prefix) under the
    verifier ('qa') planning dir -- _discover_files() previously only
    recognized the pre-#9184 *-<N>-TEST-PLAN.md shape and silently found
    nothing for every real post-#9184 issue, making the 'never bypassed' TC
    coverage ship gate a permanent no-op."""

    def _setup_planning(self, tmp_path, role, files):
        planning = tmp_path / ".squidsquad" / role / "planning"
        planning.mkdir(parents=True, exist_ok=True)
        for fname, content in files.items():
            (planning / fname).write_text(content, encoding="utf-8")
        return planning

    def test_discovers_current_convention_pair(self, tmp_path, monkeypatch):
        """A real TEST-PLAN-<N>.md/QA-RESULTS-<N>.md pair is found."""
        self._setup_planning(tmp_path, "qa", {
            "TEST-PLAN-13735.md": "| TC | Maps to |\n| TC1 | AC1 |\n",
            "QA-RESULTS-13735.md": "### TC-1\n- **Result**: PASS\n",
        })
        monkeypatch.setattr(tc_coverage, "SQUID_DIR", tmp_path / ".squidsquad")

        tp, qr = tc_coverage._discover_files(13735)
        assert tp is not None and tp.name == "TEST-PLAN-13735.md"
        assert qr is not None and qr.name == "QA-RESULTS-13735.md"

    def test_qa_preferred_over_pm_for_current_convention(self, tmp_path, monkeypatch):
        """qa (verifier) planning dir wins -- #9184 moved TEST-PLAN/QA-RESULTS
        ownership from PM to verifier, unlike the pre-#9184 PM-first order."""
        self._setup_planning(tmp_path, "pm", {
            "TEST-PLAN-500.md": "### TC-1: PM copy\n",
        })
        self._setup_planning(tmp_path, "qa", {
            "TEST-PLAN-500.md": "### TC-1: QA copy\n",
        })
        monkeypatch.setattr(tc_coverage, "SQUID_DIR", tmp_path / ".squidsquad")

        tp, _ = tc_coverage._discover_files(500)
        assert tp is not None
        assert tp.parent.parent.name == "qa"

    def test_current_convention_does_not_require_rn_file(self, tmp_path, monkeypatch):
        """Round revisions live as sections inside the single QA-RESULTS-<N>.md
        under #9184 -- no separate -RN.md file needed or expected."""
        self._setup_planning(tmp_path, "qa", {
            "TEST-PLAN-777.md": "### TC-1: A\n",
            "QA-RESULTS-777.md": (
                "## Round 1\n### TC-1\n- **Result**: FAIL\n\n"
                "## Round 2\n### TC-1\n- **Result**: PASS\n"
            ),
        })
        monkeypatch.setattr(tc_coverage, "SQUID_DIR", tmp_path / ".squidsquad")

        tp, qr = tc_coverage._discover_files(777)
        assert tp is not None
        assert qr is not None and qr.name == "QA-RESULTS-777.md"

    def test_legacy_convention_still_falls_back(self, tmp_path, monkeypatch):
        """Pre-#9184 in-flight issues (legacy *-<N>-TEST-PLAN.md shape) must
        still resolve -- verification.md documents this as a kept fallback,
        not a removed path."""
        self._setup_planning(tmp_path, "pm", {
            "FEAT-PM-42-TEST-PLAN.md": "### TC-1: A\n",
            "FEAT-PM-42-QA-RESULTS.md": "### TC-1: A\n- **Result**: PASS\n",
        })
        monkeypatch.setattr(tc_coverage, "SQUID_DIR", tmp_path / ".squidsquad")

        tp, qr = tc_coverage._discover_files(42)
        assert tp is not None and "FEAT-PM-42-TEST-PLAN" in tp.name
        assert qr is not None and "FEAT-PM-42-QA-RESULTS" in qr.name

    def test_current_convention_preferred_over_legacy_in_same_dir(self, tmp_path, monkeypatch):
        """If both shapes somehow exist for the same issue, the current
        convention wins (it's checked first)."""
        self._setup_planning(tmp_path, "qa", {
            "TEST-PLAN-88.md": "### TC-1: current\n",
            "FEAT-PM-88-TEST-PLAN.md": "### TC-1: legacy\n",
        })
        monkeypatch.setattr(tc_coverage, "SQUID_DIR", tmp_path / ".squidsquad")

        tp, _ = tc_coverage._discover_files(88)
        assert tp is not None and tp.name == "TEST-PLAN-88.md"


class TestCheckCoverageFileErrors:
    """#7622: check_coverage must handle unreadable files gracefully."""

    def test_missing_test_plan_returns_1(self, tmp_path):
        """Missing test plan file returns exit code 1, not unhandled exception."""
        result = tc_coverage.check_coverage(
            str(tmp_path / "nonexistent-plan.md"),
            str(tmp_path / "nonexistent-results.md"),
        )
        assert result == 1

    def test_missing_qa_results_returns_1(self, tmp_path):
        """Missing QA results file returns exit code 1."""
        plan = tmp_path / "plan.md"
        plan.write_text("### TC-1: Test\n- **Result**: PASS\n")
        result = tc_coverage.check_coverage(
            str(plan),
            str(tmp_path / "nonexistent-results.md"),
        )
        assert result == 1


# --- #13944: merged-cell table rows + bold-bullet plan declarations ---


class TestMergedCellTableRows13944:
    """The QA-RESULTS convention verifier sessions actually write puts TC-N
    plus a free-text description in ONE cell (`| TC1 -- repro | PASS |`).
    The old regex required the cell to BE exactly TC-N, so every conforming
    QA-RESULTS parsed as 0 TCs and the ship-integrity gate skipped (#13944)."""

    def test_merged_cell_id_and_result(self):
        text = "| TC1 — core repro under real flipped state | PASS | evidence |\n"
        assert tc_coverage.parse_tc_ids(text) == [1]
        assert tc_coverage.parse_tc_results(text) == {1: "PASS"}

    def test_merged_cell_description_words_do_not_pollute_result(self):
        """Description prose containing invalid-result vocabulary must not
        register: only cells AFTER the TC cell are searched (the table-row
        analog of the #2469 heading fix)."""
        text = "| TC2 — deferred cleanup and N/A handling | PASS | e |\n"
        assert tc_coverage.parse_tc_results(text) == {2: "PASS"}

    def test_isolated_cell_backcompat(self):
        text = "| TC-3 | FAIL | notes |\n"
        assert tc_coverage.parse_tc_results(text) == {3: "FAIL"}

    def test_malformed_row_without_closing_pipe_is_unknown(self):
        """A TC cell that never closes has no result cell -- UNKNOWN, never a
        result guessed out of description prose."""
        text = "| TC4 — description only, row never closes PASS\n"
        assert tc_coverage.parse_tc_results(text) == {4: "UNKNOWN"}

    def test_partial_number_not_matched(self):
        """TC123abc must not parse as TC-123 (word boundary)."""
        text = "| TC123abc | PASS |\n"
        assert tc_coverage.parse_tc_ids(text) == []

    def test_real_qa_results_shape_end_to_end(self, tmp_path):
        """Round-trip the real #13863-era artifact shapes: bold-bullet
        TEST-PLAN declarations + merged-cell QA-RESULTS table -> full
        coverage, gate pass (was: 'No TCs found, gate skipped 0/0')."""
        plan = tmp_path / "TEST-PLAN-9999.md"
        plan.write_text(
            "## TCs\n\n"
            "- **TC1 — core repro**: does the fix hold?\n"
            "- **TC2 — gate fails loudly**: does boot block?\n",
            encoding="utf-8",
        )
        results = tmp_path / "QA-RESULTS-9999.md"
        results.write_text(
            "## TC Results\n\n"
            "| TC | Result | Evidence |\n"
            "|---|---|---|\n"
            "| TC1 — core repro | PASS | live push succeeded |\n"
            "| TC2 — gate fails loudly | PASS | marker-keyed block |\n",
            encoding="utf-8",
        )
        assert tc_coverage.check_coverage(str(plan), str(results)) == 0


class TestBulletDeclarations13944:
    """Real TEST-PLANs declare TCs as bold bullets (`- **TC1 -- x**: ...`);
    with only heading/table patterns the plan side parsed 0 TCs."""

    def test_bold_bullet_ids(self):
        text = "- **TC1 — override proof**: works?\n- **TC-2 — resolves**: yes?\n* **TC 3 — star bullet**: also\n"
        assert tc_coverage.parse_tc_ids(text) == [1, 2, 3]

    def test_plain_bullet_prose_not_matched(self):
        """Un-bolded prose mentions are references, not declarations."""
        text = "- TC3 is covered by the integration run\n- see **the TC4 notes** above\n"
        assert tc_coverage.parse_tc_ids(text) == []


# --- #13990: result-cell-only scan for table rows ---


class TestResultCellOnly13990:
    """#13944's first cut scanned the whole row remainder, so Evidence-column
    prose mentioning deferred/N-A misclassified a genuine PASS as INVALID
    (live-hit shipping QA-RESULTS-13944 itself). A result is only ever
    declared in the Result cell; Evidence is prose."""

    def test_evidence_prose_with_invalid_words_does_not_block(self):
        """The live repro shape: PASS in the Result cell, deferred/N-A
        wording inside the Evidence cell."""
        text = ('| TC5 — description-pollution guard | PASS | a TC cell '
                'description containing the literal words "deferred" and "N/A" |\n')
        assert tc_coverage.parse_tc_results(text) == {5: "PASS"}

    def test_isolated_cell_notes_column_no_longer_scanned(self):
        """Pre-#13944 latent form of the same bug: isolated TC cell, notes
        column mentioning an invalid token."""
        text = "| TC-1 | PASS | scenario covers the deferred cleanup path |\n"
        assert tc_coverage.parse_tc_results(text) == {1: "PASS"}

    def test_invalid_token_in_result_cell_still_blocks(self):
        """The invalid check still fires where it should: in the Result
        cell itself."""
        text = "| TC2 — edge case | deferred | will do later |\n"
        assert tc_coverage.parse_tc_results(text) == {2: "INVALID"}

    def test_empty_result_cell_is_unknown_not_scavenged(self):
        """An empty Result cell must not scavenge a result from Evidence
        or from subsequent lines."""
        text = "| TC3 — desc | | evidence says PASS somewhere |\nPASS on the next line\n"
        assert tc_coverage.parse_tc_results(text) == {3: "UNKNOWN"}

    def test_result_cell_with_qualifier_prose_still_parses(self):
        """Real-artifact shape: 'PASS (by code inspection + TC1)' in the
        Result cell."""
        text = "| TC2 — credential-manager-independent | PASS (by code inspection + TC1) | evidence |\n"
        assert tc_coverage.parse_tc_results(text) == {2: "PASS"}
