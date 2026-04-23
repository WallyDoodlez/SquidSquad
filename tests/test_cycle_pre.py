"""Tests for references/scripts/cycle_pre.py — pre-cycle mechanical operations."""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import cycle_pre


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def squid_dir(tmp_path):
    """Create a minimal .squidsquad directory structure."""
    squid = tmp_path / ".squidsquad"
    for role in ("skill", "pm", "qa", "dm"):
        (squid / role).mkdir(parents=True)
        (squid / role / "iterations").mkdir()
    return squid


@pytest.fixture
def patch_dirs(squid_dir, tmp_path, monkeypatch):
    """Patch REPO_ROOT and SQUID_DIR to use tmp_path."""
    monkeypatch.setattr(cycle_pre, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(cycle_pre, "SQUID_DIR", squid_dir)
    return tmp_path


# ---------------------------------------------------------------------------
# Working State Parsing
# ---------------------------------------------------------------------------

class TestReadWorkingState:
    def test_empty_file(self, patch_dirs, squid_dir):
        ws = squid_dir / "skill" / "working-state.md"
        ws.write_text("", encoding="utf-8")
        result = cycle_pre._read_working_state("skill")
        assert result["task"] == "none"
        assert result["status"] == "none"
        assert result["suppressed"] is False

    def test_active_task(self, patch_dirs, squid_dir):
        ws = squid_dir / "skill" / "working-state.md"
        ws.write_text(
            "# Working State\n\n"
            "- **Task**: #2050\n"
            "- **Status**: in-progress\n"
            "- **Quiet Cycles**: 0\n\n"
            "## Completed Steps\n"
            "- Read issue details\n"
            "- Located bug in parser.py\n\n"
            "## Remaining Steps\n"
            "- Write fix\n"
            "- Run tests\n\n"
            "## Key Decisions\n"
            "- Use regex instead of string split\n",
            encoding="utf-8",
        )
        result = cycle_pre._read_working_state("skill")
        assert result["task"] == "#2050"
        assert result["status"] == "in-progress"
        assert result["completed_steps"] == ["Read issue details", "Located bug in parser.py"]
        assert result["remaining_steps"] == ["Write fix", "Run tests"]
        assert result["key_decisions"] == ["Use regex instead of string split"]
        assert result["quiet_cycles"] == 0

    def test_no_task(self, patch_dirs, squid_dir):
        ws = squid_dir / "skill" / "working-state.md"
        ws.write_text(
            "# Working State\n\n"
            "- **Task**: none\n"
            "- **Status**: none\n"
            "- **Quiet Cycles**: 3\n",
            encoding="utf-8",
        )
        result = cycle_pre._read_working_state("skill")
        assert result["task"] == "none"
        assert result["status"] == "none"
        assert result["quiet_cycles"] == 3

    def test_missing_file(self, patch_dirs, squid_dir):
        result = cycle_pre._read_working_state("skill")
        assert result["task"] == "none"
        assert result["raw_content"] == ""

    def test_pm_planning_phase_suppression(self, patch_dirs, squid_dir):
        ws = squid_dir / "pm" / "working-state.md"
        ws.write_text(
            "# Working State\n\n"
            "- **Task**: #2070\n"
            "- **Status**: in-progress\n"
            "- **Phase**: researching #2070\n",
            encoding="utf-8",
        )
        result = cycle_pre._read_working_state("pm")
        assert result["suppressed"] is True
        assert result["phase"] == "researching #2070"


# ---------------------------------------------------------------------------
# Cycle Number
# ---------------------------------------------------------------------------

class TestGetCycleNumber:
    def test_no_iterations(self, patch_dirs, squid_dir):
        assert cycle_pre._get_cycle_number("skill") == 1

    def test_increments_from_last(self, patch_dirs, squid_dir):
        iter_dir = squid_dir / "skill" / "iterations"
        (iter_dir / "iter-204.md").write_text("# Iteration 204", encoding="utf-8")
        (iter_dir / "iter-205.md").write_text("# Iteration 205", encoding="utf-8")
        assert cycle_pre._get_cycle_number("skill") == 206

    def test_handles_gaps(self, patch_dirs, squid_dir):
        iter_dir = squid_dir / "skill" / "iterations"
        (iter_dir / "iter-100.md").write_text("", encoding="utf-8")
        (iter_dir / "iter-150.md").write_text("", encoding="utf-8")
        assert cycle_pre._get_cycle_number("skill") == 151


# ---------------------------------------------------------------------------
# Context Pressure
# ---------------------------------------------------------------------------

class TestContextPressure:
    def test_reads_pressure_file(self, patch_dirs, squid_dir):
        (squid_dir / "skill" / "context-pressure").write_text("42", encoding="utf-8")
        with patch.object(cycle_pre, "_config_get", return_value="70"):
            result = cycle_pre._read_context_pressure("skill")
        assert result["used_pct"] == 42
        assert result["threshold"] == 70
        assert result["exceeded"] is False

    def test_exceeded_threshold(self, patch_dirs, squid_dir):
        (squid_dir / "skill" / "context-pressure").write_text("85", encoding="utf-8")
        with patch.object(cycle_pre, "_config_get", return_value="70"):
            result = cycle_pre._read_context_pressure("skill")
        assert result["exceeded"] is True

    def test_missing_pressure_file(self, patch_dirs, squid_dir):
        with patch.object(cycle_pre, "_config_get", return_value="70"):
            result = cycle_pre._read_context_pressure("skill")
        assert result["used_pct"] == 0
        assert result["exceeded"] is False

    def test_default_threshold_on_missing_config(self, patch_dirs, squid_dir):
        with patch.object(cycle_pre, "_config_get", return_value=""):
            result = cycle_pre._read_context_pressure("skill")
        assert result["threshold"] == 70


# ---------------------------------------------------------------------------
# Pull
# ---------------------------------------------------------------------------

class TestDoPull:
    def test_ok(self, monkeypatch):
        fake = MagicMock()
        fake.returncode = 0
        fake.stdout = "Pulled"
        monkeypatch.setattr(cycle_pre, "_run_script", lambda *a, **kw: fake)
        assert cycle_pre._do_pull() == "ok"

    def test_error(self, monkeypatch):
        fake = MagicMock()
        fake.returncode = 1
        fake.stdout = "error"
        monkeypatch.setattr(cycle_pre, "_run_script", lambda *a, **kw: fake)
        assert cycle_pre._do_pull() == "error"

    def test_stash_conflict(self, monkeypatch):
        fake = MagicMock()
        fake.returncode = 0
        fake.stdout = "Pulled (stash pop conflict — run 'git stash show')"
        monkeypatch.setattr(cycle_pre, "_run_script", lambda *a, **kw: fake)
        assert cycle_pre._do_pull() == "stash_conflict"


# ---------------------------------------------------------------------------
# Config Flags
# ---------------------------------------------------------------------------

class TestReadConfigFlags:
    def test_reads_all_flags(self, monkeypatch):
        flags = {
            "branch-workflow": "yes",
            "pr-flow": "no",
            "improvement-scanning": "yes",
            "vault-remember": "no",
            "vault-optimize": "yes",
        }
        monkeypatch.setattr(cycle_pre, "_config_get", lambda f: flags.get(f, ""))
        result = cycle_pre._read_config_flags()
        assert result["branch_workflow"] is True
        assert result["pr_flow"] is False
        assert result["improvement_scanning"] is True
        assert result["vault_remember"] is False
        assert result["vault_optimize"] is True


# ---------------------------------------------------------------------------
# Skill Input Builder
# ---------------------------------------------------------------------------

class TestBuildSkillInput:
    def test_builds_with_empty_queue(self, patch_dirs, monkeypatch):
        empty = MagicMock()
        empty.returncode = 0
        empty.stdout = "[]"
        monkeypatch.setattr(cycle_pre, "_run_script", lambda *a, **kw: empty)
        monkeypatch.setattr(cycle_pre, "_config_get", lambda f: {
            "interval": "30", "test-command": "python tests/run_tests.py",
            "branch-workflow": "no", "pr-flow": "no",
            "improvement-scanning": "yes", "vault-remember": "yes",
            "vault-optimize": "no",
        }.get(f, ""))

        result = cycle_pre._build_skill_input("skill")
        assert result["work_queue"]["qa_rejected"] == []
        assert result["work_queue"]["queue"] == []
        assert result["planning_artifacts"] == {}
        assert result["interval_minutes"] == 30
        assert result["config"]["test_command"] == "python tests/run_tests.py"

    def test_builds_with_queue_items(self, patch_dirs, squid_dir, monkeypatch):
        queue_data = [
            {"number": 2045, "type": "issue", "priority": "high", "title": "Bug"},
        ]

        def fake_run_script(*args, **kwargs):
            fake = MagicMock()
            fake.returncode = 0
            if "triage.py" in args[0]:
                fake.stdout = "[]"
            elif "tracker.py" in args[0] and "work-queue" in args:
                fake.stdout = json.dumps(queue_data)
            else:
                fake.stdout = "[]"
            return fake

        monkeypatch.setattr(cycle_pre, "_run_script", fake_run_script)
        monkeypatch.setattr(cycle_pre, "_config_get", lambda f: {
            "interval": "30", "test-command": "",
            "branch-workflow": "no", "pr-flow": "no",
            "improvement-scanning": "no", "vault-remember": "no",
            "vault-optimize": "no",
        }.get(f, ""))

        result = cycle_pre._build_skill_input("skill")
        assert len(result["work_queue"]["queue"]) == 1
        assert result["work_queue"]["queue"][0]["number"] == 2045


# ---------------------------------------------------------------------------
# QA Input Builder — e2e guard regression (#2070 QA feedback)
# ---------------------------------------------------------------------------

class TestBuildQaInputE2eGuard:
    def test_none_placeholder_skips_e2e(self, patch_dirs, monkeypatch):
        """Config value '(none)' for e2e-tests must not be treated as a command."""
        empty = MagicMock()
        empty.returncode = 0
        empty.stdout = "[]"
        monkeypatch.setattr(cycle_pre, "_run_script", lambda *a, **kw: empty)
        monkeypatch.setattr(cycle_pre, "_run", lambda *a, **kw: MagicMock(
            returncode=0, stdout="[]", stderr=""))
        monkeypatch.setattr(cycle_pre, "_config_get", lambda f: {
            "e2e-tests": "(none)",
            "interval": "30",
            "branch-workflow": "no", "pr-flow": "no",
            "improvement-scanning": "no", "vault-remember": "no",
            "vault-optimize": "no",
        }.get(f, ""))

        result = cycle_pre._build_qa_input("qa")
        assert result["e2e_test_result"]["result"] == "skipped"

    def test_empty_e2e_skips(self, patch_dirs, monkeypatch):
        """Empty e2e-tests config must skip."""
        empty = MagicMock()
        empty.returncode = 0
        empty.stdout = "[]"
        monkeypatch.setattr(cycle_pre, "_run_script", lambda *a, **kw: empty)
        monkeypatch.setattr(cycle_pre, "_run", lambda *a, **kw: MagicMock(
            returncode=0, stdout="[]", stderr=""))
        monkeypatch.setattr(cycle_pre, "_config_get", lambda f: {
            "e2e-tests": "",
            "interval": "30",
            "branch-workflow": "no", "pr-flow": "no",
            "improvement-scanning": "no", "vault-remember": "no",
            "vault-optimize": "no",
        }.get(f, ""))

        result = cycle_pre._build_qa_input("qa")
        assert result["e2e_test_result"]["result"] == "skipped"


# ---------------------------------------------------------------------------
# Comment enrichment (#2272)
# ---------------------------------------------------------------------------

class TestEnrichWithComments:
    def test_adds_latest_comment(self, monkeypatch):
        """_enrich_with_comments adds latest_comment to items."""
        comment = {"author": "pm-lead", "body": "Blocker!", "createdAt": "2026-04-23"}
        monkeypatch.setattr(cycle_pre, "_fetch_latest_comment", lambda n: comment)
        items = [{"number": 42, "title": "Test"}]
        cycle_pre._enrich_with_comments(items)
        assert items[0]["latest_comment"] == comment

    def test_handles_no_comment(self, monkeypatch):
        """Items without comments don't get latest_comment key."""
        monkeypatch.setattr(cycle_pre, "_fetch_latest_comment", lambda n: None)
        items = [{"number": 42, "title": "Test"}]
        cycle_pre._enrich_with_comments(items)
        assert "latest_comment" not in items[0]

    def test_handles_empty_list(self, monkeypatch):
        """Empty list doesn't crash."""
        monkeypatch.setattr(cycle_pre, "_fetch_latest_comment", lambda n: None)
        items = []
        cycle_pre._enrich_with_comments(items)
        assert items == []
