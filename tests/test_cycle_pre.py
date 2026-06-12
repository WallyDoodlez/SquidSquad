"""Tests for references/scripts/cycle_pre.py — pre-cycle mechanical operations."""

import json
import subprocess
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
    """Patch REPO_ROOT, SQUID_DIR, and _state_path to use tmp_path."""
    monkeypatch.setattr(cycle_pre, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(cycle_pre, "SQUID_DIR", squid_dir)
    # _state_path is imported from state_bus at load time — patch it so
    # working state, iterations, etc. resolve to the temp directory
    monkeypatch.setattr(cycle_pre, "_state_path", lambda rel: squid_dir / rel)
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

    def test_cursor_line_no_longer_parsed(self, patch_dirs, squid_dir):
        """#11329: the event cursor moved to harness-owned .event-state.json;
        working-state.md no longer carries a Last Processed Event ID line and
        the parser no longer surfaces one — even if a legacy install still has
        the line, it is ignored (not mistaken for agent-private state)."""
        ws = squid_dir / "skill" / "working-state.md"
        ws.write_text(
            "# Working State\n\n"
            "- **Task**: #5622\n"
            "- **Status**: in-progress\n"
            "- **Last Processed Event ID**: abc12345\n",  # legacy residue
            encoding="utf-8",
        )
        result = cycle_pre._read_working_state("skill")
        assert "last_processed_event_id" not in result


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
        fake.stderr = ""
        monkeypatch.setattr(cycle_pre, "_run_script", lambda *a, **kw: fake)
        assert cycle_pre._do_pull() == "ok"

    def test_error(self, monkeypatch):
        fake = MagicMock()
        fake.returncode = 1
        fake.stdout = ""
        fake.stderr = "fatal: network error"
        monkeypatch.setattr(cycle_pre, "_run_script", lambda *a, **kw: fake)
        assert cycle_pre._do_pull() == "error"

    def test_stash_conflict(self, monkeypatch):
        fake = MagicMock()
        fake.returncode = 0
        fake.stdout = "Pulled (stash pop conflict — run 'git stash show')"
        fake.stderr = ""
        monkeypatch.setattr(cycle_pre, "_run_script", lambda *a, **kw: fake)
        assert cycle_pre._do_pull() == "stash_conflict"

    def test_already_up_to_date_returns_ok(self, monkeypatch):
        """#5378: 'already up to date' should return 'ok', not 'error'."""
        fake = MagicMock()
        fake.returncode = 0
        fake.stdout = "Pulled (already up to date)"
        fake.stderr = ""
        monkeypatch.setattr(cycle_pre, "_run_script", lambda *a, **kw: fake)
        assert cycle_pre._do_pull() == "ok"

    def test_nonzero_with_pulled_in_stdout_returns_ok(self, monkeypatch):
        """#5378: If stdout says 'Pulled' but exit code is non-zero, still ok."""
        fake = MagicMock()
        fake.returncode = 1
        fake.stdout = "Pulled"
        fake.stderr = ""
        monkeypatch.setattr(cycle_pre, "_run_script", lambda *a, **kw: fake)
        assert cycle_pre._do_pull() == "ok"

    def test_genuine_error(self, monkeypatch):
        """Genuine errors (no 'pulled' in stdout) still return 'error'."""
        fake = MagicMock()
        fake.returncode = 1
        fake.stdout = ""
        fake.stderr = "fatal: unable to access remote"
        monkeypatch.setattr(cycle_pre, "_run_script", lambda *a, **kw: fake)
        assert cycle_pre._do_pull() == "error"


# ---------------------------------------------------------------------------
# Sub-process timeout guard (#9904)
# ---------------------------------------------------------------------------


class TestRunTimeout9904:
    """#9904: `_run` / `_run_script` must not block forever — every call site
    that fans out to a sub-process should have a defensive timeout so a
    single misbehaving sub-script can't wedge the entire cycle (the symptom
    that produced #9903).
    """

    def test_default_timeout_constant_is_bounded(self):
        """The default must be a positive finite number — not None, not 0."""
        assert isinstance(cycle_pre.DEFAULT_SCRIPT_TIMEOUT, (int, float))
        assert cycle_pre.DEFAULT_SCRIPT_TIMEOUT > 0
        # Sanity: not absurdly large (would defeat the point of the guard).
        assert cycle_pre.DEFAULT_SCRIPT_TIMEOUT <= 600

    def test_run_forwards_timeout_to_subprocess_run(self, monkeypatch):
        """Confirms `_run` passes its `timeout` kwarg to subprocess.run."""
        captured = {}

        def fake_subprocess_run(cmd, **kwargs):
            captured.update(kwargs)
            return subprocess.CompletedProcess(cmd, 0, "ok", "")

        monkeypatch.setattr(cycle_pre.subprocess, "run", fake_subprocess_run)
        cycle_pre._run(["echo", "hi"], timeout=7)
        assert captured.get("timeout") == 7

    def test_run_default_timeout_passed_when_unspecified(self, monkeypatch):
        """Callers that don't pass `timeout` get the default — not None."""
        captured = {}

        def fake_subprocess_run(cmd, **kwargs):
            captured.update(kwargs)
            return subprocess.CompletedProcess(cmd, 0, "ok", "")

        monkeypatch.setattr(cycle_pre.subprocess, "run", fake_subprocess_run)
        cycle_pre._run(["echo", "hi"])
        assert captured.get("timeout") == cycle_pre.DEFAULT_SCRIPT_TIMEOUT

    def test_run_returns_124_on_timeout(self, monkeypatch, capsys):
        """On TimeoutExpired, `_run` must return a CompletedProcess with
        returncode=124 (POSIX convention) — not raise — so existing
        `if result.returncode != 0` paths degrade gracefully instead of
        bubbling the exception to abort cycle_pre.
        """

        def fake_subprocess_run(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=kwargs.get("timeout", 0))

        monkeypatch.setattr(cycle_pre.subprocess, "run", fake_subprocess_run)
        result = cycle_pre._run(["python", "wedge.py"], timeout=1)
        assert result.returncode == 124
        assert result.stdout == ""
        assert "TIMEOUT" in result.stderr
        # Also emits a stderr diagnostic so a wedged sub-script is visible.
        captured = capsys.readouterr()
        assert "TIMEOUT" in captured.err

    def test_run_script_forwards_timeout(self, monkeypatch):
        """_run_script must forward `timeout` to _run — confirms the
        wrapper doesn't silently swallow the kwarg."""
        captured = {}

        def fake_run(cmd, **kwargs):
            captured.update(kwargs)
            return subprocess.CompletedProcess(cmd, 0, "", "")

        monkeypatch.setattr(cycle_pre, "_run", fake_run)
        cycle_pre._run_script("tracker.py", "list-issues", "skill", timeout=15)
        assert captured.get("timeout") == 15

    def test_run_script_default_timeout_when_unspecified(self, monkeypatch):
        """_run_script without explicit timeout still bounds the sub-process —
        the default propagates through the wrapper."""
        captured = {}

        def fake_run(cmd, **kwargs):
            captured.update(kwargs)
            return subprocess.CompletedProcess(cmd, 0, "", "")

        monkeypatch.setattr(cycle_pre, "_run", fake_run)
        cycle_pre._run_script("tracker.py", "list-issues", "skill")
        assert captured.get("timeout") == cycle_pre.DEFAULT_SCRIPT_TIMEOUT

    def test_real_timeout_with_sleep_subprocess(self):
        """End-to-end: a real subprocess that exceeds the timeout returns
        124 rather than hanging. Uses a tight 1s timeout against `python -c
        "import time; time.sleep(5)"` to keep the test fast.
        """
        result = cycle_pre._run(
            [sys.executable, "-c", "import time; time.sleep(5)"],
            timeout=1,
        )
        assert result.returncode == 124
        assert "TIMEOUT" in result.stderr


# ---------------------------------------------------------------------------
# Config Flags
# ---------------------------------------------------------------------------

class TestReadConfigFlags:
    def test_reads_all_flags(self, monkeypatch):
        flags = {
            "pr-flow": "no",
            "improvement-scanning": "yes",
            "vault-remember": "no",
            "vault-optimize": "yes",
        }
        monkeypatch.setattr(cycle_pre, "_config_get", lambda f: flags.get(f, ""))
        result = cycle_pre._read_config_flags()
        assert result["pr_flow"] is False
        assert result["improvement_scanning"] is True
        assert result["vault_remember"] is False
        assert result["vault_optimize"] is True

    def test_accepts_true_and_1_as_truthy(self, monkeypatch):
        """#8343 regression: 'true' and '1' must be accepted, not just 'yes'."""
        flags = {
            "pr-flow": "1",
            "improvement-scanning": "True",
            "vault-remember": "YES",
            "vault-optimize": "no",
        }
        monkeypatch.setattr(cycle_pre, "_config_get", lambda f: flags.get(f, ""))
        result = cycle_pre._read_config_flags()
        assert result["pr_flow"] is True
        assert result["improvement_scanning"] is True
        assert result["vault_remember"] is True
        assert result["vault_optimize"] is False


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
# Dead stub removal regression (#3813)
# ---------------------------------------------------------------------------

class TestNoTemplateChanged:
    """Regression test for #3813: template_changed was a dead stub always returning False."""

    def test_skill_input_has_no_template_changed(self, patch_dirs, monkeypatch):
        """_build_skill_input should not include template_changed field."""
        empty = MagicMock()
        empty.returncode = 0
        empty.stdout = "[]"
        monkeypatch.setattr(cycle_pre, "_run_script", lambda *a, **kw: empty)
        monkeypatch.setattr(cycle_pre, "_config_get", lambda f: {
            "interval": "30", "test-command": "",
            "branch-workflow": "no", "pr-flow": "no",
            "improvement-scanning": "no", "vault-remember": "no",
            "vault-optimize": "no",
        }.get(f, ""))

        result = cycle_pre._build_skill_input("skill")
        assert "template_changed" not in result

    def test_no_check_template_changed_function(self):
        """_check_template_changed should not exist — it was a dead stub."""
        assert not hasattr(cycle_pre, "_check_template_changed")


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

    def _make_mocks(self, monkeypatch, tracker_responses=None, gh_responses=None,
                     gh_fetch_responses=None):
        """Set up mocks for _run_script, _run, and _gh_fetch.

        `gh_fetch_responses` maps (label_filter, state) tuples -> list of issue
        dicts and is the post-refactor injection point: PM/QA/DM builders now
        derive every subset via Python filters over a small set of bulk
        `_gh_fetch` calls instead of fanning out tracker.py subprocesses.
        Tests built against the old per-call tracker mocks supply the same
        items via this map and label each fixture appropriately so the
        filters route them into the right bucket.
        """
        tracker_responses = tracker_responses or {}
        gh_responses = gh_responses or {}
        gh_fetch_responses = gh_fetch_responses or {}

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

        def fake_gh_fetch(label_filter, state, **kwargs):
            return gh_fetch_responses.get((label_filter, state), [])

        monkeypatch.setattr(cycle_pre, "_run_script", fake_run_script)
        monkeypatch.setattr(cycle_pre, "_run", fake_run)
        monkeypatch.setattr(cycle_pre, "_gh_fetch", fake_gh_fetch)
        monkeypatch.setattr(cycle_pre, "_config_get", lambda f: {
            "dev-agents": "skill",
            "branch-workflow": "no", "pr-flow": "no",
            "improvement-scanning": "no", "vault-remember": "no",
            "vault-optimize": "no", "ship-threshold": "10",
            "shipped-since-bump": "0",
            "interval": "30",
        }.get(f, ""))
        monkeypatch.setattr(cycle_pre, "_fetch_latest_comment", lambda n: None)

    def test_approved_items_present(self, patch_dirs, squid_dir, monkeypatch):
        """PM input includes approved_items field."""
        approved = [{
            "number": 100, "title": "Approved task",
            "labels": [{"name": "squidsquad"}, {"name": "status:approved"}],
        }]
        self._make_mocks(monkeypatch, gh_fetch_responses={
            ("squidsquad", "open"): approved,
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
        items = [
            {"number": 200, "title": "Needs human action",
              "labels": [{"name": "squidsquad"}, {"name": "blocked:human-action"}]},
            {"number": 201, "title": "Needs human review",
              "labels": [{"name": "squidsquad"}, {"name": "status:pending-human-review"}]},
        ]
        self._make_mocks(monkeypatch, gh_fetch_responses={
            ("squidsquad", "open"): items,
        })
        result = cycle_pre._build_pm_input("pm")
        assert "human_blocked" in result
        assert len(result["human_blocked"]) == 2
        numbers = {i["number"] for i in result["human_blocked"]}
        assert numbers == {200, 201}

    def test_human_blocked_deduplicates(self, patch_dirs, squid_dir, monkeypatch):
        """Items carrying multiple blocked labels are not duplicated.

        Bulk-fetch refactor: each item appears once in squid_open and is
        appended once to human_blocked regardless of how many blocked labels
        it carries. Old per-label-query path needed an explicit `seen` set
        for the same guarantee.
        """
        same_item = [{
            "number": 300, "title": "Same item",
            "labels": [
                {"name": "squidsquad"},
                {"name": "blocked:human-action"},
                {"name": "status:pending-human-setup"},
            ],
        }]
        self._make_mocks(monkeypatch, gh_fetch_responses={
            ("squidsquad", "open"): same_item,
        })
        result = cycle_pre._build_pm_input("pm")
        assert len(result["human_blocked"]) == 1

    def test_recently_commented_present(self, patch_dirs, squid_dir, monkeypatch):
        """PM input includes recently_commented field."""
        from datetime import datetime, timezone
        now_iso = datetime.now(timezone.utc).isoformat()
        items = [{
            "number": 400, "title": "Recent",
            "labels": [{"name": "squidsquad"}],
            "updatedAt": now_iso,
        }]
        self._make_mocks(monkeypatch, gh_fetch_responses={
            ("squidsquad", "open"): items,
        })
        result = cycle_pre._build_pm_input("pm")
        assert "recently_commented" in result
        assert len(result["recently_commented"]) == 1

    def test_recently_commented_filters_old(self, patch_dirs, squid_dir, monkeypatch):
        """Items updated more than 2x interval ago are excluded."""
        items = [{
            "number": 500, "title": "Old",
            "labels": [{"name": "squidsquad"}],
            "updatedAt": "2020-01-01T00:00:00Z",
        }]
        self._make_mocks(monkeypatch, gh_fetch_responses={
            ("squidsquad", "open"): items,
        })
        result = cycle_pre._build_pm_input("pm")
        assert len(result["recently_commented"]) == 0

    def test_all_new_fields_enriched_with_comments(self, patch_dirs, squid_dir, monkeypatch):
        """All three new fields are enriched with latest comments.

        Bulk-fetch refactor: `latest_comment` is now extracted from the
        inline `comments` field on each fetched item rather than from a
        per-item subprocess. The test fixture embeds `comments` directly.
        """
        from datetime import datetime, timezone
        now_iso = datetime.now(timezone.utc).isoformat()
        comment_inline = [{
            "author": {"login": "human"}, "body": "Please fix", "createdAt": now_iso,
        }]
        expected = {"author": "human", "body": "Please fix", "createdAt": now_iso}

        items = [
            {"number": 600, "title": "A",
              "labels": [{"name": "squidsquad"}, {"name": "status:approved"}],
              "updatedAt": now_iso, "comments": comment_inline},
            {"number": 601, "title": "B",
              "labels": [{"name": "squidsquad"}, {"name": "blocked:human-action"}],
              "updatedAt": now_iso, "comments": comment_inline},
        ]
        self._make_mocks(monkeypatch, gh_fetch_responses={
            ("squidsquad", "open"): items,
        })

        result = cycle_pre._build_pm_input("pm")
        assert result["approved_items"][0].get("latest_comment") == expected
        assert result["human_blocked"][0].get("latest_comment") == expected

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
    """Tests for boot_results field in PM cycle-input.json.

    Boot detection was deprecated (#3807) — boot_results is always [].
    These tests verify the field exists and is always empty.
    """

    def _make_mocks(self, monkeypatch):
        """Set up mocks for _build_pm_input."""

        def fake_run_script(*args, **kwargs):
            fake = MagicMock()
            fake.returncode = 0
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
        """PM input includes boot_results field as empty list (#3807)."""
        self._make_mocks(monkeypatch)
        result = cycle_pre._build_pm_input("pm")
        assert "boot_results" in result
        assert isinstance(result["boot_results"], list)
        assert result["boot_results"] == []

    def test_boot_results_empty_when_no_agents(self, patch_dirs, squid_dir, monkeypatch):
        """boot_results is empty list when no agents configured."""
        self._make_mocks(monkeypatch)
        result = cycle_pre._build_pm_input("pm")
        assert result["boot_results"] == []

    def test_auto_boot_agents_field_absent(self, patch_dirs, squid_dir, monkeypatch):
        """Regression #2724: auto_boot_agents field must NOT be in config."""
        self._make_mocks(monkeypatch)
        result = cycle_pre._build_pm_input("pm")
        assert "auto_boot_agents" not in result.get("config", {})

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


# ---------------------------------------------------------------------------
# E2E command uses shlex.split (#3079)
# ---------------------------------------------------------------------------

class TestE2eCmdShlexSplit:
    """Regression #3079: e2e_cmd must use shlex.split, not str.split."""

    def test_shlex_import_exists(self):
        """cycle_pre imports shlex module."""
        import importlib
        importlib.reload(cycle_pre)
        assert hasattr(cycle_pre, 'shlex') or 'shlex' in dir(cycle_pre) or \
            'shlex' in cycle_pre.__dict__ or \
            any('shlex' in str(v) for v in vars(cycle_pre).values()), \
            "cycle_pre.py must import shlex"

    def test_e2e_cmd_uses_shlex_split(self):
        """Source code uses shlex.split, not bare .split()."""
        import inspect
        source = inspect.getsource(cycle_pre._build_qa_input)
        assert "shlex.split" in source, (
            "e2e_cmd must use shlex.split() not .split() — "
            "bare split breaks on paths with spaces"
        )
        assert "e2e_cmd.split()" not in source, (
            "e2e_cmd.split() found — must use shlex.split(e2e_cmd)"
        )

    def test_e2e_cmd_opts_out_of_default_timeout_9904(self):
        """#9904 DS review: E2E test suites are user-configured commands
        that can legitimately exceed DEFAULT_SCRIPT_TIMEOUT (60s). The
        call site must pass ``timeout=None`` so a long-but-legitimate
        E2E run isn't killed and falsely reported as 'failed'."""
        import inspect
        source = inspect.getsource(cycle_pre._build_qa_input)
        # Locate the E2E _run line specifically.
        e2e_lines = [l for l in source.splitlines() if "shlex.split(e2e_cmd)" in l]
        assert e2e_lines, "E2E _run call site not found"
        assert any("timeout=None" in l for l in e2e_lines), (
            "E2E _run call must pass timeout=None to opt out of the "
            "DEFAULT_SCRIPT_TIMEOUT bound — otherwise legitimately long "
            "E2E runs would be killed and falsely reported as failed."
        )


# ---------------------------------------------------------------------------
# Multi-role pending-test queries — regression #4803
# ---------------------------------------------------------------------------

class TestGetVerifiableRoles:
    """_get_verifiable_roles returns all roles whose items need verification."""

    def test_includes_config_dev_agents(self, monkeypatch):
        """Dev agents from config are included."""
        monkeypatch.setattr(cycle_pre, "_config_get", lambda f: "skill, qa" if f == "dev-agents" else "")
        roles = cycle_pre._get_verifiable_roles()
        assert "skill" in roles
        assert "qa" in roles

    def test_always_includes_mandatory_roles(self, monkeypatch):
        """pm, verifier, dm are always included regardless of config (#9318, #6274.2).

        Post-#6055 these are mandatory roles. verifier (renamed from qa
        in #6274.2) was previously sourced from dev-agents — when
        config.md stopped listing it there (#9318), the test below
        catches the regression where verifier would silently drop out
        of PM's verifiable-role queries.
        """
        monkeypatch.setattr(cycle_pre, "_config_get", lambda f: "skill" if f == "dev-agents" else "")
        roles = cycle_pre._get_verifiable_roles()
        assert "dm" in roles
        assert "pm" in roles
        assert "verifier" in roles

    def test_fallback_when_config_empty(self, monkeypatch):
        """If config returns empty, at least skill is present."""
        monkeypatch.setattr(cycle_pre, "_config_get", lambda f: "")
        roles = cycle_pre._get_verifiable_roles()
        assert "skill" in roles
        # mandatory roles always added (pm, verifier, dm — #9318 / #6274.2)
        assert "dm" in roles
        assert "pm" in roles
        assert "verifier" in roles

    def test_deduplicates(self, monkeypatch):
        """Roles are not duplicated even if they appear in config and hardcoded."""
        monkeypatch.setattr(cycle_pre, "_config_get", lambda f: "skill, dm, pm" if f == "dev-agents" else "")
        roles = cycle_pre._get_verifiable_roles()
        assert roles == sorted(set(roles))

    def test_returns_sorted(self, monkeypatch):
        """Roles are returned in sorted order for determinism."""
        monkeypatch.setattr(cycle_pre, "_config_get", lambda f: "skill, qa, dev" if f == "dev-agents" else "")
        roles = cycle_pre._get_verifiable_roles()
        assert roles == sorted(roles)


class TestQAInputMultiRole:
    """Regression #4803: QA input must cover all verifiable roles, not just skill.

    Post-refactor: there's no per-role tracker.py loop to inspect — items
    flow through a single labeled `_gh_fetch` call and are routed into the
    verification queue by their `role:*` label. Tests assert routing/attribution
    on labeled fixtures.
    """

    def _setup(self, monkeypatch, gh_fetch_responses=None):
        gh_fetch_responses = gh_fetch_responses or {}

        def fake_gh_fetch(label_filter, state, **kwargs):
            return gh_fetch_responses.get((label_filter, state), [])

        monkeypatch.setattr(cycle_pre, "_gh_fetch", fake_gh_fetch)
        monkeypatch.setattr(cycle_pre, "_run_script", lambda *a, **k: MagicMock(
            returncode=0, stdout="[]"))
        monkeypatch.setattr(cycle_pre, "_run", lambda cmd, **kw: MagicMock(
            returncode=0, stdout="[]", stderr=""))
        monkeypatch.setattr(cycle_pre, "_config_get", lambda f: {
            "dev-agents": "skill",
            "e2e-tests": "(none)",
            "interval": "30",
            "branch-workflow": "no", "pr-flow": "no",
            "improvement-scanning": "no", "vault-remember": "no",
            "vault-optimize": "no",
        }.get(f, ""))

    def test_qa_queries_all_roles(self, patch_dirs, squid_dir, monkeypatch):
        """Items from dm, skill, pm, qa all appear in the QA verification queue."""
        items = [
            {"number": 3969, "title": "DM task",
              "labels": [{"name": "squidsquad"}, {"name": "role:dm"},
                          {"name": "type:issue"}, {"name": "status:pending-test"}]},
            {"number": 4000, "title": "Skill task",
              "labels": [{"name": "squidsquad"}, {"name": "role:skill"},
                          {"name": "type:issue"}, {"name": "status:pending-test"}]},
            {"number": 4001, "title": "PM task",
              "labels": [{"name": "squidsquad"}, {"name": "role:pm"},
                          {"name": "type:issue"}, {"name": "status:pending-test"}]},
            {"number": 4002, "title": "QA task",
              "labels": [{"name": "squidsquad"}, {"name": "role:qa"},
                          {"name": "type:issue"}, {"name": "status:pending-test"}]},
        ]
        self._setup(monkeypatch, gh_fetch_responses={("squidsquad", "open"): items})

        result = cycle_pre._build_qa_input("qa")
        numbers = [i["number"] for i in result["verification_queue"]["pending_test_issues"]]
        assert 3969 in numbers, "DM pending-test issue must appear in QA queue"
        assert 4000 in numbers, "Skill pending-test issue must appear in QA queue"
        assert 4001 in numbers, "PM pending-test issue must appear in QA queue"
        assert 4002 in numbers, "QA pending-test issue must appear in QA queue"

    def test_qa_items_have_source_role(self, patch_dirs, squid_dir, monkeypatch):
        """Each item in QA verification queue is attributed by role label."""
        items = [{
            "number": 3969, "title": "DM task",
            "labels": [{"name": "squidsquad"}, {"name": "role:dm"},
                        {"name": "type:issue"}, {"name": "status:pending-test"}],
        }]
        self._setup(monkeypatch, gh_fetch_responses={("squidsquad", "open"): items})

        result = cycle_pre._build_qa_input("qa")
        dm_items = [i for i in result["verification_queue"]["pending_test_issues"]
                     if i.get("source_role") == "dm"]
        assert len(dm_items) == 1
        assert dm_items[0]["branch"] == "squidsquad/dm/3969"

    def test_qa_branch_uses_correct_role_prefix(self, patch_dirs, squid_dir, monkeypatch):
        """Branch path uses the item's source role, not hardcoded 'skill'."""
        items = [{
            "number": 5000, "title": "QA task",
            "labels": [{"name": "squidsquad"}, {"name": "role:qa"},
                        {"name": "type:task"}, {"name": "status:pending-test"}],
        }]
        self._setup(monkeypatch, gh_fetch_responses={("squidsquad", "open"): items})

        result = cycle_pre._build_qa_input("qa")
        qa_items = [i for i in result["verification_queue"]["pending_test_tasks"]
                    if i.get("source_role") == "qa"]
        assert len(qa_items) == 1
        assert qa_items[0]["branch"] == "squidsquad/qa/5000"


class TestPMInputMultiRole:
    """Regression #4803: PM input must cover all verifiable roles.

    Post-refactor: items flow through a single labeled `_gh_fetch` call and
    are routed by role label. Tests assert routing/attribution on labeled
    fixtures.
    """

    def _setup(self, monkeypatch, gh_fetch_responses=None):
        gh_fetch_responses = gh_fetch_responses or {}

        def fake_gh_fetch(label_filter, state, **kwargs):
            return gh_fetch_responses.get((label_filter, state), [])

        monkeypatch.setattr(cycle_pre, "_gh_fetch", fake_gh_fetch)
        monkeypatch.setattr(cycle_pre, "_run_script", lambda *a, **k: MagicMock(
            returncode=0, stdout="[]"))
        monkeypatch.setattr(cycle_pre, "_run", lambda cmd, **kw: MagicMock(
            returncode=0, stdout="[]", stderr=""))
        monkeypatch.setattr(cycle_pre, "_config_get", lambda f: {
            "dev-agents": "skill",
            "interval": "30", "ship-threshold": "10", "shipped-since-bump": "0",
            "branch-workflow": "no", "pr-flow": "no",
            "improvement-scanning": "no", "vault-remember": "no",
            "vault-optimize": "no",
        }.get(f, ""))

    def test_pm_queries_all_roles(self, patch_dirs, squid_dir, monkeypatch):
        """PM pending-test queue surfaces items from every verifiable role."""
        items = [
            {"number": 3969, "title": "DM issue",
              "labels": [{"name": "squidsquad"}, {"name": "role:dm"},
                          {"name": "type:issue"}, {"name": "status:pending-test"}]},
            {"number": 3970, "title": "QA issue",
              "labels": [{"name": "squidsquad"}, {"name": "role:qa"},
                          {"name": "type:issue"}, {"name": "status:pending-test"}]},
        ]
        self._setup(monkeypatch, gh_fetch_responses={("squidsquad", "open"): items})

        result = cycle_pre._build_pm_input("pm")
        numbers = {i["number"] for i in result["tracker"]["pending_test_issues"]}
        assert 3969 in numbers, "DM pending-test item must reach PM queue"
        assert 3970 in numbers, "QA pending-test item must reach PM queue"

    def test_pm_items_have_source_role(self, patch_dirs, squid_dir, monkeypatch):
        """PM pending-test items include source_role attribution."""
        items = [{
            "number": 3969, "title": "DM issue",
            "labels": [{"name": "squidsquad"}, {"name": "role:dm"},
                        {"name": "type:issue"}, {"name": "status:pending-test"}],
        }]
        self._setup(monkeypatch, gh_fetch_responses={("squidsquad", "open"): items})

        result = cycle_pre._build_pm_input("pm")
        dm_items = [i for i in result["tracker"]["pending_test_issues"]
                     if i.get("source_role") == "dm"]
        assert len(dm_items) == 1


# ---------------------------------------------------------------------------
# Branch enforcement — regression #4942
# ---------------------------------------------------------------------------

class TestEnforceBranch:
    """cycle_pre._enforce_branch ensures correct branch before pull."""

    def test_calls_task_begin_for_active_task(self, monkeypatch):
        """When working-state has an active task, task-begin is called."""
        calls = []

        def fake_run_script(*args, **kwargs):
            calls.append(args)
            return MagicMock(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(cycle_pre, "_config_get",
                            lambda f: "yes" if f == "branch-workflow" else "main")
        monkeypatch.setattr(cycle_pre, "_run_script", fake_run_script)
        monkeypatch.setattr(cycle_pre, "_run",
                            lambda cmd, **kw: MagicMock(returncode=0, stdout="main\n", stderr=""))

        ws = {"task": "#4942", "status": "in-progress"}
        cycle_pre._enforce_branch("skill", ws)

        task_begin_calls = [c for c in calls if "task-begin" in c]
        assert len(task_begin_calls) == 1
        assert "4942" in task_begin_calls[0]

    @pytest.mark.parametrize("task_field,expected_number", [
        ("#9965", "9965"),
        ("9965", "9965"),
        ("#9965 — 6274.2 AC2.8 catch-up (PM option-3 path) [PAUSED]", "9965"),
        ("#10072 — verbose description with em-dash", "10072"),
        ("9965 — bare-number verbose form", "9965"),
        # Whitespace tolerance (DS review Finding 1 — was a regression vs old code)
        ("# 9965", "9965"),
        ("  #9965", "9965"),
        ("#\t9965", "9965"),
        ("#9965 - ASCII dash separator", "9965"),
        # Backward compat with old task.lstrip("#") behavior (DS round 2 Finding 1)
        ("##4942", "4942"),
        ("###9965 — triple-hash typo", "9965"),
    ])
    def test_extracts_number_from_verbose_task_field(
        self, monkeypatch, task_field, expected_number
    ):
        """#10072: regex extraction handles both bare and verbose task forms."""
        calls = []

        def fake_run_script(*args, **kwargs):
            calls.append(args)
            return MagicMock(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(cycle_pre, "_config_get",
                            lambda f: "yes" if f == "branch-workflow" else "main")
        monkeypatch.setattr(cycle_pre, "_run_script", fake_run_script)
        monkeypatch.setattr(cycle_pre, "_run",
                            lambda cmd, **kw: MagicMock(returncode=0, stdout="main\n", stderr=""))

        ws = {"task": task_field, "status": "in-progress"}
        cycle_pre._enforce_branch("skill", ws)

        task_begin_calls = [c for c in calls if "task-begin" in c]
        assert len(task_begin_calls) == 1, f"task-begin not called for {task_field!r}"
        assert expected_number in task_begin_calls[0], \
            f"expected {expected_number} in {task_begin_calls[0]} for {task_field!r}"

    @pytest.mark.parametrize("task_field", [
        "no-number-here",
        "#",                # DS review Finding 2: hash with no digits
        "#abc",             # hash followed by non-digits
        "9965-fix",         # DS review Finding 3: glued suffix — old code rejected
        "9965abc",          # digits glued to letters
    ])
    def test_skips_task_begin_for_non_numeric_task(self, monkeypatch, task_field):
        """#10072: malformed task fields skip task-begin without crashing."""
        calls = []

        def fake_run_script(*args, **kwargs):
            calls.append(args)
            return MagicMock(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(cycle_pre, "_config_get",
                            lambda f: "yes" if f == "branch-workflow" else "main")
        monkeypatch.setattr(cycle_pre, "_run_script", fake_run_script)
        monkeypatch.setattr(cycle_pre, "_run",
                            lambda cmd, **kw: MagicMock(returncode=0, stdout="main\n", stderr=""))

        ws = {"task": task_field, "status": "in-progress"}
        cycle_pre._enforce_branch("skill", ws)

        task_begin_calls = [c for c in calls if "task-begin" in c]
        assert len(task_begin_calls) == 0, \
            f"task-begin unexpectedly called for {task_field!r}: {task_begin_calls}"

    def test_switches_to_working_branch_when_no_task(self, monkeypatch):
        """When no active task, switches to working branch."""
        checkout_targets = []

        def fake_run(cmd, **kwargs):
            r = MagicMock()
            r.returncode = 0
            r.stdout = "squidsquad/skill/old\n"
            r.stderr = ""
            if isinstance(cmd, list) and "checkout" in cmd:
                checkout_targets.append(cmd[-1])
            return r

        monkeypatch.setattr(cycle_pre, "_config_get",
                            lambda f: {"branch-workflow": "yes", "working-branch": "main"}.get(f, ""))
        monkeypatch.setattr(cycle_pre, "_run", fake_run)

        ws = {"task": "none", "status": "none"}
        cycle_pre._enforce_branch("skill", ws)

        assert "main" in checkout_targets

    def test_stays_on_working_branch_when_already_there(self, monkeypatch):
        """No checkout when already on working branch."""
        checkout_calls = []

        def fake_run(cmd, **kwargs):
            r = MagicMock()
            r.returncode = 0
            r.stdout = "main\n"  # already on main
            r.stderr = ""
            if isinstance(cmd, list) and "checkout" in cmd:
                checkout_calls.append(cmd)
            return r

        monkeypatch.setattr(cycle_pre, "_config_get",
                            lambda f: {"branch-workflow": "yes", "working-branch": "main"}.get(f, ""))
        monkeypatch.setattr(cycle_pre, "_run", fake_run)

        ws = {"task": "none", "status": "none"}
        cycle_pre._enforce_branch("skill", ws)

        assert len(checkout_calls) == 0


class TestBranchGuardrail:
    """#5208: cycle_pre detects wrong branch and auto-corrects."""

    def test_returns_correction_when_on_wrong_branch(self, monkeypatch):
        """Returns branch_correction dict when on a feature branch with no active task."""
        checkout_targets = []

        def fake_run(cmd, **kwargs):
            r = MagicMock()
            r.returncode = 0
            if isinstance(cmd, list) and "branch" in cmd and "--show-current" in cmd:
                r.stdout = "squidsquad/task/5126\n"
            elif isinstance(cmd, list) and "checkout" in cmd:
                checkout_targets.append(cmd[-1])
                r.stdout = ""
            else:
                r.stdout = ""
            r.stderr = ""
            return r

        monkeypatch.setattr(cycle_pre, "_config_get",
                            lambda f: {"branch-workflow": "yes", "working-branch": "main"}.get(f, ""))
        monkeypatch.setattr(cycle_pre, "_run", fake_run)

        ws = {"task": "none", "status": "none"}
        result = cycle_pre._enforce_branch("skill", ws)

        assert result is not None
        assert result["corrected"] is True
        assert result["was_on"] == "squidsquad/task/5126"
        assert result["switched_to"] == "main"
        assert "main" in checkout_targets

    def test_returns_none_when_on_correct_branch(self, monkeypatch):
        """Returns None when already on working branch."""
        def fake_run(cmd, **kwargs):
            r = MagicMock()
            r.returncode = 0
            r.stdout = "main\n"
            r.stderr = ""
            return r

        monkeypatch.setattr(cycle_pre, "_config_get",
                            lambda f: {"branch-workflow": "yes", "working-branch": "main"}.get(f, ""))
        monkeypatch.setattr(cycle_pre, "_run", fake_run)

        ws = {"task": "none", "status": "none"}
        result = cycle_pre._enforce_branch("skill", ws)

        assert result is None

    def test_uses_configured_working_branch(self, monkeypatch):
        """Uses config value, not hardcoded 'main'."""
        checkout_targets = []

        def fake_run(cmd, **kwargs):
            r = MagicMock()
            r.returncode = 0
            if isinstance(cmd, list) and "branch" in cmd and "--show-current" in cmd:
                r.stdout = "squidsquad/task/999\n"
            elif isinstance(cmd, list) and "checkout" in cmd:
                checkout_targets.append(cmd[-1])
                r.stdout = ""
            else:
                r.stdout = ""
            r.stderr = ""
            return r

        monkeypatch.setattr(cycle_pre, "_config_get",
                            lambda f: {"branch-workflow": "yes", "working-branch": "develop"}.get(f, ""))
        monkeypatch.setattr(cycle_pre, "_run", fake_run)

        ws = {"task": "none", "status": "none"}
        result = cycle_pre._enforce_branch("skill", ws)

        assert result["switched_to"] == "develop"
        assert "develop" in checkout_targets



class TestConfigVersionValidation:
    """#5136: Post-pull config.md version regression detection."""

    def test_fixes_regressed_version(self, monkeypatch):
        """Auto-fixes config.md when version < latest git tag."""
        config_calls = []

        def fake_run(cmd, **kwargs):
            r = MagicMock()
            r.returncode = 0
            if isinstance(cmd, list) and "tag" in cmd:
                r.stdout = "v0.31.0\nv0.30.0\nv0.29.0\n"
            else:
                r.stdout = ""
            r.stderr = ""
            return r

        def fake_run_script(*args, **kwargs):
            config_calls.append(args)
            return MagicMock(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(cycle_pre, "_run", fake_run)
        monkeypatch.setattr(cycle_pre, "_run_script", fake_run_script)
        monkeypatch.setattr(cycle_pre, "_config_get", lambda f: "0.29.0" if f == "version" else "")

        cycle_pre._validate_config_version()

        # Should have called config.py set version 0.31.0
        set_calls = [c for c in config_calls if "set" in c and "version" in c]
        assert len(set_calls) == 1
        assert "0.31.0" in set_calls[0]

    def test_no_fix_when_version_current(self, monkeypatch):
        """No fix when config.md version matches latest tag."""
        config_calls = []

        def fake_run(cmd, **kwargs):
            r = MagicMock()
            r.returncode = 0
            if isinstance(cmd, list) and "tag" in cmd:
                r.stdout = "v0.31.0\nv0.30.0\n"
            else:
                r.stdout = ""
            r.stderr = ""
            return r

        monkeypatch.setattr(cycle_pre, "_run", fake_run)
        monkeypatch.setattr(cycle_pre, "_run_script", lambda *a, **kw: config_calls.append(a))
        monkeypatch.setattr(cycle_pre, "_config_get", lambda f: "0.31.0" if f == "version" else "")

        cycle_pre._validate_config_version()

        set_calls = [c for c in config_calls if "set" in c]
        assert len(set_calls) == 0

    def test_no_downgrade_when_config_newer(self, monkeypatch):
        """Config version newer than latest tag is not downgraded."""
        config_calls = []

        def fake_run(cmd, **kwargs):
            r = MagicMock()
            r.returncode = 0
            if isinstance(cmd, list) and "tag" in cmd:
                r.stdout = "v0.31.0\nv0.30.0\n"
            else:
                r.stdout = ""
            r.stderr = ""
            return r

        monkeypatch.setattr(cycle_pre, "_run", fake_run)
        monkeypatch.setattr(cycle_pre, "_run_script", lambda *a, **kw: config_calls.append(a))
        monkeypatch.setattr(cycle_pre, "_config_get", lambda f: "0.32.0" if f == "version" else "")

        cycle_pre._validate_config_version()

        set_calls = [c for c in config_calls if "set" in c]
        assert len(set_calls) == 0

    def test_no_crash_on_missing_tags(self, monkeypatch):
        """Graceful when no git tags exist."""
        def fake_run(cmd, **kwargs):
            r = MagicMock()
            r.returncode = 0
            r.stdout = ""
            r.stderr = ""
            return r

        monkeypatch.setattr(cycle_pre, "_run", fake_run)
        monkeypatch.setattr(cycle_pre, "_config_get", lambda f: "0.31.0")

        cycle_pre._validate_config_version()  # Should not raise

    def test_no_crash_on_empty_config_version(self, monkeypatch):
        """Graceful when config has no version field."""
        def fake_run(cmd, **kwargs):
            r = MagicMock()
            r.returncode = 0
            r.stdout = "v0.31.0\n"
            r.stderr = ""
            return r

        monkeypatch.setattr(cycle_pre, "_run", fake_run)
        monkeypatch.setattr(cycle_pre, "_config_get", lambda f: "")

        cycle_pre._validate_config_version()  # Should not raise


# ---------------------------------------------------------------------------
# _config_get_int (#8115)
# ---------------------------------------------------------------------------

class TestConfigGetInt:
    """Tests for _config_get_int — safe int parsing from config values."""

    def test_valid_integer(self, monkeypatch):
        monkeypatch.setattr(cycle_pre, "_config_get", lambda f: "42")
        assert cycle_pre._config_get_int("ship-threshold", 10) == 42

    def test_empty_returns_default(self, monkeypatch):
        monkeypatch.setattr(cycle_pre, "_config_get", lambda f: "")
        assert cycle_pre._config_get_int("ship-threshold", 10) == 10

    def test_none_like_returns_default(self, monkeypatch):
        """_config_get returns '' on failure, never None, but guard anyway."""
        monkeypatch.setattr(cycle_pre, "_config_get", lambda f: "")
        assert cycle_pre._config_get_int("interval", 30) == 30

    def test_non_numeric_returns_default(self, monkeypatch):
        """#8115 regression: '10 items' must not crash."""
        monkeypatch.setattr(cycle_pre, "_config_get", lambda f: "10 items")
        assert cycle_pre._config_get_int("ship-threshold", 10) == 10

    def test_float_string_returns_default(self, monkeypatch):
        monkeypatch.setattr(cycle_pre, "_config_get", lambda f: "10.5")
        assert cycle_pre._config_get_int("interval", 30) == 30

    def test_whitespace_only_returns_default(self, monkeypatch):
        monkeypatch.setattr(cycle_pre, "_config_get", lambda f: "   ")
        assert cycle_pre._config_get_int("shipped-since-bump", 0) == 0

    def test_zero_is_valid(self, monkeypatch):
        monkeypatch.setattr(cycle_pre, "_config_get", lambda f: "0")
        assert cycle_pre._config_get_int("shipped-since-bump", 5) == 0

    def test_negative_is_valid(self, monkeypatch):
        """Negative values are technically valid integers."""
        monkeypatch.setattr(cycle_pre, "_config_get", lambda f: "-1")
        assert cycle_pre._config_get_int("ship-threshold", 10) == -1


# ---------------------------------------------------------------------------
# _filter_events_for_role — #8489
# ---------------------------------------------------------------------------

class TestFilterEventsForRole:
    """#8489: _filter_events_for_role test coverage."""

    SAMPLE_EVENTS = [
        {"event_type": "status-transition", "payload": "a"},
        {"event_type": "pr-merged", "payload": "b"},
        {"event_type": "cycle-start", "payload": "c"},
        {"event_type": "verification-failed", "payload": "d"},
    ]

    def test_config_driven_filter(self, monkeypatch):
        """Config-driven filter returns only matching event_types."""
        # Simulate config module providing filters
        fake_config = MagicMock()
        fake_config.get_event_filters_for_role = lambda role: {"status-transition", "pr-merged"}
        monkeypatch.setitem(sys.modules, "config", fake_config)

        result = cycle_pre._filter_events_for_role(self.SAMPLE_EVENTS, "skill")
        types = {e["event_type"] for e in result}
        assert types == {"status-transition", "pr-merged"}

    def test_hardcoded_fallback_when_config_absent(self, monkeypatch):
        """Falls back to _ROLE_EVENT_TYPES when config import fails."""
        # Force ImportError for config module
        real_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__

        def fail_config(name, *args, **kwargs):
            if name == "config":
                raise ImportError("no config")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", fail_config)

        result = cycle_pre._filter_events_for_role(self.SAMPLE_EVENTS, "skill")
        # skill hardcoded types: pr-merged, compose-completed, verification-failed, status-transition
        types = {e["event_type"] for e in result}
        assert "status-transition" in types
        assert "pr-merged" in types
        assert "cycle-start" not in types  # Not in skill's hardcoded set

    def test_no_filter_passthrough_for_unknown_role(self, monkeypatch):
        """Unknown roles not in _ROLE_EVENT_TYPES get all events."""
        def fail_config(name, *args, **kwargs):
            if name == "config":
                raise ImportError("no config")
            return __import__(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", fail_config)

        result = cycle_pre._filter_events_for_role(self.SAMPLE_EVENTS, "unknown-role")
        assert len(result) == len(self.SAMPLE_EVENTS)

    def test_config_returns_none_falls_to_hardcoded(self, monkeypatch):
        """When config.get_event_filters_for_role returns None, use hardcoded."""
        fake_config = MagicMock()
        fake_config.get_event_filters_for_role = lambda role: None
        monkeypatch.setitem(sys.modules, "config", fake_config)

        result = cycle_pre._filter_events_for_role(self.SAMPLE_EVENTS, "pm")
        types = {e["event_type"] for e in result}
        # PM hardcoded: pr-merged, compose-completed, verification-failed, verification-passed,
        # cycle-start, cycle-end, status-transition, agent-health
        assert "cycle-start" in types
        assert "status-transition" in types

    def test_empty_events_returns_empty(self, monkeypatch):
        """Empty event list returns empty regardless of filter."""
        fake_config = MagicMock()
        fake_config.get_event_filters_for_role = lambda role: {"status-transition"}
        monkeypatch.setitem(sys.modules, "config", fake_config)

        result = cycle_pre._filter_events_for_role([], "skill")
        assert result == []

    def test_config_exception_falls_to_hardcoded(self, monkeypatch):
        """Generic exception from config is caught, falls to hardcoded."""
        fake_config = MagicMock()
        fake_config.get_event_filters_for_role = MagicMock(side_effect=RuntimeError("bad config"))
        monkeypatch.setitem(sys.modules, "config", fake_config)

        result = cycle_pre._filter_events_for_role(self.SAMPLE_EVENTS, "dm")
        types = {e["event_type"] for e in result}
        # DM hardcoded: status-transition, verification-passed, pr-merged, compose-completed
        assert "status-transition" in types
        assert "pr-merged" in types
        assert "cycle-start" not in types


# ---------------------------------------------------------------------------
# _run_mechanical_reactions — #8532
# ---------------------------------------------------------------------------

class TestRunMechanicalReactions:
    """#8532: _run_mechanical_reactions test coverage."""

    def test_empty_events_returns_empty(self):
        """Empty event list returns empty reactions."""
        assert cycle_pre._run_mechanical_reactions([], "skill") == []

    def test_self_emitted_events_skipped(self):
        """Events emitted by the same role are skipped."""
        events = [
            {"event_type": "pr-merged", "role": "pm",
             "payload": {"success": True, "pr_number": "10", "issue_number": "5"},
             "id": "abc"},
        ]
        result = cycle_pre._run_mechanical_reactions(events, "pm")
        # PM emitted + PM consuming → skipped (self-emitted)
        assert len(result) == 0

    def test_pr_merged_pm_produces_merge_detected(self):
        """pr-merged + PM role + success produces pr-merge-detected reaction."""
        events = [
            {"event_type": "pr-merged", "role": "harness",
             "payload": {"success": True, "pr_number": "42", "issue_number": "100"},
             "id": "evt1"},
        ]
        result = cycle_pre._run_mechanical_reactions(events, "pm")
        merge_detected = [r for r in result if r["type"] == "pr-merge-detected"]
        assert len(merge_detected) == 1
        assert merge_detected[0]["pr_number"] == "42"
        assert merge_detected[0]["issue_number"] == "100"

    def test_pr_merged_non_pm_produces_reactive_pull(self):
        """pr-merged + non-PM role + success produces reactive-pull-needed."""
        events = [
            {"event_type": "pr-merged", "role": "harness",
             "payload": {"success": True, "pr_number": "42", "issue_number": "100"},
             "id": "evt2"},
        ]
        result = cycle_pre._run_mechanical_reactions(events, "skill")
        pull_needed = [r for r in result if r["type"] == "reactive-pull-needed"]
        assert len(pull_needed) == 1
        assert pull_needed[0]["pr_number"] == "42"

    def test_pr_merged_failed_no_reaction(self):
        """Failed merge (success=False) produces no reactions."""
        events = [
            {"event_type": "pr-merged", "role": "harness",
             "payload": {"success": False, "pr_number": "42", "issue_number": "100"},
             "id": "evt3"},
        ]
        result = cycle_pre._run_mechanical_reactions(events, "pm")
        assert len(result) == 0

    def test_verification_failed_dev_produces_rework(self):
        """verification-failed + dev role produces rework-needed reaction."""
        events = [
            {"event_type": "verification-failed", "role": "qa",
             "payload": {"issue_number": "55", "reason": "AC-2 not met"},
             "id": "evt4"},
        ]
        result = cycle_pre._run_mechanical_reactions(events, "skill")
        rework = [r for r in result if r["type"] == "rework-needed"]
        assert len(rework) == 1
        assert rework[0]["issue_number"] == "55"
        assert rework[0]["reason"] == "AC-2 not met"

    def test_verification_failed_non_dev_no_reaction(self):
        """verification-failed for non-dev role (pm) produces no rework reaction."""
        events = [
            {"event_type": "verification-failed", "role": "qa",
             "payload": {"issue_number": "55"},
             "id": "evt5"},
        ]
        result = cycle_pre._run_mechanical_reactions(events, "pm")
        rework = [r for r in result if r["type"] == "rework-needed"]
        assert len(rework) == 0


# ---------------------------------------------------------------------------
# Task-mode CLI parsing — #8701
# ---------------------------------------------------------------------------


class TestParseCliArgs:
    def test_role_only_no_task(self):
        role, task = cycle_pre._parse_cli_args(["skill"])
        assert role == "skill"
        assert task is None

    def test_role_with_task_flag(self):
        role, task = cycle_pre._parse_cli_args(["skill", "--task", "42"])
        assert role == "skill"
        assert task == "42"

    def test_task_flag_with_no_value_ignored(self):
        """Trailing `--task` without a value should not crash."""
        role, task = cycle_pre._parse_cli_args(["skill", "--task"])
        assert role == "skill"
        assert task is None

    def test_empty_argv(self):
        role, task = cycle_pre._parse_cli_args([])
        assert role is None
        assert task is None

    def test_extra_args_after_task(self):
        role, task = cycle_pre._parse_cli_args(["pm", "--task", "100", "--ignored"])
        assert role == "pm"
        assert task == "100"


# ---------------------------------------------------------------------------
# Harness reachability probe — #4792 Phase 2 §5.5 (Q8)
# ---------------------------------------------------------------------------


class TestDiscoverHarnessPort:
    def test_default_port_when_no_file(self, patch_dirs, squid_dir):
        # No .harness-port anywhere → fall back to 7373
        assert cycle_pre._discover_harness_port() == 7373

    def test_reads_squid_dir_port_file(self, patch_dirs, squid_dir):
        (squid_dir / ".harness-port").write_text("9999", encoding="utf-8")
        assert cycle_pre._discover_harness_port() == 9999

    def test_invalid_port_file_falls_back_to_default(self, patch_dirs, squid_dir):
        (squid_dir / ".harness-port").write_text("not-a-port", encoding="utf-8")
        assert cycle_pre._discover_harness_port() == 7373

    def test_parent_walk_finds_port_file(self, patch_dirs, squid_dir, tmp_path):
        """Clone-isolation: agent clone is a child of the primary repo, so
        `.harness-port` lives in a parent's `.squidsquad/` rather than the
        clone's own. The 5-level walk must discover it."""
        parent_squid = tmp_path.parent / ".squidsquad"
        parent_squid.mkdir(parents=True, exist_ok=True)
        (parent_squid / ".harness-port").write_text("8888", encoding="utf-8")
        try:
            # REPO_ROOT is tmp_path; no local port file → walk picks up parent.
            assert cycle_pre._discover_harness_port() == 8888
        finally:
            (parent_squid / ".harness-port").unlink()
            parent_squid.rmdir()


class TestQueryHarnessStatus:
    """`harness_status` is informational (#4792 §5.5, Q8) — no decision
    branches on it. The probe must (a) return `"reachable"` on a 2xx
    response, (b) return `"unreachable"` on any error class, and
    (c) never raise out of the call site."""

    def test_returns_reachable_on_200(self, patch_dirs):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = lambda self: self
        mock_resp.__exit__ = lambda self, *a: False
        with patch("cycle_pre.urllib.request.urlopen", return_value=mock_resp):
            assert cycle_pre._query_harness_status() == "reachable"

    def test_returns_unreachable_on_urlerror(self, patch_dirs):
        import urllib.error
        with patch("cycle_pre.urllib.request.urlopen",
                   side_effect=urllib.error.URLError("connection refused")):
            assert cycle_pre._query_harness_status() == "unreachable"

    def test_returns_unreachable_on_timeout(self, patch_dirs):
        """In CPython, urlopen wraps `socket.timeout` inside a `URLError`
        before it reaches the caller (so the `URLError` test above is the
        real production timeout path). This test pins the defense-in-depth
        branch: if a non-stdlib urllib backend ever surfaced a bare
        `TimeoutError`, fail-open semantics must still hold."""
        with patch("cycle_pre.urllib.request.urlopen",
                   side_effect=TimeoutError("slow")):
            assert cycle_pre._query_harness_status() == "unreachable"

    def test_returns_unreachable_on_httperror(self, patch_dirs):
        """A reachable harness that returns 5xx is the realistic non-2xx
        path: urlopen raises `HTTPError` (a URLError subclass) for any
        4xx/5xx response rather than returning a response object. Pin
        the production behavior here, not just the defensive branch."""
        import urllib.error
        err = urllib.error.HTTPError(
            "http://127.0.0.1:7373/status", 503,
            "Service Unavailable", {}, None,
        )
        with patch("cycle_pre.urllib.request.urlopen", side_effect=err):
            assert cycle_pre._query_harness_status() == "unreachable"

    def test_returns_unreachable_on_oserror(self, patch_dirs):
        with patch("cycle_pre.urllib.request.urlopen",
                   side_effect=OSError("network down")):
            assert cycle_pre._query_harness_status() == "unreachable"

    def test_non_2xx_response_is_unreachable(self, patch_dirs):
        """Defense-in-depth check on the `200 <= status < 300` guard. In
        production CPython, urlopen raises `HTTPError` for non-2xx (see
        `test_returns_unreachable_on_httperror`), so the returning-non-2xx
        branch is only reachable if a future urllib wrapper changes the
        contract. Keep this test to lock the guard's value."""
        mock_resp = MagicMock()
        mock_resp.status = 503
        mock_resp.__enter__ = lambda self: self
        mock_resp.__exit__ = lambda self, *a: False
        with patch("cycle_pre.urllib.request.urlopen", return_value=mock_resp):
            assert cycle_pre._query_harness_status() == "unreachable"

    def test_uses_short_timeout(self, patch_dirs):
        """Spec calls for a 1-2s timeout so an unreachable harness doesn't
        stall cycle_pre. Lock the upper bound."""
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["timeout"] = timeout
            raise OSError("not actually opening")

        with patch("cycle_pre.urllib.request.urlopen", side_effect=fake_urlopen):
            cycle_pre._query_harness_status()
        assert captured["timeout"] is not None and captured["timeout"] <= 2

