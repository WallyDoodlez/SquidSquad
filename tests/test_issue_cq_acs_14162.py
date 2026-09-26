"""#14162 -- instruction-changing issues arrive with ACs and a CQ requirement.

Issues skip PM intake, and the filing shapes asked for no acceptance criteria.
So an issue whose fix changes LLM-consumed instructions reached pickup with no
CQ requirement (#14114, #14147 and #14137 were all backfilled by hand).

- Every issue shape in tracker-protocol now ends with `## Acceptance
  criteria`, with a CQ line when the fix touches instructions.
- `tracker.py create-issue` backstops it: a body naming an instruction file
  with no CQ mention gets a CQ criterion appended.
- The worker pickup guard asks PM for ACs, without blocking, on legacy issues.

Safety: the forge adapter and label lookup are mocked, so no real issue is
ever created.
"""

import sys
from pathlib import Path
from unittest import mock

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "references" / "scripts"))

import tracker  # noqa: E402

SUB = REPO / "references" / "sub-skills"


class TestEnsureCqAcceptanceCriteria:
    def test_instruction_issue_without_cq_gets_section(self):
        body = ("**Observation**: step is wrong\n"
                "**Location**: references/sub-skills/common/foo.md:12\n"
                "**Suggested fix**: reword")
        out, added = tracker._ensure_cq_acceptance_criteria(body)
        assert added
        assert out.startswith(body)
        assert "\n## Acceptance criteria\n- **CQ** (auto-added, #14162)" in out
        assert "tests/comprehension/<this issue>_spec.json" in out

    def test_existing_ac_section_gets_cq_line_not_second_section(self):
        body = ("**Location**: references/roles/pm/instructions.md\n\n"
                "## Acceptance criteria\n- the step fires")
        out, added = tracker._ensure_cq_acceptance_criteria(body)
        assert added
        assert out.count("## Acceptance criteria") == 1
        assert out.endswith(tracker._CQ_AC_LINE)

    def test_ac_section_not_last_gets_new_section(self):
        body = ("references/sub-skills/x.md\n\n## Acceptance criteria\n- a\n\n"
                "## Notes\n- b")
        out, added = tracker._ensure_cq_acceptance_criteria(body)
        assert added and out.count("## Acceptance criteria") == 2

    @pytest.mark.parametrize("body", [
        "**Location**: references/scripts/harness.py:10 -- pure code bug",
        "Fix in references/sub-skills/a.md; CQ: tests/comprehension/1_spec.json",
        "references/roles/x.md -- verifier authors a comprehension spec",
        "",
    ])
    def test_no_change_when_code_only_or_cq_present(self, body):
        out, added = tracker._ensure_cq_acceptance_criteria(body)
        assert not added and out == body

    @pytest.mark.parametrize("surface", [
        "references/roles/pm/instructions.md",
        "references\\sub-skills\\common\\x.md",
        ".squidsquad/project/worker.md",
        "the composed CLAUDE.md",
        "SOUL.md drift",
    ])
    def test_surfaces_detected(self, surface):
        _, added = tracker._ensure_cq_acceptance_criteria(f"see {surface}")
        assert added


class TestCreateIssueWiring:
    def test_create_issue_appends_cq_block_before_filing(self, capsys):
        adapter = mock.Mock()
        adapter.create_issue.return_value = {"number": 999}
        with mock.patch("tracker._get_forge_adapter", return_value=adapter), \
             mock.patch("tracker._filter_role_labels_to_existing",
                        side_effect=lambda labels, role: labels):
            n = tracker.create_issue(
                "step wrong", "**Location**: references/sub-skills/a.md",
                "skill", "low", reporter="pm-lead")
        assert n == 999
        body = adapter.create_issue.call_args.args[1]
        assert body.startswith("**Reported By**: pm-lead")
        assert "## Acceptance criteria\n- **CQ** (auto-added, #14162)" in body
        assert "appended a CQ acceptance-criteria block" in capsys.readouterr().err

    def test_code_only_issue_body_unchanged(self):
        adapter = mock.Mock()
        adapter.create_issue.return_value = {"number": 1000}
        with mock.patch("tracker._get_forge_adapter", return_value=adapter), \
             mock.patch("tracker._filter_role_labels_to_existing",
                        side_effect=lambda labels, role: labels):
            tracker.create_issue("crash", "harness.py raises", "skill", "low")
        assert adapter.create_issue.call_args.args[1] == "harness.py raises"


class TestFilingShapesAndPickupGuard:
    TP = SUB / "common" / "tracker-protocol.md"

    @pytest.mark.parametrize("shape", ["**Bug fix**", "**Improvement-scan finding**",
                                       "**Cross-role issue**"])
    def test_every_issue_shape_has_acceptance_criteria(self, shape):
        text = self.TP.read_text(encoding="utf-8")
        block = text[text.index(shape):]
        block = block[:block.index("```", block.index("```bash") + 7)]
        assert "## Acceptance criteria" in block

    def test_cq_rule_and_code_only_case(self):
        text = self.TP.read_text(encoding="utf-8")
        rule = text[text.index("**Every issue carries `## Acceptance criteria`"):]
        rule = rule[:rule.index("**Cross-role issue**")]
        assert "tests/comprehension/<this issue>_spec.json" in rule
        assert "A pure code fix gets ACs without the CQ line." in rule

    @pytest.mark.parametrize("path", ["common/improvement-scan.md",
                                      "common/improvement-scan-slim.md",
                                      "roles/pm/improvement-scan.md"])
    def test_scan_filing_steps_name_the_ac_section(self, path):
        text = (SUB / path).read_text(encoding="utf-8")
        assert "`## Acceptance criteria`, with a CQ line when the fix changes agent instructions" in text

    def test_pm_issue_filing_requires_acs(self):
        text = (SUB / "roles" / "pm" / "issue-filing.md").read_text(encoding="utf-8")
        assert "acceptance criteria" in text and "CQ line" in text

    def test_worker_pickup_guard_is_non_blocking(self):
        text = (SUB / "roles" / "worker" / "triage-issues.md").read_text(encoding="utf-8")
        guard = text[text.index("**AC guard (#14162)**"):]
        guard = guard[:guard.index("\n4b.")]
        assert "PM: this fix changes agent instructions" in guard
        assert "Do not wait for PM." in guard
