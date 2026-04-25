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


# ---------------------------------------------------------------------------
# PM Input Builder — approved, human-blocked, recently-commented (#2494)
# ---------------------------------------------------------------------------

class TestBuildPmInputNewFields:
    """Tests for #2494: approved_items, human_blocked, recently_commented."""

    def _make_mocks(self, monkeypatch, tracker_responses=None, gh_responses=None):
        """Set up mocks for _run_script and _run with configurable responses."""
        tracker_responses = tracker_responses or {}
        gh_responses = gh_responses or {}

        def fake_run_script(*args, **kwargs):
            fake = MagicMock()
            fake.returncode = 0
            fake.stdout = "[]"
            # Match tracker.py subcommands
            if len(args) >= 2 and "tracker.py" in str(args[0]):
                subcmd = args[1] if len(args) > 1 else ""
                # For list-by-labels, match on the label string
                if subcmd == "list-by-labels" and len(args) > 2:
                    label_str = args[2]
                    fake.stdout = json.dumps(
                        tracker_responses.get(f"list-by-labels:{label_str}", [])
                    )
                elif subcmd in tracker_responses:
                    fake.stdout = json.dumps(tracker_responses[subcmd])
            elif len(args) >= 1 and "health_check.py" in str(args[0]):
                fake.stdout = json.dumps(tracker_responses.get("health", []))
            return fake

        def fake_run(cmd, **kwargs):
            fake = MagicMock()
            fake.returncode = 0
            fake.stdout = "[]"
            fake.stderr = ""
            cmd_str = " ".join(str(c) for c in cmd)
            for key, val in gh_responses.items():
                if key in cmd_str:
                    fake.stdout = json.dumps(val)
                    break
            return fake

        monkeypatch.setattr(cycle_pre, "_run_script", fake_run_script)
        monkeypatch.setattr(cycle_pre, "_run", fake_run)
        monkeypatch.setattr(cycle_pre, "_config_get", lambda f: {
            "branch-workflow": "no", "pr-flow": "no",
            "improvement-scanning": "no", "vault-remember": "no",
            "vault-optimize": "no", "ship-threshold": "10",
            "shipped-since-bump": "0",
            "interval": "30",
        }.get(f, ""))
        monkeypatch.setattr(cycle_pre, "_fetch_latest_comment", lambda n: None)

    def test_approved_items_present(self, patch_dirs, squid_dir, monkeypatch):
        """PM input includes approved_items field."""
        approved = [{"number": 100, "title": "Approved task", "labels": []}]
        self._make_mocks(monkeypatch, tracker_responses={
            "list-by-labels:squidsquad,status:approved": approved,
        })
        result = cycle_pre._build_pm_input("pm")
        assert "approved_items" in result
        assert len(result["approved_items"]) == 1
        assert result["approved_items"][0]["number"] == 100

    def test_approved_items_empty(self, patch_dirs, squid_dir, monkeypatch):
        """approved_items is empty list when no approved items exist."""
        self._make_mocks(monkeypatch)
        result = cycle_pre._build_pm_input("pm")
        assert result["approved_items"] == []

    def test_human_blocked_items(self, patch_dirs, squid_dir, monkeypatch):
        """PM input includes human_blocked field with items from all three labels."""
        blocked = [{"number": 200, "title": "Needs human setup", "labels": []}]
        review = [{"number": 201, "title": "Needs human review", "labels": []}]
        self._make_mocks(monkeypatch, tracker_responses={
            "list-by-labels:squidsquad,blocked:human-action": blocked,
            "list-by-labels:squidsquad,status:pending-human-setup": [],
            "list-by-labels:squidsquad,status:pending-human-review": review,
        })
        result = cycle_pre._build_pm_input("pm")
        assert "human_blocked" in result
        assert len(result["human_blocked"]) == 2
        numbers = {i["number"] for i in result["human_blocked"]}
        assert numbers == {200, 201}

    def test_human_blocked_deduplicates(self, patch_dirs, squid_dir, monkeypatch):
        """Items appearing in multiple blocked queries are not duplicated."""
        same_item = [{"number": 300, "title": "Same item", "labels": []}]
        self._make_mocks(monkeypatch, tracker_responses={
            "list-by-labels:squidsquad,blocked:human-action": same_item,
            "list-by-labels:squidsquad,status:pending-human-setup": same_item,
            "list-by-labels:squidsquad,status:pending-human-review": [],
        })
        result = cycle_pre._build_pm_input("pm")
        assert len(result["human_blocked"]) == 1

    def test_recently_commented_present(self, patch_dirs, squid_dir, monkeypatch):
        """PM input includes recently_commented field."""
        from datetime import datetime, timezone
        now_iso = datetime.now(timezone.utc).isoformat()
        items = [{"number": 400, "title": "Recent", "labels": [], "updatedAt": now_iso}]
        self._make_mocks(monkeypatch, gh_responses={
            "issue list": items,
        })
        result = cycle_pre._build_pm_input("pm")
        assert "recently_commented" in result

    def test_recently_commented_filters_old(self, patch_dirs, squid_dir, monkeypatch):
        """Items updated more than 2x interval ago are excluded."""
        items = [{"number": 500, "title": "Old", "labels": [], "updatedAt": "2020-01-01T00:00:00Z"}]
        self._make_mocks(monkeypatch, gh_responses={
            "issue list": items,
        })
        result = cycle_pre._build_pm_input("pm")
        assert len(result["recently_commented"]) == 0

    def test_all_new_fields_enriched_with_comments(self, patch_dirs, squid_dir, monkeypatch):
        """All three new fields are enriched with latest comments."""
        from datetime import datetime, timezone
        now_iso = datetime.now(timezone.utc).isoformat()
        comment = {"author": "human", "body": "Please fix", "createdAt": now_iso}

        approved = [{"number": 600, "title": "A", "labels": []}]
        blocked = [{"number": 601, "title": "B", "labels": []}]

        self._make_mocks(monkeypatch, tracker_responses={
            "list-by-labels:squidsquad,status:approved": approved,
            "list-by-labels:squidsquad,blocked:human-action": blocked,
            "list-by-labels:squidsquad,status:pending-human-setup": [],
            "list-by-labels:squidsquad,status:pending-human-review": [],
        }, gh_responses={
            "issue list": [{"number": 602, "title": "C", "labels": [], "updatedAt": now_iso}],
        })
        # Override comment enrichment to add comments
        monkeypatch.setattr(cycle_pre, "_fetch_latest_comment", lambda n: comment)

        result = cycle_pre._build_pm_input("pm")
        assert result["approved_items"][0].get("latest_comment") == comment
        assert result["human_blocked"][0].get("latest_comment") == comment

    def test_agent_health_parsed_on_nonzero_exit(self, patch_dirs, squid_dir, monkeypatch):
        """Regression #2713: health JSON must be parsed even when health_check.py exits 1."""
        health_data = [
            {"role": "skill", "status": "healthy"},
            {"role": "pm", "status": "unhealthy"},
        ]

        def fake_run_script(*args, **kwargs):
            fake = MagicMock()
            fake.returncode = 0
            fake.stdout = "[]"
            if len(args) >= 1 and "health_check.py" in str(args[0]):
                fake.returncode = 1  # non-zero exit = some agents unhealthy
                fake.stdout = json.dumps(health_data)
            elif len(args) >= 2 and "tracker.py" in str(args[0]):
                subcmd = args[1] if len(args) > 1 else ""
                fake.stdout = json.dumps({}.get(subcmd, []))
            return fake

        def fake_run(cmd, **kwargs):
            fake = MagicMock()
            fake.returncode = 0
            fake.stdout = "[]"
            fake.stderr = ""
            return fake

        monkeypatch.setattr(cycle_pre, "_run_script", fake_run_script)
        monkeypatch.setattr(cycle_pre, "_run", fake_run)
        monkeypatch.setattr(cycle_pre, "_config_get", lambda f: {
            "branch-workflow": "no", "pr-flow": "no",
            "improvement-scanning": "no", "vault-remember": "no",
            "vault-optimize": "no", "ship-threshold": "10",
            "shipped-since-bump": "0",
            "interval": "30",
        }.get(f, ""))
        monkeypatch.setattr(cycle_pre, "_fetch_latest_comment", lambda n: None)

        result = cycle_pre._build_pm_input("pm")
        assert result["agent_health"] == {"skill": "healthy", "pm": "unhealthy"}


class TestQAHealthParsing:
    """Regression #2713: QA builder also affected by health gate bug."""

    def test_qa_agent_health_parsed_on_nonzero_exit(self, patch_dirs, squid_dir, monkeypatch):
        """QA input parses health JSON even when health_check.py exits 1."""
        health_data = [
            {"role": "skill", "status": "healthy"},
            {"role": "dm", "status": "unknown"},
        ]

        def fake_run_script(*args, **kwargs):
            fake = MagicMock()
            fake.returncode = 0
            fake.stdout = "[]"
            if len(args) >= 1 and "health_check.py" in str(args[0]):
                fake.returncode = 1
                fake.stdout = json.dumps(health_data)
            elif len(args) >= 2 and "tracker.py" in str(args[0]):
                subcmd = args[1] if len(args) > 1 else ""
                fake.stdout = json.dumps({}.get(subcmd, []))
            return fake

        def fake_run(cmd, **kwargs):
            fake = MagicMock()
            fake.returncode = 0
            fake.stdout = "[]"
            fake.stderr = ""
            return fake

        monkeypatch.setattr(cycle_pre, "_run_script", fake_run_script)
        monkeypatch.setattr(cycle_pre, "_run", fake_run)
        monkeypatch.setattr(cycle_pre, "_config_get", lambda f: {
            "branch-workflow": "no", "pr-flow": "no",
            "improvement-scanning": "no", "vault-remember": "no",
            "vault-optimize": "no", "ship-threshold": "10",
            "shipped-since-bump": "0",
            "interval": "30",
        }.get(f, ""))
        monkeypatch.setattr(cycle_pre, "_fetch_latest_comment", lambda n: None)

        result = cycle_pre._build_qa_input("qa")
        assert result["agent_health"] == {"skill": "healthy", "dm": "unknown"}


class TestBootResults:
    """Tests for #2724: boot_results field in PM cycle-input.json."""

    def _make_mocks(self, monkeypatch, boot_data=None, boot_returncode=0):
        """Set up mocks with configurable boot_remote.py response."""

        def fake_run_script(*args, **kwargs):
            fake = MagicMock()
            fake.returncode = 0
            fake.stdout = "[]"
            if len(args) >= 1 and "boot_remote.py" in str(args[0]):
                fake.returncode = boot_returncode
                fake.stdout = json.dumps(boot_data if boot_data is not None else [])
            elif len(args) >= 1 and "health_check.py" in str(args[0]):
                fake.stdout = "[]"
            elif len(args) >= 2 and "tracker.py" in str(args[0]):
                fake.stdout = "[]"
            return fake

        def fake_run(cmd, **kwargs):
            fake = MagicMock()
            fake.returncode = 0
            fake.stdout = "[]"
            fake.stderr = ""
            return fake

        monkeypatch.setattr(cycle_pre, "_run_script", fake_run_script)
        monkeypatch.setattr(cycle_pre, "_run", fake_run)
        monkeypatch.setattr(cycle_pre, "_config_get", lambda f: {
            "branch-workflow": "no", "pr-flow": "no",
            "improvement-scanning": "no", "vault-remember": "no",
            "vault-optimize": "no", "ship-threshold": "10",
            "shipped-since-bump": "0",
            "interval": "30",
        }.get(f, ""))
        monkeypatch.setattr(cycle_pre, "_fetch_latest_comment", lambda n: None)

    def test_boot_results_present(self, patch_dirs, squid_dir, monkeypatch):
        """PM input includes boot_results field."""
        boot_data = [
            {"role": "skill", "action": "skip", "success": True, "message": "alive"},
        ]
        self._make_mocks(monkeypatch, boot_data=boot_data)
        result = cycle_pre._build_pm_input("pm")
        assert "boot_results" in result
        assert isinstance(result["boot_results"], list)
        assert len(result["boot_results"]) == 1
        assert result["boot_results"][0]["role"] == "skill"

    def test_boot_results_empty_when_no_agents(self, patch_dirs, squid_dir, monkeypatch):
        """boot_results is empty list when no agents configured."""
        self._make_mocks(monkeypatch, boot_data=[])
        result = cycle_pre._build_pm_input("pm")
        assert result["boot_results"] == []

    def test_boot_results_captures_spawn_failure(self, patch_dirs, squid_dir, monkeypatch):
        """boot_results captures spawn failures (boot_remote.py exits 1)."""
        boot_data = [
            {"role": "skill", "action": "spawn", "success": False, "message": "wt.exe not found"},
        ]
        self._make_mocks(monkeypatch, boot_data=boot_data, boot_returncode=1)
        result = cycle_pre._build_pm_input("pm")
        assert len(result["boot_results"]) == 1
        assert result["boot_results"][0]["success"] is False

    def test_auto_boot_agents_field_absent(self, patch_dirs, squid_dir, monkeypatch):
        """Regression #2724: auto_boot_agents field must NOT be in config."""
        self._make_mocks(monkeypatch)
        result = cycle_pre._build_pm_input("pm")
        assert "auto_boot_agents" not in result.get("config", {})

    def test_boot_results_handles_dict_response(self, patch_dirs, squid_dir, monkeypatch):
        """boot_results handles a single dict response (disabled/error case)."""
        boot_data = {"action": "error", "message": "no agents"}
        self._make_mocks(monkeypatch, boot_data=boot_data)
        result = cycle_pre._build_pm_input("pm")
        assert isinstance(result["boot_results"], list)
        assert len(result["boot_results"]) == 1

    def test_tc26_nonzero_exit_empty_stdout(self, patch_dirs, squid_dir, monkeypatch):
        """TC-26: boot_remote.py non-zero exit with empty stdout — cycle_pre
        must not crash and boot_results defaults to empty list."""

        def fake_run_script(*args, **kwargs):
            fake = MagicMock()
            fake.returncode = 0
            fake.stdout = "[]"
            if len(args) >= 1 and "boot_remote.py" in str(args[0]):
                fake.returncode = 1
                fake.stdout = ""  # empty — simulates crash/no output
            elif len(args) >= 1 and "health_check.py" in str(args[0]):
                fake.stdout = "[]"
            elif len(args) >= 2 and "tracker.py" in str(args[0]):
                fake.stdout = "[]"
            return fake

        monkeypatch.setattr(cycle_pre, "_run_script", fake_run_script)
        monkeypatch.setattr(cycle_pre, "_run", lambda cmd, **kw: MagicMock(
            returncode=0, stdout="[]", stderr=""))
        monkeypatch.setattr(cycle_pre, "_config_get", lambda f: {
            "branch-workflow": "no", "pr-flow": "no",
            "improvement-scanning": "no", "vault-remember": "no",
            "vault-optimize": "no", "ship-threshold": "10",
            "shipped-since-bump": "0", "interval": "30",
        }.get(f, ""))
        monkeypatch.setattr(cycle_pre, "_fetch_latest_comment", lambda n: None)

        result = cycle_pre._build_pm_input("pm")
        assert isinstance(result["boot_results"], list)
        assert result["boot_results"] == []

    def test_tc26_nonzero_exit_malformed_stdout(self, patch_dirs, squid_dir, monkeypatch):
        """TC-26: boot_remote.py non-zero exit with malformed JSON — cycle_pre
        must not crash and boot_results defaults to empty list."""

        def fake_run_script(*args, **kwargs):
            fake = MagicMock()
            fake.returncode = 0
            fake.stdout = "[]"
            if len(args) >= 1 and "boot_remote.py" in str(args[0]):
                fake.returncode = 1
                fake.stdout = "not valid json{{"
            elif len(args) >= 1 and "health_check.py" in str(args[0]):
                fake.stdout = "[]"
            elif len(args) >= 2 and "tracker.py" in str(args[0]):
                fake.stdout = "[]"
            return fake

        monkeypatch.setattr(cycle_pre, "_run_script", fake_run_script)
        monkeypatch.setattr(cycle_pre, "_run", lambda cmd, **kw: MagicMock(
            returncode=0, stdout="[]", stderr=""))
        monkeypatch.setattr(cycle_pre, "_config_get", lambda f: {
            "branch-workflow": "no", "pr-flow": "no",
            "improvement-scanning": "no", "vault-remember": "no",
            "vault-optimize": "no", "ship-threshold": "10",
            "shipped-since-bump": "0", "interval": "30",
        }.get(f, ""))
        monkeypatch.setattr(cycle_pre, "_fetch_latest_comment", lambda n: None)

        result = cycle_pre._build_pm_input("pm")
        assert isinstance(result["boot_results"], list)
        assert result["boot_results"] == []
