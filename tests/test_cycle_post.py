"""Tests for references/scripts/cycle_post.py — post-cycle mechanical operations."""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import cycle_post


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
    monkeypatch.setattr(cycle_post, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(cycle_post, "SQUID_DIR", squid_dir)
    return tmp_path


def _write_output(squid_dir, role, data):
    """Write cycle-output.json for a role."""
    output_path = squid_dir / role / "cycle-output.json"
    output_path.write_text(json.dumps(data), encoding="utf-8")
    return output_path


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class TestValidateOutput:
    def test_valid_minimal(self):
        data = {"role": "skill", "cycle_number": 205, "cycle_type": "quiet"}
        assert cycle_post._validate_output(data) == []

    def test_missing_required_fields(self):
        data = {"role": "skill"}
        errors = cycle_post._validate_output(data)
        assert any("cycle_number" in e for e in errors)
        assert any("cycle_type" in e for e in errors)

    def test_invalid_cycle_type(self):
        data = {"role": "skill", "cycle_number": 1, "cycle_type": "banana"}
        errors = cycle_post._validate_output(data)
        assert any("banana" in e for e in errors)

    def test_not_a_dict(self):
        errors = cycle_post._validate_output("not a dict")
        assert len(errors) == 1
        assert "object" in errors[0]

    def test_invalid_transition_structure(self):
        data = {
            "role": "pm", "cycle_number": 1, "cycle_type": "active",
            "status_transitions": [{"number": 123}],  # missing from/to
        }
        errors = cycle_post._validate_output(data)
        assert any("from" in e for e in errors)
        assert any("to" in e for e in errors)

    def test_valid_with_transitions(self):
        data = {
            "role": "pm", "cycle_number": 1, "cycle_type": "active",
            "status_transitions": [
                {"number": 123, "from": "pending-test", "to": "pending-ship"},
            ],
        }
        assert cycle_post._validate_output(data) == []


# ---------------------------------------------------------------------------
# Missing / Invalid Output File
# ---------------------------------------------------------------------------

class TestMissingOutput:
    def test_missing_output_file(self, patch_dirs, capsys):
        """cycle_post exits 0 with warning when no output file exists."""
        result = cycle_post.main.__wrapped__(
        ) if hasattr(cycle_post.main, '__wrapped__') else None
        # Call main with role arg
        with patch("sys.argv", ["cycle_post.py", "skill"]):
            exit_code = cycle_post.main()
        assert exit_code == 0
        err = capsys.readouterr().err
        assert "WARNING" in err or "No cycle-output.json" in err

    def test_invalid_json(self, patch_dirs, squid_dir, capsys):
        """cycle_post exits 1 on malformed JSON."""
        output_path = squid_dir / "pm" / "cycle-output.json"
        output_path.write_text('{"role": "pm", "cycle_number": 459, ', encoding="utf-8")

        with patch("sys.argv", ["cycle_post.py", "pm"]):
            with pytest.raises(SystemExit) as exc:
                cycle_post.main()
            assert exc.value.code == 1
        err = capsys.readouterr().err
        assert "JSON" in err or "json" in err.lower()

    def test_schema_validation_fails(self, patch_dirs, squid_dir, capsys):
        """cycle_post exits 1 on schema-invalid output."""
        _write_output(squid_dir, "pm", {"role": "pm"})  # missing cycle_number, cycle_type

        with patch("sys.argv", ["cycle_post.py", "pm"]):
            with pytest.raises(SystemExit) as exc:
                cycle_post.main()
            assert exc.value.code == 1
        err = capsys.readouterr().err
        assert "cycle_number" in err or "cycle_type" in err


# ---------------------------------------------------------------------------
# Status Transitions
# ---------------------------------------------------------------------------

class TestStatusTransitions:
    def test_calls_tracker_transition(self, monkeypatch):
        calls = []

        def fake_run_script(script, *args, **kwargs):
            calls.append((script, args))
            fake = MagicMock()
            fake.returncode = 0
            fake.stdout = ""
            fake.stderr = ""
            return fake

        monkeypatch.setattr(cycle_post, "_run_script", fake_run_script)

        data = {
            "status_transitions": [
                {"number": 123, "from": "pending-test", "to": "pending-ship"},
            ],
        }
        cycle_post._do_status_transitions(data, "pm")

        # Check tracker.py was called with correct args
        tracker_calls = [c for c in calls if "tracker.py" in c[0]]
        assert len(tracker_calls) == 1
        args = tracker_calls[0][1]
        assert "transition" in args
        assert "123" in args
        assert "pending-test" in args
        assert "pending-ship" in args
        assert "--role" in args
        assert "pm-lead" in args

    def test_skips_invalid_transition(self, monkeypatch, capsys):
        calls = []
        monkeypatch.setattr(cycle_post, "_run_script", lambda *a, **kw: MagicMock(returncode=0, stdout="", stderr=""))

        data = {
            "status_transitions": [
                {"number": 123},  # missing from/to
            ],
        }
        cycle_post._do_status_transitions(data, "pm")
        err = capsys.readouterr().err
        assert "WARNING" in err or "Skipping" in err


# ---------------------------------------------------------------------------
# Iteration Log
# ---------------------------------------------------------------------------

class TestIterationLog:
    def test_creates_active_log(self, monkeypatch):
        calls = []

        def fake_run_script(script, *args, **kwargs):
            calls.append((script, args))
            return MagicMock(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(cycle_post, "_run_script", fake_run_script)

        data = {
            "cycle_number": 459,
            "cycle_type": "active",
            "iteration_summary": "Verified #123",
        }
        cycle_post._do_iteration_log(data, "pm")

        log_calls = [c for c in calls if "log-iteration" in c[1]]
        assert len(log_calls) == 1
        assert "459" in log_calls[0][1]
        assert "--work" in log_calls[0][1]

    def test_creates_quiet_log(self, monkeypatch):
        calls = []

        def fake_run_script(script, *args, **kwargs):
            calls.append((script, args))
            return MagicMock(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(cycle_post, "_run_script", fake_run_script)

        data = {
            "cycle_number": 460,
            "cycle_type": "quiet",
            "iteration_summary": "No work",
        }
        cycle_post._do_iteration_log(data, "pm")

        log_calls = [c for c in calls if "log-iteration" in c[1]]
        assert len(log_calls) == 1
        assert "--quiet" in log_calls[0][1]


# ---------------------------------------------------------------------------
# Restart Sentinel
# ---------------------------------------------------------------------------

class TestRestartSentinel:
    def test_writes_sentinel(self, patch_dirs, squid_dir):
        data = {"restart_needed": True, "restart_reason": "context pressure at 85%"}
        result = cycle_post._do_restart_sentinel(data, "pm")
        assert result is True
        sentinel = squid_dir / "pm" / ".restart"
        assert sentinel.exists()
        assert "context pressure" in sentinel.read_text(encoding="utf-8")

    def test_no_sentinel_when_not_needed(self, patch_dirs, squid_dir):
        data = {"restart_needed": False}
        result = cycle_post._do_restart_sentinel(data, "pm")
        assert result is False
        assert not (squid_dir / "pm" / ".restart").exists()


# ---------------------------------------------------------------------------
# Status Bar
# ---------------------------------------------------------------------------

class TestStatusBar:
    def test_idle_after_cycle(self, patch_dirs, squid_dir):
        cycle_post._write_status_bar("pm", "idle", "")
        state_file = squid_dir / "pm" / "current-state"
        assert state_file.read_text(encoding="utf-8") == "idle|"

    def test_atomic_write(self, patch_dirs, squid_dir):
        """Status bar write should not leave .tmp files."""
        cycle_post._write_status_bar("skill", "implementing", "#2050 — Working...")
        tmp_file = squid_dir / "skill" / "current-state.tmp"
        assert not tmp_file.exists()
        state_file = squid_dir / "skill" / "current-state"
        assert "implementing" in state_file.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# #3433 regression: _do_commit_push uses configured working branch
# ---------------------------------------------------------------------------

class TestCommitPushUsesWorkingBranch:
    def test_skill_branch_workflow_uses_working_branch(self, monkeypatch):
        """Skill branch workflow checks out configured working branch, not 'main'."""
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            r = MagicMock()
            r.returncode = 0
            r.stdout = "squidsquad/skill/3433\n"  # on feature branch
            r.stderr = ""
            return r

        def fake_run_script(script, *args, **kwargs):
            calls.append((script, args))
            return MagicMock(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(cycle_post, "_run", fake_run)
        monkeypatch.setattr(cycle_post, "_run_script", fake_run_script)
        monkeypatch.setattr(cycle_post, "_get_working_branch", lambda: "develop")

        data = {
            "cycle_type": "active",
            "cycle_number": 376,
            "commit_message": "test",
            "config": {"branch_workflow": True},
            "code_commit": {"branch": "squidsquad/skill/3433", "message": "code fix"},
        }
        cycle_post._do_commit_push(data, "skill")

        # Should checkout "develop", not "main"
        checkout_calls = [c for c in calls if isinstance(c, list) and "checkout" in c]
        assert any("develop" in c for c in checkout_calls), f"Expected 'develop' checkout, got: {checkout_calls}"
        assert not any(c == ["git", "checkout", "main"] for c in calls if isinstance(c, list))

    def test_qa_uses_working_branch(self, monkeypatch):
        """QA path checks out configured working branch, not 'main'."""
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            r = MagicMock()
            r.returncode = 0
            r.stdout = "some-other-branch\n"
            r.stderr = ""
            return r

        monkeypatch.setattr(cycle_post, "_run", fake_run)
        monkeypatch.setattr(cycle_post, "_run_script", lambda *a, **kw: MagicMock(returncode=0, stdout="", stderr=""))
        monkeypatch.setattr(cycle_post, "_get_working_branch", lambda: "develop")

        data = {
            "cycle_type": "active",
            "cycle_number": 376,
            "commit_message": "test",
        }
        cycle_post._do_commit_push(data, "qa")

        checkout_calls = [c for c in calls if isinstance(c, list) and "checkout" in c]
        assert any("develop" in c for c in checkout_calls)
        assert not any(c == ["git", "checkout", "main"] for c in calls if isinstance(c, list))


# ---------------------------------------------------------------------------
# Stop-after-cycle sentinel (#3807)
# ---------------------------------------------------------------------------

class TestStopAfterCycleCheck:
    """Regression tests for #3807: universal sentinel-based restart."""

    def test_writes_sentinel_on_context_pressure(self, patch_dirs, squid_dir):
        """cycle_post writes .stop-after-cycle when context pressure exceeded."""
        data = {
            "context_pressure": {"used_pct": 85, "threshold": 70, "exceeded": True},
        }
        result = cycle_post._do_stop_after_cycle_check(data, "skill")
        assert result is True
        sentinel = squid_dir / "skill" / ".stop-after-cycle"
        assert sentinel.exists()
        assert "85%" in sentinel.read_text(encoding="utf-8")

    def test_no_sentinel_below_threshold(self, patch_dirs, squid_dir):
        """No sentinel written when context pressure is below threshold."""
        data = {
            "context_pressure": {"used_pct": 50, "threshold": 70, "exceeded": False},
        }
        result = cycle_post._do_stop_after_cycle_check(data, "skill")
        assert result is False
        sentinel = squid_dir / "skill" / ".stop-after-cycle"
        assert not sentinel.exists()

    def test_detects_external_sentinel(self, patch_dirs, squid_dir):
        """Detects externally written .stop-after-cycle (e.g. start_team.py --reboot)."""
        sentinel = squid_dir / "skill" / ".stop-after-cycle"
        sentinel.write_text("reboot via start_team.py", encoding="utf-8")
        data = {"context_pressure": {"used_pct": 10, "threshold": 70, "exceeded": False}}
        result = cycle_post._do_stop_after_cycle_check(data, "skill")
        assert result is True

    def test_no_context_pressure_data(self, patch_dirs, squid_dir):
        """No crash when context_pressure is missing from data."""
        data = {}
        result = cycle_post._do_stop_after_cycle_check(data, "skill")
        assert result is False

    def test_legacy_restart_sentinel_still_works(self, patch_dirs, squid_dir):
        """Backward compat: restart_needed still writes .restart."""
        data = {"restart_needed": True, "restart_reason": "context pressure at 80%"}
        result = cycle_post._do_restart_sentinel(data, "skill")
        assert result is True
        sentinel = squid_dir / "skill" / ".restart"
        assert sentinel.exists()
