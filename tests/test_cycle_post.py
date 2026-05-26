"""Tests for references/scripts/cycle_post.py — post-cycle mechanical operations."""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import cycle_post
# #9901: cycle_post._write_status_bar now delegates to cycle.status_bar, which
# uses cycle.SQUIDSQUAD_DIR — patching only cycle_post.SQUID_DIR would let
# writes escape to the real repo. Import cycle here so patch_dirs can patch it.
import cycle


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
    """Patch REPO_ROOT and SQUID_DIR to use tmp_path.

    #9901: also patch ``cycle.SQUIDSQUAD_DIR`` because
    ``cycle_post._write_status_bar`` now delegates to ``cycle.status_bar``,
    which reads from ``cycle.SQUIDSQUAD_DIR``. Without this patch, tests
    that exercise status-bar writes pollute the real repo's
    ``.squidsquad/<role>/current-state`` files (DeepSeek finding 1+5).
    """
    monkeypatch.setattr(cycle_post, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(cycle_post, "SQUID_DIR", squid_dir)
    monkeypatch.setattr(cycle, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(cycle, "SQUIDSQUAD_DIR", squid_dir)
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


class TestValidateOutputModeGated:
    """#8918 (UT-10): _validate_output picks REQUIRED_FIELDS by role wake mode.

    Loop mode keeps {role, cycle_number, cycle_type}. Event mode swaps in
    `task` (the task IS the cycle in event mode) so a cycle-output without
    cycle_number but with task passes, and one without either fails clearly.
    """

    def test_event_mode_passes_with_task(self, monkeypatch):
        """UT-10a: event-mode role + task identifier present → validation passes."""
        monkeypatch.setattr(
            cycle_post, "_get_role_wake_mode", lambda r: "event-driven",
        )
        data = {"role": "skill", "task": "100", "cycle_type": "active"}
        assert cycle_post._validate_output(data, "skill") == []

    def test_loop_mode_rejects_missing_cycle_number(self, monkeypatch):
        """UT-10b: loop-mode role without cycle_number → validation fails on it."""
        monkeypatch.setattr(
            cycle_post, "_get_role_wake_mode", lambda r: "polling",
        )
        data = {"role": "skill", "cycle_type": "active"}
        errors = cycle_post._validate_output(data, "skill")
        assert any("cycle_number" in e for e in errors), errors
        # And task is NOT required in loop mode — error list mentions only
        # cycle_number, not task.
        assert not any("task" in e for e in errors), errors

    def test_event_mode_rejects_missing_task(self, monkeypatch):
        """UT-10c: event-mode role with no task identifier → validation fails on it."""
        monkeypatch.setattr(
            cycle_post, "_get_role_wake_mode", lambda r: "event-driven",
        )
        data = {"role": "skill", "cycle_type": "active"}
        errors = cycle_post._validate_output(data, "skill")
        assert any("task" in e for e in errors), errors
        # cycle_number is NOT required in event mode, so it must NOT appear.
        assert not any("cycle_number" in e for e in errors), errors

    def test_default_role_none_uses_loop_required(self):
        """Existing callers that pass no role keep the pre-refactor behavior:
        validate against LOOP_REQUIRED_FIELDS. Preserves backwards compat for
        tests that don't yet thread a role through."""
        data = {"role": "skill", "cycle_type": "active"}
        errors = cycle_post._validate_output(data)
        assert any("cycle_number" in e for e in errors)


class TestAdvanceEventCursorRemoved:
    """#8918 NT-5: _advance_event_cursor is gone from cycle_post.py source."""

    def test_function_attribute_is_absent(self):
        assert not hasattr(cycle_post, "_advance_event_cursor"), (
            "cycle_post.py must not own cursor advancement — event_poll.py "
            "is the sole owner per CONTEXT.md §2"
        )

    def test_source_contains_no_reference(self):
        """Negative grep: even comments mentioning the function are gone so
        nothing in cycle_post.py participates in cursor advancement."""
        from pathlib import Path
        src = Path(cycle_post.__file__).read_text(encoding="utf-8")
        assert "_advance_event_cursor" not in src, (
            "cycle_post.py source still mentions _advance_event_cursor"
        )


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

class TestRestartSentinelRemoved:
    """#8918 (Audit B F2): _do_restart_sentinel deleted. Harness intent API
    (#4966) is the sole restart authority per CONTEXT-4792.md §5.6 and
    DECISIONS-4792.md Q16. The function wrote a `.restart` file that
    contradicted the harness sole-authority principle."""

    def test_function_attribute_is_absent(self):
        assert not hasattr(cycle_post, "_do_restart_sentinel")

    def test_source_contains_no_reference(self):
        from pathlib import Path
        src = Path(cycle_post.__file__).read_text(encoding="utf-8")
        assert "_do_restart_sentinel" not in src


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
    """#4966: API-based intent check replaces .stop-after-cycle sentinel."""

    def test_exits_on_context_pressure(self, patch_dirs, squid_dir):
        """cycle_post returns True when context pressure exceeded (#4966)."""
        data = {
            "context_pressure": {"used_pct": 85, "threshold": 70, "exceeded": True},
        }
        with patch.object(cycle_post, "_query_harness_intent", return_value=None):
            result = cycle_post._do_stop_after_cycle_check(data, "skill")
        assert result is True

    def test_no_exit_below_threshold(self, patch_dirs, squid_dir):
        """No exit when context pressure is below threshold."""
        data = {
            "context_pressure": {"used_pct": 50, "threshold": 70, "exceeded": False},
        }
        with patch.object(cycle_post, "_query_harness_intent", return_value="running"):
            result = cycle_post._do_stop_after_cycle_check(data, "skill")
        assert result is False

    def test_exits_on_harness_intent_stopping(self, patch_dirs, squid_dir):
        """Exits when harness intent is 'stopping' (#4966)."""
        data = {"context_pressure": {"used_pct": 10, "threshold": 70, "exceeded": False}}
        with patch.object(cycle_post, "_query_harness_intent", return_value="stopping"):
            result = cycle_post._do_stop_after_cycle_check(data, "skill")
        assert result is True

    def test_exits_on_harness_intent_restarting(self, patch_dirs, squid_dir):
        """Exits when harness intent is 'restarting' (#4966)."""
        data = {"context_pressure": {"used_pct": 10, "threshold": 70, "exceeded": False}}
        with patch.object(cycle_post, "_query_harness_intent", return_value="restarting"):
            result = cycle_post._do_stop_after_cycle_check(data, "skill")
        assert result is True

    def test_continues_on_harness_unreachable(self, patch_dirs, squid_dir):
        """Safe default: continues when harness API is unreachable (#4966)."""
        data = {"context_pressure": {"used_pct": 10, "threshold": 70, "exceeded": False}}
        with patch.object(cycle_post, "_query_harness_intent", return_value=None):
            result = cycle_post._do_stop_after_cycle_check(data, "skill")
        assert result is False

    def test_no_context_pressure_data(self, patch_dirs, squid_dir):
        """No crash when context_pressure is missing from data."""
        data = {}
        with patch.object(cycle_post, "_query_harness_intent", return_value=None):
            result = cycle_post._do_stop_after_cycle_check(data, "skill")
        assert result is False

    # test_legacy_restart_sentinel_still_works removed in #8918 — the
    # underlying function _do_restart_sentinel was deleted. Harness intent
    # API (#4966) is the sole restart authority.


class TestContextPressureRestartRouting:
    """#4792 Phase 1 / CONTEXT-4792.md §5.1: when context pressure is exceeded,
    cycle_post must POST /agents/{role}/restart BEFORE returning 42 so the
    harness flips intent to RESTARTING (recording intent_set_at for the 60s
    force-kill safety net). Without this routing, a context-pressure exit
    leaves intent=RUNNING and the harness's #4949 auto-reboot path runs
    instead, bypassing the RESTARTING bookkeeping the safety net expects."""

    def test_context_pressure_exceeded_posts_restart(self, patch_dirs,
                                                      squid_dir):
        data = {"context_pressure": {"used_pct": 85, "threshold": 70,
                                      "exceeded": True}}
        with patch.object(cycle_post, "_query_harness_intent",
                          return_value="running"), \
             patch.object(cycle_post, "_post_harness_restart") as post:
            result = cycle_post._do_stop_after_cycle_check(data, "skill")
        assert result is True
        post.assert_called_once_with("skill")

    def test_context_pressure_post_failure_still_returns_true(
        self, patch_dirs, squid_dir,
    ):
        """Best-effort: POST failure must NOT block the exit 42."""
        data = {"context_pressure": {"used_pct": 85, "threshold": 70,
                                      "exceeded": True}}
        with patch.object(cycle_post, "_query_harness_intent",
                          return_value="running"), \
             patch.object(cycle_post, "_post_harness_restart",
                          return_value=False):
            result = cycle_post._do_stop_after_cycle_check(data, "skill")
        assert result is True

    def test_no_double_restart_when_intent_already_restarting(
        self, patch_dirs, squid_dir,
    ):
        """If intent is already STOPPING/RESTARTING the intent branch caught
        it first; this is just a defensive check that the POST is not made
        in that path. The intent branch returns True before evaluating
        context pressure."""
        data = {"context_pressure": {"used_pct": 85, "threshold": 70,
                                      "exceeded": True}}
        with patch.object(cycle_post, "_query_harness_intent",
                          return_value="restarting"), \
             patch.object(cycle_post, "_post_harness_restart") as post:
            result = cycle_post._do_stop_after_cycle_check(data, "skill")
        assert result is True
        # Intent branch short-circuits before reaching the context-pressure
        # path, so no POST is made.
        post.assert_not_called()

    def test_context_pressure_not_exceeded_no_post(self, patch_dirs,
                                                    squid_dir):
        data = {"context_pressure": {"used_pct": 30, "threshold": 70,
                                      "exceeded": False}}
        with patch.object(cycle_post, "_query_harness_intent",
                          return_value="running"), \
             patch.object(cycle_post, "_post_harness_restart") as post:
            result = cycle_post._do_stop_after_cycle_check(data, "skill")
        assert result is False
        post.assert_not_called()


class TestPostHarnessRestart:
    """The _post_harness_restart helper itself."""

    def test_post_returns_false_when_port_unavailable(self, monkeypatch,
                                                       capsys):
        monkeypatch.setattr(cycle_post, "_discover_harness_port",
                             lambda: None)
        assert cycle_post._post_harness_restart("skill") is False

    def test_post_returns_true_on_success(self, monkeypatch):
        monkeypatch.setattr(cycle_post, "_discover_harness_port",
                             lambda: 9999)

        class _Resp:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

        captured = {}

        def _fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            captured["method"] = req.get_method()
            return _Resp()

        monkeypatch.setattr(cycle_post.urllib.request, "urlopen",
                             _fake_urlopen)
        assert cycle_post._post_harness_restart("skill") is True
        assert captured["url"] == "http://127.0.0.1:9999/agents/skill/restart"
        assert captured["method"] == "POST"

    def test_post_returns_false_on_network_error(self, monkeypatch, capsys):
        monkeypatch.setattr(cycle_post, "_discover_harness_port",
                             lambda: 9999)

        def _boom(*args, **kwargs):
            raise OSError("connection refused")

        monkeypatch.setattr(cycle_post.urllib.request, "urlopen", _boom)
        assert cycle_post._post_harness_restart("skill") is False
        # Warning goes to stderr to match the rest of cycle_post.
        assert "WARNING" in capsys.readouterr().err


class TestSelfRestartFragmentMentionsQuit:
    """#4792 Phase 1 / CONTEXT-4792.md §5.11: the self-restart fragment must
    instruct the agent to invoke /quit after cycle_post exits 42."""

    def test_self_restart_md_mentions_quit_after_42(self):
        from pathlib import Path
        path = (Path(__file__).resolve().parent.parent
                / "references" / "sub-skills" / "common" / "self-restart.md")
        text = path.read_text(encoding="utf-8")
        assert "/quit" in text, (
            "self-restart.md must mention `/quit` per CONTEXT-4792.md §5.11"
        )
        assert "exit" in text.lower() and "42" in text, (
            "self-restart.md must reference exit code 42"
        )

    def test_self_restart_md_mentions_force_kill_safety_net(self):
        from pathlib import Path
        path = (Path(__file__).resolve().parent.parent
                / "references" / "sub-skills" / "common" / "self-restart.md")
        text = path.read_text(encoding="utf-8")
        assert "60-second" in text or "60s" in text, (
            "self-restart.md must mention the 60s force-kill window"
        )
        assert "force-kill" in text.lower(), (
            "self-restart.md must mention the force-kill safety net"
        )


class TestPortDiscovery:
    """#4966: Port discovery for harness API communication."""

    def test_reads_port_from_harness_port_file(self, patch_dirs, squid_dir):
        """Reads port from .squidsquad/.harness-port."""
        port_file = squid_dir / ".harness-port"
        port_file.write_text("8080", encoding="utf-8")
        result = cycle_post._discover_harness_port()
        assert result == 8080

    def test_falls_back_to_default_port(self, patch_dirs, squid_dir):
        """Falls back to 7373 when no .harness-port file exists."""
        result = cycle_post._discover_harness_port()
        assert result == 7373

    def test_handles_invalid_port_file(self, patch_dirs, squid_dir):
        """Falls back to default on invalid port file content."""
        port_file = squid_dir / ".harness-port"
        port_file.write_text("not-a-number", encoding="utf-8")
        result = cycle_post._discover_harness_port()
        assert result == 7373


# ---------------------------------------------------------------------------
# #4038 regression: commit message auto-close sanitization
# ---------------------------------------------------------------------------

class TestSanitizeCommitMsg:
    """_sanitize_commit_msg must neutralize GitHub auto-close keywords."""

    def test_fixed_hash_escaped(self):
        result = cycle_post._sanitize_commit_msg("skill: fixed #3465 QA failures")
        assert "fixed #3465" not in result
        assert "#3465" in result  # number still present

    def test_fixes_hash_escaped(self):
        result = cycle_post._sanitize_commit_msg("fixes #123 — typo")
        assert "fixes #123" not in result
        assert "#123" in result

    def test_closes_hash_escaped(self):
        result = cycle_post._sanitize_commit_msg("closes #456")
        assert "closes #456" not in result
        assert "#456" in result

    def test_resolves_hash_escaped(self):
        result = cycle_post._sanitize_commit_msg("Resolved #789 bug")
        assert "Resolved #789" not in result
        assert "#789" in result

    def test_non_keyword_untouched(self):
        result = cycle_post._sanitize_commit_msg("skill: cycle 458 -- implemented #3465")
        assert "implemented #3465" in result

    def test_multiple_refs_all_escaped(self):
        result = cycle_post._sanitize_commit_msg("fixed #100, closes #200")
        assert "fixed #100" not in result
        assert "closes #200" not in result
        assert "#100" in result
        assert "#200" in result

    def test_empty_string(self):
        assert cycle_post._sanitize_commit_msg("") == ""

    def test_no_issue_ref(self):
        msg = "skill: quiet cycle — pipeline clean"
        assert cycle_post._sanitize_commit_msg(msg) == msg

    def test_closes_in_pr_body_escaped(self):
        """#4518: PR body 'Closes #N' must be sanitized to prevent GitHub auto-close."""
        body = "Closes #4459\n\n## Summary\nL4 shared content"
        result = cycle_post._sanitize_commit_msg(body)
        assert "Closes #4459" not in result
        assert "#4459" in result


# ---------------------------------------------------------------------------
# #4081 regression: disposable file detection
# ---------------------------------------------------------------------------

class TestDisposablePatterns:
    """_DISPOSABLE_PATTERNS catches common disposable file names."""

    def test_gen_script_matches(self):
        import fnmatch
        assert any(fnmatch.fnmatch("gen_presets.py", p) for p in cycle_post._DISPOSABLE_PATTERNS)

    def test_scratch_matches(self):
        import fnmatch
        assert any(fnmatch.fnmatch("notes.scratch.py", p) for p in cycle_post._DISPOSABLE_PATTERNS)

    def test_normal_file_does_not_match(self):
        import fnmatch
        assert not any(fnmatch.fnmatch("compose.py", p) for p in cycle_post._DISPOSABLE_PATTERNS)

    def test_test_file_does_not_match(self):
        import fnmatch
        assert not any(fnmatch.fnmatch("test_compose.py", p) for p in cycle_post._DISPOSABLE_PATTERNS)


# ---------------------------------------------------------------------------
# #4125 regression: CHANGELOG skip when DM present
# ---------------------------------------------------------------------------

class TestVersionBumpChangelogSkip:
    """_do_version_bump skips CHANGELOG when DM is present."""

    def test_skips_changelog_when_dm_present(self, patch_dirs, squid_dir):
        """#4125: DM owns CHANGELOG — cycle_post must not write it."""
        # Create DM dir (DM is present)
        (squid_dir / "dm").mkdir(parents=True, exist_ok=True)
        # Create a CHANGELOG
        changelog = patch_dirs / "CHANGELOG.md"
        changelog.write_text("# Changelog\n\nOld content.\n", encoding="utf-8")
        # Create config.md for set_field
        config_md = squid_dir.parent / ".squidsquad" / "config.md"
        config_md.parent.mkdir(parents=True, exist_ok=True)
        config_md.write_text("- **SquidSquad Version**: 0.28.0\n", encoding="utf-8")

        data = {"version_bump": {"new_version": "0.29.0", "items_included": [100, 200]}}
        cycle_post._do_version_bump(data, "pm")

        content = changelog.read_text(encoding="utf-8")
        # CHANGELOG should NOT have been modified (DM handles it)
        assert "0.29.0" not in content
        assert "Old content." in content


# ---------------------------------------------------------------------------
# #8452: _do_version_bump happy path tests
# ---------------------------------------------------------------------------

class TestVersionBumpHappyPath:
    """#8452: Full behavioral coverage for _do_version_bump."""

    def test_no_op_when_no_version_bump(self, monkeypatch):
        """No action when version_bump key is absent or empty."""
        calls = []
        monkeypatch.setattr(cycle_post, "_run_script",
                            lambda *a, **kw: calls.append(a))

        cycle_post._do_version_bump({}, "dm")
        cycle_post._do_version_bump({"version_bump": {}}, "dm")
        cycle_post._do_version_bump({"version_bump": {"new_version": ""}}, "dm")

        assert len(calls) == 0

    def test_calls_config_set_version(self, monkeypatch):
        """config.py set version is called with new version."""
        script_calls = []

        def fake_run_script(script, *args, **kwargs):
            script_calls.append((script, args))
            return MagicMock(returncode=0, stdout="", stderr="")

        def fake_run(cmd, **kwargs):
            r = MagicMock()
            r.returncode = 1  # diff --cached --quiet returns 1 = changes staged
            r.stdout = ""
            r.stderr = ""
            return r

        monkeypatch.setattr(cycle_post, "_run_script", fake_run_script)
        monkeypatch.setattr(cycle_post, "_run", fake_run)
        monkeypatch.setattr(cycle_post, "REPO_ROOT", Path("/fake"))

        data = {"version_bump": {"new_version": "1.2.3"}}
        cycle_post._do_version_bump(data, "dm")

        config_calls = [c for c in script_calls
                        if c[0] == "config.py" and "version" in c[1]]
        assert len(config_calls) >= 1
        assert "1.2.3" in config_calls[0][1]

    def test_updates_skill_md_version(self, monkeypatch, tmp_path):
        """SKILL.md frontmatter version is updated via regex."""
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nname: SquidSquad\nversion: 0.37.0\n---\n# Content\n",
                            encoding="utf-8")

        def fake_run(cmd, **kwargs):
            r = MagicMock()
            r.returncode = 0  # diff --cached --quiet returns 0 = no staged changes
            r.stdout = ""
            r.stderr = ""
            return r

        monkeypatch.setattr(cycle_post, "_run_script",
                            lambda *a, **kw: MagicMock(returncode=0, stdout="", stderr=""))
        monkeypatch.setattr(cycle_post, "_run", fake_run)
        monkeypatch.setattr(cycle_post, "REPO_ROOT", tmp_path)

        data = {"version_bump": {"new_version": "0.38.0"}}
        cycle_post._do_version_bump(data, "dm")

        content = skill_md.read_text(encoding="utf-8")
        assert "version: 0.38.0" in content
        assert "version: 0.37.0" not in content

    def test_staged_diff_guard_skips_empty_commit(self, monkeypatch, capsys):
        """When no staged changes, commit/tag/push is skipped (#5126)."""
        run_calls = []

        def fake_run(cmd, **kwargs):
            run_calls.append(cmd)
            r = MagicMock()
            r.stdout = ""
            r.stderr = ""
            # diff --cached --quiet returns 0 = nothing staged
            r.returncode = 0
            return r

        monkeypatch.setattr(cycle_post, "_run_script",
                            lambda *a, **kw: MagicMock(returncode=0, stdout="", stderr=""))
        monkeypatch.setattr(cycle_post, "_run", fake_run)
        monkeypatch.setattr(cycle_post, "REPO_ROOT", Path("/fake"))

        data = {"version_bump": {"new_version": "2.0.0"}}
        cycle_post._do_version_bump(data, "dm")

        # Should NOT have commit, tag-CREATE, or push calls.
        # Read-only probes (tag -l, ls-remote) are allowed — they fuel the
        # orphaned-tag recovery check (#10241) which is a no-op here because
        # this fake_run never reports a local tag.
        commit_calls = [c for c in run_calls if "commit" in c and "-m" in c]
        tag_create_calls = [c for c in run_calls if c == ["git", "tag", "v2.0.0"]]
        push_calls = [c for c in run_calls if c == ["git", "push"]]
        assert len(commit_calls) == 0
        assert len(tag_create_calls) == 0
        assert len(push_calls) == 0

        captured = capsys.readouterr()
        assert "skipping commit/tag/push" in captured.out.lower()

    def test_commit_tag_push_sequence(self, monkeypatch):
        """Full commit/tag/push sequence runs when changes are staged."""
        run_calls = []

        def fake_run(cmd, **kwargs):
            run_calls.append(cmd)
            r = MagicMock()
            r.stdout = ""
            r.stderr = ""
            if cmd == ["git", "diff", "--cached", "--quiet"]:
                r.returncode = 1  # changes staged
            elif cmd == ["git", "tag", "-l", "v1.0.0"]:
                r.stdout = ""  # tag doesn't exist
                r.returncode = 0
            else:
                r.returncode = 0
            return r

        monkeypatch.setattr(cycle_post, "_run_script",
                            lambda *a, **kw: MagicMock(returncode=0, stdout="", stderr=""))
        monkeypatch.setattr(cycle_post, "_run", fake_run)
        monkeypatch.setattr(cycle_post, "REPO_ROOT", Path("/fake"))

        data = {"version_bump": {"new_version": "1.0.0"}}
        cycle_post._do_version_bump(data, "dm")

        # Verify commit
        commit_calls = [c for c in run_calls
                        if len(c) >= 3 and c[0] == "git" and c[1] == "commit"]
        assert len(commit_calls) == 1
        assert "v1.0.0" in commit_calls[0][-1]

        # Verify tag created
        tag_create_calls = [c for c in run_calls
                           if c == ["git", "tag", "v1.0.0"]]
        assert len(tag_create_calls) == 1

        # Verify push + push --tags
        assert ["git", "push"] in run_calls
        assert ["git", "push", "--tags"] in run_calls

    def test_skips_tag_when_already_exists(self, monkeypatch):
        """Tag creation is skipped when tag already exists."""
        run_calls = []

        def fake_run(cmd, **kwargs):
            run_calls.append(cmd)
            r = MagicMock()
            r.stdout = ""
            r.stderr = ""
            if cmd == ["git", "diff", "--cached", "--quiet"]:
                r.returncode = 1  # changes staged
            elif cmd == ["git", "tag", "-l", "v2.0.0"]:
                r.stdout = "v2.0.0\n"  # tag exists
                r.returncode = 0
            else:
                r.returncode = 0
            return r

        monkeypatch.setattr(cycle_post, "_run_script",
                            lambda *a, **kw: MagicMock(returncode=0, stdout="", stderr=""))
        monkeypatch.setattr(cycle_post, "_run", fake_run)
        monkeypatch.setattr(cycle_post, "REPO_ROOT", Path("/fake"))

        data = {"version_bump": {"new_version": "2.0.0"}}
        cycle_post._do_version_bump(data, "dm")

        # Tag create should NOT be called
        tag_create_calls = [c for c in run_calls
                           if c == ["git", "tag", "v2.0.0"]]
        assert len(tag_create_calls) == 0

    def test_resets_shipped_since_bump_counter(self, monkeypatch):
        """After bump, shipped-since-bump counter is reset to 0."""
        script_calls = []

        def fake_run_script(script, *args, **kwargs):
            script_calls.append((script, args))
            return MagicMock(returncode=0, stdout="", stderr="")

        def fake_run(cmd, **kwargs):
            r = MagicMock()
            r.stdout = ""
            r.stderr = ""
            if cmd == ["git", "diff", "--cached", "--quiet"]:
                r.returncode = 1
            elif "tag" in cmd and "-l" in cmd:
                r.stdout = ""
                r.returncode = 0
            else:
                r.returncode = 0
            return r

        monkeypatch.setattr(cycle_post, "_run_script", fake_run_script)
        monkeypatch.setattr(cycle_post, "_run", fake_run)
        monkeypatch.setattr(cycle_post, "REPO_ROOT", Path("/fake"))

        data = {"version_bump": {"new_version": "3.0.0"}}
        cycle_post._do_version_bump(data, "dm")

        # Verify shipped-since-bump reset
        reset_calls = [c for c in script_calls
                       if c[0] == "config.py" and "shipped-since-bump" in c[1]]
        assert len(reset_calls) == 1
        assert "0" in reset_calls[0][1]

    def test_stages_only_bump_files(self, monkeypatch):
        """Only version-bump files are staged, not git add -A (#3494)."""
        run_calls = []

        def fake_run(cmd, **kwargs):
            run_calls.append(cmd)
            r = MagicMock()
            r.stdout = ""
            r.stderr = ""
            r.returncode = 0 if cmd != ["git", "diff", "--cached", "--quiet"] else 1
            return r

        monkeypatch.setattr(cycle_post, "_run_script",
                            lambda *a, **kw: MagicMock(returncode=0, stdout="", stderr=""))
        monkeypatch.setattr(cycle_post, "_run", fake_run)
        monkeypatch.setattr(cycle_post, "REPO_ROOT", Path("/fake"))

        data = {"version_bump": {"new_version": "4.0.0"}}
        cycle_post._do_version_bump(data, "dm")

        # Find git add calls
        add_calls = [c for c in run_calls if c[0] == "git" and c[1] == "add"]
        assert len(add_calls) == 1
        staged_files = add_calls[0][3:]  # after ["git", "add", "--"]
        assert ".squidsquad/config.md" in staged_files
        assert "CHANGELOG.md" in staged_files
        # No -A flag
        assert "-A" not in add_calls[0]


# ---------------------------------------------------------------------------
# #10002: _do_version_bump must surface push/commit/tag failures and refuse
# to reset shipped-since-bump or print the success line when any step fails.
# ---------------------------------------------------------------------------

class TestVersionBumpPushFailure:
    """#10002: any non-zero result from commit / tag-create / push / push --tags
    must (a) emit a clear ERROR to stderr, (b) skip the shipped-since-bump
    reset, and (c) skip the success print. Otherwise DM-side state claims the
    bump shipped while no v<NEW> tag exists on origin."""

    def _fake_run_factory(self, failing_cmd, run_calls):
        """Returns a fake _run that fails (rc=1, stderr filled) when the
        supplied command matches exactly; success otherwise. Exact-match
        (not prefix-match) avoids false-positives where ['git', 'push']
        would also match ['git', 'push', '--tags']. The diff guard always
        returns rc=1 (staged changes present) so the commit path runs."""
        def fake_run(cmd, **kwargs):
            run_calls.append(cmd)
            r = MagicMock()
            r.stdout = ""
            r.stderr = ""
            if cmd == ["git", "diff", "--cached", "--quiet"]:
                r.returncode = 1
            elif "tag" in cmd and "-l" in cmd:
                r.stdout = ""  # tag doesn't exist yet
                r.returncode = 0
            elif failing_cmd is not None and cmd == failing_cmd:
                r.returncode = 1
                r.stderr = "fatal: simulated failure"
            else:
                r.returncode = 0
            return r
        return fake_run

    def test_push_failure_skips_counter_reset(self, monkeypatch, capsys):
        """`git push` fails -> shipped-since-bump NOT reset."""
        script_calls = []
        run_calls = []

        def fake_run_script(script, *args, **kwargs):
            script_calls.append((script, args))
            return MagicMock(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(cycle_post, "_run_script", fake_run_script)
        monkeypatch.setattr(cycle_post, "_run",
                            self._fake_run_factory(["git", "push"], run_calls))
        monkeypatch.setattr(cycle_post, "REPO_ROOT", Path("/fake"))

        data = {"version_bump": {"new_version": "5.0.0"}}
        cycle_post._do_version_bump(data, "dm")

        reset_calls = [c for c in script_calls
                       if c[0] == "config.py" and "shipped-since-bump" in c[1]]
        assert reset_calls == [], (
            "shipped-since-bump must NOT be reset when git push fails"
        )

        captured = capsys.readouterr()
        assert "ERROR" in captured.err
        assert "push" in captured.err.lower()
        assert "v5.0.0" in captured.err
        assert "tagged and pushed" not in captured.out

    def test_push_tags_failure_skips_counter_reset(self, monkeypatch, capsys):
        """`git push --tags` fails -> shipped-since-bump NOT reset."""
        script_calls = []
        run_calls = []

        def fake_run_script(script, *args, **kwargs):
            script_calls.append((script, args))
            return MagicMock(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(cycle_post, "_run_script", fake_run_script)
        monkeypatch.setattr(cycle_post, "_run",
                            self._fake_run_factory(["git", "push", "--tags"], run_calls))
        monkeypatch.setattr(cycle_post, "REPO_ROOT", Path("/fake"))

        data = {"version_bump": {"new_version": "5.1.0"}}
        cycle_post._do_version_bump(data, "dm")

        reset_calls = [c for c in script_calls
                       if c[0] == "config.py" and "shipped-since-bump" in c[1]]
        assert reset_calls == [], (
            "shipped-since-bump must NOT be reset when git push --tags fails"
        )

        captured = capsys.readouterr()
        assert "ERROR" in captured.err
        assert "tags" in captured.err.lower()
        assert "tagged and pushed" not in captured.out

    def test_commit_failure_skips_everything_downstream(self, monkeypatch, capsys):
        """`git commit` fails -> no tag, no push, no counter reset."""
        script_calls = []
        run_calls = []

        def fake_run_script(script, *args, **kwargs):
            script_calls.append((script, args))
            return MagicMock(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(cycle_post, "_run_script", fake_run_script)
        monkeypatch.setattr(cycle_post, "_run",
                            self._fake_run_factory(
                                ["git", "commit", "-m", "chore: bump version to v5.2.0"],
                                run_calls))
        monkeypatch.setattr(cycle_post, "REPO_ROOT", Path("/fake"))

        data = {"version_bump": {"new_version": "5.2.0"}}
        cycle_post._do_version_bump(data, "dm")

        # No tag-create, no push, no push --tags after commit failure
        assert ["git", "tag", "v5.2.0"] not in run_calls
        assert ["git", "push"] not in run_calls
        assert ["git", "push", "--tags"] not in run_calls
        reset_calls = [c for c in script_calls
                       if c[0] == "config.py" and "shipped-since-bump" in c[1]]
        assert reset_calls == []

        captured = capsys.readouterr()
        assert "ERROR" in captured.err
        assert "commit" in captured.err.lower()

    def test_tag_list_failure_aborts_bump(self, monkeypatch, capsys):
        """`git tag -l` itself fails (rc != 0) -> abort before tag-create
        or push; counter NOT reset. Pairs with the returncode check added
        to the `git tag -l` call so a listing failure cannot mask an
        already-existing tag and produce a misleading downstream error."""
        script_calls = []
        run_calls = []

        def fake_run_script(script, *args, **kwargs):
            script_calls.append((script, args))
            return MagicMock(returncode=0, stdout="", stderr="")

        def fake_run(cmd, **kwargs):
            run_calls.append(cmd)
            r = MagicMock()
            r.stdout = ""
            r.stderr = ""
            if cmd == ["git", "diff", "--cached", "--quiet"]:
                r.returncode = 1
            elif cmd == ["git", "tag", "-l", "v5.4.0"]:
                r.returncode = 1
                r.stderr = "fatal: simulated tag-list failure"
            else:
                r.returncode = 0
            return r

        monkeypatch.setattr(cycle_post, "_run_script", fake_run_script)
        monkeypatch.setattr(cycle_post, "_run", fake_run)
        monkeypatch.setattr(cycle_post, "REPO_ROOT", Path("/fake"))

        data = {"version_bump": {"new_version": "5.4.0"}}
        cycle_post._do_version_bump(data, "dm")

        assert ["git", "tag", "v5.4.0"] not in run_calls
        assert ["git", "push"] not in run_calls
        assert ["git", "push", "--tags"] not in run_calls
        reset_calls = [c for c in script_calls
                       if c[0] == "config.py" and "shipped-since-bump" in c[1]]
        assert reset_calls == []

        captured = capsys.readouterr()
        assert "ERROR" in captured.err
        assert "tag -l" in captured.err

    def test_tag_create_failure_skips_push_and_counter(self, monkeypatch, capsys):
        """`git tag v<NEW>` fails -> push not attempted, counter not reset."""
        script_calls = []
        run_calls = []

        def fake_run_script(script, *args, **kwargs):
            script_calls.append((script, args))
            return MagicMock(returncode=0, stdout="", stderr="")

        # Custom: tag-create fails (not the tag-check -l variant)
        def fake_run(cmd, **kwargs):
            run_calls.append(cmd)
            r = MagicMock()
            r.stdout = ""
            r.stderr = ""
            if cmd == ["git", "diff", "--cached", "--quiet"]:
                r.returncode = 1
            elif cmd == ["git", "tag", "-l", "v5.3.0"]:
                r.stdout = ""
                r.returncode = 0
            elif cmd == ["git", "tag", "v5.3.0"]:
                r.returncode = 1
                r.stderr = "fatal: simulated tag failure"
            else:
                r.returncode = 0
            return r

        monkeypatch.setattr(cycle_post, "_run_script", fake_run_script)
        monkeypatch.setattr(cycle_post, "_run", fake_run)
        monkeypatch.setattr(cycle_post, "REPO_ROOT", Path("/fake"))

        data = {"version_bump": {"new_version": "5.3.0"}}
        cycle_post._do_version_bump(data, "dm")

        assert ["git", "push"] not in run_calls
        assert ["git", "push", "--tags"] not in run_calls
        reset_calls = [c for c in script_calls
                       if c[0] == "config.py" and "shipped-since-bump" in c[1]]
        assert reset_calls == []

        captured = capsys.readouterr()
        assert "ERROR" in captured.err
        assert "tag" in captured.err.lower()


# ---------------------------------------------------------------------------
# #10241: orphaned-tag self-healing recovery — when the diff guard would
# otherwise short-circuit, check whether a prior bump landed locally but
# never reached origin, and push the tag if so.
# ---------------------------------------------------------------------------

class TestOrphanedTagRecovery:
    """#10241: _do_version_bump must self-heal a half-completed prior bump.

    Setup pattern for these tests: ``git diff --cached --quiet`` returns 0
    (no staged changes — config.md already at target version, the post-#10002
    blocker scenario). The recovery helper then probes local + remote for the
    tag and pushes if asymmetric."""

    def _build_fake_run(self, run_calls, local_has_tag, remote_has_tag,
                       push_succeeds=True, ls_remote_succeeds=True,
                       tag_l_succeeds=True):
        """Returns a fake _run that simulates the post-#10002 stall state.

        diff --cached --quiet returns 0 (no staged changes). tag -l returns
        the tag name iff local_has_tag. ls-remote returns a ref line iff
        remote_has_tag. push origin <tag> succeeds iff push_succeeds."""
        def fake_run(cmd, **kwargs):
            run_calls.append(cmd)
            r = MagicMock()
            r.stdout = ""
            r.stderr = ""
            r.returncode = 0
            if cmd == ["git", "diff", "--cached", "--quiet"]:
                r.returncode = 0  # nothing staged
            elif "tag" in cmd and "-l" in cmd:
                if not tag_l_succeeds:
                    r.returncode = 1
                    r.stderr = "fatal: simulated tag -l failure"
                elif local_has_tag:
                    r.stdout = cmd[-1] + "\n"
            elif cmd[:3] == ["git", "ls-remote", "--tags"]:
                if not ls_remote_succeeds:
                    r.returncode = 1
                    r.stderr = "fatal: simulated ls-remote failure"
                elif remote_has_tag:
                    r.stdout = f"deadbeefdeadbeefdeadbeefdeadbeefdeadbeef\t{cmd[-1]}\n"
            elif cmd[:3] == ["git", "push", "origin"]:
                if not push_succeeds:
                    r.returncode = 1
                    r.stderr = "fatal: simulated recovery push failure"
            return r
        return fake_run

    def _build_run_script(self, script_calls):
        def fake_run_script(script, *args, **kwargs):
            script_calls.append((script, args))
            return MagicMock(returncode=0, stdout="", stderr="")
        return fake_run_script

    def test_recovers_when_local_has_tag_remote_does_not(self, monkeypatch, capsys):
        """Local v6.0.0 exists, origin does not → push it, reset counter."""
        script_calls = []
        run_calls = []
        monkeypatch.setattr(cycle_post, "_run_script",
                            self._build_run_script(script_calls))
        monkeypatch.setattr(cycle_post, "_run",
                            self._build_fake_run(run_calls,
                                                  local_has_tag=True,
                                                  remote_has_tag=False))
        monkeypatch.setattr(cycle_post, "REPO_ROOT", Path("/fake"))

        cycle_post._do_version_bump(
            {"version_bump": {"new_version": "6.0.0"}}, "dm",
        )

        # Recovery push attempted with the tag-specific form (not push --tags)
        assert ["git", "push", "origin", "v6.0.0"] in run_calls
        # Counter was reset (bump is now fully complete)
        reset_calls = [c for c in script_calls
                       if c[0] == "config.py" and "shipped-since-bump" in c[1]]
        assert len(reset_calls) == 1

        captured = capsys.readouterr()
        assert "Recovered orphaned tag v6.0.0" in captured.out
        assert "skipping commit/tag/push" not in captured.out

    def test_no_recovery_when_local_tag_missing(self, monkeypatch, capsys):
        """No local tag → nothing to recover; fall through to skip message."""
        script_calls = []
        run_calls = []
        monkeypatch.setattr(cycle_post, "_run_script",
                            self._build_run_script(script_calls))
        monkeypatch.setattr(cycle_post, "_run",
                            self._build_fake_run(run_calls,
                                                  local_has_tag=False,
                                                  remote_has_tag=False))
        monkeypatch.setattr(cycle_post, "REPO_ROOT", Path("/fake"))

        cycle_post._do_version_bump(
            {"version_bump": {"new_version": "6.1.0"}}, "dm",
        )

        # No push attempted
        assert not any(c[:3] == ["git", "push", "origin"] for c in run_calls)
        # No counter reset
        reset_calls = [c for c in script_calls
                       if c[0] == "config.py" and "shipped-since-bump" in c[1]]
        assert reset_calls == []

        captured = capsys.readouterr()
        assert "skipping commit/tag/push" in captured.out

    def test_no_recovery_when_remote_already_has_tag(self, monkeypatch, capsys):
        """Both have the tag → bump is fully done; fall through to skip."""
        script_calls = []
        run_calls = []
        monkeypatch.setattr(cycle_post, "_run_script",
                            self._build_run_script(script_calls))
        monkeypatch.setattr(cycle_post, "_run",
                            self._build_fake_run(run_calls,
                                                  local_has_tag=True,
                                                  remote_has_tag=True))
        monkeypatch.setattr(cycle_post, "REPO_ROOT", Path("/fake"))

        cycle_post._do_version_bump(
            {"version_bump": {"new_version": "6.2.0"}}, "dm",
        )

        assert not any(c[:3] == ["git", "push", "origin"] for c in run_calls)
        reset_calls = [c for c in script_calls
                       if c[0] == "config.py" and "shipped-since-bump" in c[1]]
        assert reset_calls == []

        captured = capsys.readouterr()
        assert "skipping commit/tag/push" in captured.out

    def test_recovery_push_failure_skips_counter_reset(self, monkeypatch, capsys):
        """Local-yes / origin-no but `git push origin v<NEW>` fails →
        recovery attempted, ERROR surfaced, counter NOT reset (next
        cycle will retry)."""
        script_calls = []
        run_calls = []
        monkeypatch.setattr(cycle_post, "_run_script",
                            self._build_run_script(script_calls))
        monkeypatch.setattr(cycle_post, "_run",
                            self._build_fake_run(run_calls,
                                                  local_has_tag=True,
                                                  remote_has_tag=False,
                                                  push_succeeds=False))
        monkeypatch.setattr(cycle_post, "REPO_ROOT", Path("/fake"))

        cycle_post._do_version_bump(
            {"version_bump": {"new_version": "6.3.0"}}, "dm",
        )

        assert ["git", "push", "origin", "v6.3.0"] in run_calls
        reset_calls = [c for c in script_calls
                       if c[0] == "config.py" and "shipped-since-bump" in c[1]]
        assert reset_calls == []

        captured = capsys.readouterr()
        assert "ERROR" in captured.err
        assert "recovery push failed" in captured.err
        assert "v6.3.0" in captured.err
        assert "skipping commit/tag/push" in captured.out

    def test_ls_remote_failure_aborts_recovery_safely(self, monkeypatch, capsys):
        """ls-remote network/auth failure → leave state untouched (no
        push attempted, no counter reset, fall through to skip message)."""
        script_calls = []
        run_calls = []
        monkeypatch.setattr(cycle_post, "_run_script",
                            self._build_run_script(script_calls))
        monkeypatch.setattr(cycle_post, "_run",
                            self._build_fake_run(run_calls,
                                                  local_has_tag=True,
                                                  remote_has_tag=False,
                                                  ls_remote_succeeds=False))
        monkeypatch.setattr(cycle_post, "REPO_ROOT", Path("/fake"))

        cycle_post._do_version_bump(
            {"version_bump": {"new_version": "6.4.0"}}, "dm",
        )

        assert not any(c[:3] == ["git", "push", "origin"] for c in run_calls)
        reset_calls = [c for c in script_calls
                       if c[0] == "config.py" and "shipped-since-bump" in c[1]]
        assert reset_calls == []

        captured = capsys.readouterr()
        assert "skipping commit/tag/push" in captured.out

    def test_tag_l_failure_aborts_recovery_safely(self, monkeypatch, capsys):
        """`git tag -l` itself failing inside the recovery probe → no
        ls-remote attempted, no push attempted, no counter reset, fall
        through to skip message. Closes the dead-parameter coverage gap."""
        script_calls = []
        run_calls = []
        monkeypatch.setattr(cycle_post, "_run_script",
                            self._build_run_script(script_calls))
        monkeypatch.setattr(cycle_post, "_run",
                            self._build_fake_run(run_calls,
                                                  local_has_tag=True,
                                                  remote_has_tag=False,
                                                  tag_l_succeeds=False))
        monkeypatch.setattr(cycle_post, "REPO_ROOT", Path("/fake"))

        cycle_post._do_version_bump(
            {"version_bump": {"new_version": "6.5.0"}}, "dm",
        )

        assert not any(c[:3] == ["git", "ls-remote", "--tags"] for c in run_calls)
        assert not any(c[:3] == ["git", "push", "origin"] for c in run_calls)
        reset_calls = [c for c in script_calls
                       if c[0] == "config.py" and "shipped-since-bump" in c[1]]
        assert reset_calls == []

        captured = capsys.readouterr()
        assert "skipping commit/tag/push" in captured.out


# ---------------------------------------------------------------------------
# Branch push fallback — regression #4837
# ---------------------------------------------------------------------------

class TestBranchPushFallback:
    """Regression #4837: cycle_post must push feature branches even when
    commit-code reports nothing to commit (code already committed by agent)."""

    def test_pushes_branch_when_commit_code_fails(self, monkeypatch):
        """When commit-code returns non-zero but branch exists, push the branch."""
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            r = MagicMock()
            r.returncode = 0
            r.stdout = "main\n"
            r.stderr = ""
            return r

        def fake_run_script(script, *args, **kwargs):
            calls.append((script, args))
            r = MagicMock()
            r.stderr = ""
            r.stdout = ""
            r.returncode = 0
            # commit-code fails (nothing to commit — code already committed)
            if args and "commit-code" in args:
                r.returncode = 1
                r.stderr = "Nothing to commit"
            return r

        monkeypatch.setattr(cycle_post, "_run", fake_run)
        monkeypatch.setattr(cycle_post, "_run_script", fake_run_script)
        monkeypatch.setattr(cycle_post, "_get_working_branch", lambda: "main")

        data = {
            "cycle_type": "active",
            "cycle_number": 590,
            "commit_message": "test",
            "config": {"branch_workflow": True},
            "code_commit": {
                "branch": "squidsquad/skill/4803",
                "message": "fix multi-role query",
            },
        }
        cycle_post._do_commit_push(data, "skill")

        # Verify push was called with the feature branch
        push_calls = [c for c in calls
                      if isinstance(c, list) and "push" in c
                      and "squidsquad/skill/4803" in c]
        assert len(push_calls) >= 1, (
            f"Expected push of squidsquad/skill/4803, got calls: "
            f"{[c for c in calls if isinstance(c, list)]}"
        )

    def test_creates_pr_on_feature_branch(self, monkeypatch):
        """PR creation checks out the feature branch before calling gh pr create."""
        calls = []
        checkout_targets = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            r = MagicMock()
            r.returncode = 0
            r.stdout = "main\n"
            r.stderr = ""
            if isinstance(cmd, list) and "checkout" in cmd:
                checkout_targets.append(cmd[-1])
            return r

        def fake_run_script(script, *args, **kwargs):
            calls.append((script, args))
            r = MagicMock()
            r.stderr = ""
            r.stdout = ""
            r.returncode = 0
            # commit-code fails (code already committed)
            if args and "commit-code" in args:
                r.returncode = 1
                r.stderr = "Nothing to commit"
            elif args and "pr-create" in args:
                r.returncode = 0
                r.stdout = "https://github.com/org/repo/pull/42"
            return r

        monkeypatch.setattr(cycle_post, "_run", fake_run)
        monkeypatch.setattr(cycle_post, "_run_script", fake_run_script)
        monkeypatch.setattr(cycle_post, "_get_working_branch", lambda: "main")

        data = {
            "cycle_type": "active",
            "cycle_number": 590,
            "commit_message": "test",
            "config": {"branch_workflow": True},
            "code_commit": {
                "branch": "squidsquad/skill/4803",
                "message": "fix",
                "pr_needed": True,
                "pr_title": "skill: #4803",
                "pr_body": "Fixes #4803",
            },
        }
        cycle_post._do_commit_push(data, "skill")

        # Verify feature branch was checked out before pr-create
        assert "squidsquad/skill/4803" in checkout_targets, (
            f"Expected checkout of feature branch before PR creation, "
            f"got checkouts: {checkout_targets}"
        )
        # Verify pr-create was called
        pr_calls = [c for c in calls
                    if isinstance(c, tuple) and any("pr-create" in str(a) for a in c)]
        assert len(pr_calls) == 1, f"Expected pr-create call, got: {calls}"


# ---------------------------------------------------------------------------
# _verify_remote_branch — #5444, #5526
# ---------------------------------------------------------------------------

class TestVerifyRemoteBranch:
    """#5526: _verify_remote_branch must resolve {role} placeholder correctly."""

    def test_resolves_role_placeholder(self, monkeypatch):
        """When branch-pattern has {role}, it resolves to actual role name."""
        with patch.dict("sys.modules", {"config": MagicMock()}), \
             patch("config.get_field", side_effect=lambda f: {
                 "branch-workflow": "yes",
                 "branch-pattern": "squidsquad/{role}/{number}",
             }.get(f, "")):

            def fake_run(cmd, **kwargs):
                r = MagicMock()
                r.returncode = 0
                r.stdout = "abc123\trefs/heads/squidsquad/skill/100\n"
                r.stderr = ""
                return r

            monkeypatch.setattr(cycle_post, "_run", fake_run)
            result = cycle_post._verify_remote_branch(100, role="skill")
            assert result is True

    def test_no_wildcard_in_branch_name(self, monkeypatch):
        """Branch name must not contain '*' — use actual role name (#5526)."""
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            r = MagicMock()
            r.returncode = 0
            r.stdout = ""
            r.stderr = ""
            return r

        monkeypatch.setattr(cycle_post, "_run", fake_run)

        with patch.dict("sys.modules", {"config": MagicMock()}), \
             patch("config.get_field", side_effect=lambda f: {
                 "branch-workflow": "yes",
                 "branch-pattern": "squidsquad/{role}/{number}",
             }.get(f, "")):
            cycle_post._verify_remote_branch(100, role="skill")

        ls_remote_cmd = calls[0]
        assert "squidsquad/skill/100" in str(ls_remote_cmd)
        assert "*" not in str(ls_remote_cmd)

    def test_returns_none_on_network_failure(self, monkeypatch):
        def fake_run(cmd, **kwargs):
            r = MagicMock()
            r.returncode = 1
            r.stdout = ""
            r.stderr = "fatal: unable to access"
            return r

        monkeypatch.setattr(cycle_post, "_run", fake_run)

        with patch.dict("sys.modules", {"config": MagicMock()}), \
             patch("config.get_field", side_effect=lambda f: {
                 "branch-workflow": "yes",
                 "branch-pattern": "squidsquad/task/{number}",
             }.get(f, "")):
            assert cycle_post._verify_remote_branch(100) is None


# TestAdvanceEventCursorInsertion removed in #8918. cycle_post no longer
# advances the event cursor — event_poll.py is the sole owner per
# CONTEXT.md §2 "per-event atomic advancement." The new
# TestAdvanceEventCursorRemoved class above asserts the function and its
# source references are gone.


# ---------------------------------------------------------------------------
# _do_tracker_comments (#7955)
# ---------------------------------------------------------------------------

class TestDoTrackerComments:
    """Tests for _do_tracker_comments — posts comments via tracker.py."""

    def test_posts_valid_comments(self, monkeypatch):
        """Each comment in tracker_comments is posted via _run_script."""
        calls = []

        def fake_run_script(script, *args, **kwargs):
            calls.append((script, list(args)))
            return MagicMock(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(cycle_post, "_run_script", fake_run_script)

        data = {
            "tracker_comments": [
                {"number": 100, "message": "Picking up."},
                {"number": 200, "message": "Fixed."},
            ]
        }
        cycle_post._do_tracker_comments(data, "skill")

        assert len(calls) == 2
        assert calls[0] == ("tracker.py", ["comment", "100", "--role", "skill-lead", "--message", "Picking up."])
        assert calls[1] == ("tracker.py", ["comment", "200", "--role", "skill-lead", "--message", "Fixed."])

    def test_empty_comments_list(self, monkeypatch):
        """Empty tracker_comments list results in zero _run_script calls."""
        calls = []
        monkeypatch.setattr(cycle_post, "_run_script", lambda *a, **kw: calls.append(1) or MagicMock(returncode=0))

        cycle_post._do_tracker_comments({"tracker_comments": []}, "skill")
        assert len(calls) == 0

    def test_missing_tracker_comments_key(self, monkeypatch):
        """Missing tracker_comments key is treated as empty list."""
        calls = []
        monkeypatch.setattr(cycle_post, "_run_script", lambda *a, **kw: calls.append(1) or MagicMock(returncode=0))

        cycle_post._do_tracker_comments({}, "pm")
        assert len(calls) == 0

    def test_skips_comment_without_number(self, monkeypatch):
        """Comments missing 'number' are skipped."""
        calls = []
        monkeypatch.setattr(cycle_post, "_run_script", lambda *a, **kw: calls.append(1) or MagicMock(returncode=0))

        data = {"tracker_comments": [{"message": "orphaned comment"}]}
        cycle_post._do_tracker_comments(data, "skill")
        assert len(calls) == 0

    def test_skips_comment_without_message(self, monkeypatch):
        """Comments missing 'message' are skipped."""
        calls = []
        monkeypatch.setattr(cycle_post, "_run_script", lambda *a, **kw: calls.append(1) or MagicMock(returncode=0))

        data = {"tracker_comments": [{"number": 100}]}
        cycle_post._do_tracker_comments(data, "skill")
        assert len(calls) == 0

    def test_continues_on_failure(self, monkeypatch, capsys):
        """A failed comment does not stop subsequent comments."""
        calls = []

        def fake_run_script(script, *args, **kwargs):
            calls.append(list(args))
            if len(calls) == 1:
                return MagicMock(returncode=1, stderr="network error")
            return MagicMock(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(cycle_post, "_run_script", fake_run_script)

        data = {
            "tracker_comments": [
                {"number": 100, "message": "First"},
                {"number": 200, "message": "Second"},
            ]
        }
        cycle_post._do_tracker_comments(data, "qa")
        assert len(calls) == 2  # Both attempted despite first failure

    def test_role_suffix(self, monkeypatch):
        """Role label is constructed as '{role}-lead'."""
        calls = []

        def fake_run_script(script, *args, **kwargs):
            calls.append(list(args))
            return MagicMock(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(cycle_post, "_run_script", fake_run_script)

        cycle_post._do_tracker_comments(
            {"tracker_comments": [{"number": 42, "message": "test"}]}, "pm"
        )
        assert "--role" in calls[0]
        role_idx = calls[0].index("--role")
        assert calls[0][role_idx + 1] == "pm-lead"


# ---------------------------------------------------------------------------
# _do_working_state_update (#7955)
# ---------------------------------------------------------------------------

class TestDoWorkingStateUpdate:
    """Tests for _do_working_state_update — writes working-state.md."""

    def test_writes_update_content(self, squid_dir, patch_dirs, monkeypatch):
        """Non-empty update is written to working-state.md."""
        monkeypatch.setattr(cycle_post, "_state_path", lambda rel: squid_dir / rel)

        update_text = "# Working State\n\n- **Task**: #42\n- **Status**: in-progress\n"
        cycle_post._do_working_state_update({"working_state_update": update_text}, "skill")

        ws = squid_dir / "skill" / "working-state.md"
        assert ws.exists()
        assert ws.read_text(encoding="utf-8") == update_text

    def test_none_update_is_noop(self, squid_dir, patch_dirs, monkeypatch):
        """None working_state_update does not write or create file."""
        monkeypatch.setattr(cycle_post, "_state_path", lambda rel: squid_dir / rel)
        ws = squid_dir / "skill" / "working-state.md"

        cycle_post._do_working_state_update({"working_state_update": None}, "skill")
        assert not ws.exists()

    def test_missing_key_is_noop(self, squid_dir, patch_dirs, monkeypatch):
        """Missing working_state_update key does not write or create file."""
        monkeypatch.setattr(cycle_post, "_state_path", lambda rel: squid_dir / rel)
        ws = squid_dir / "skill" / "working-state.md"

        cycle_post._do_working_state_update({}, "skill")
        assert not ws.exists()

    def test_empty_string_is_noop(self, squid_dir, patch_dirs, monkeypatch):
        """Empty string working_state_update is treated as falsy — no write."""
        monkeypatch.setattr(cycle_post, "_state_path", lambda rel: squid_dir / rel)
        ws = squid_dir / "skill" / "working-state.md"

        cycle_post._do_working_state_update({"working_state_update": ""}, "skill")
        assert not ws.exists()

    def test_overwrites_existing_file(self, squid_dir, patch_dirs, monkeypatch):
        """Existing working-state.md is overwritten with new content."""
        monkeypatch.setattr(cycle_post, "_state_path", lambda rel: squid_dir / rel)
        ws = squid_dir / "skill" / "working-state.md"
        ws.write_text("old content", encoding="utf-8")

        new_content = "# Working State\n\n- **Task**: none\n- **Status**: none\n"
        cycle_post._do_working_state_update({"working_state_update": new_content}, "skill")
        assert ws.read_text(encoding="utf-8") == new_content

    def test_creates_parent_directories(self, squid_dir, patch_dirs, monkeypatch):
        """Parent directories are created if they don't exist."""
        new_role_dir = squid_dir / "newrole"
        monkeypatch.setattr(cycle_post, "_state_path", lambda rel: squid_dir / rel)

        cycle_post._do_working_state_update(
            {"working_state_update": "content"}, "newrole"
        )
        ws = squid_dir / "newrole" / "working-state.md"
        assert ws.exists()
        assert ws.read_text(encoding="utf-8") == "content"


# ---------------------------------------------------------------------------
# #8453: State-branch commit paths in _do_commit_push
# ---------------------------------------------------------------------------

class TestStateCommitAfterCodeCommit:
    """#8453: Branch workflow state commit path coverage."""

    def test_state_commit_runs_after_code_commit(self, monkeypatch):
        """After code commit on feature branch, commit-state runs on working branch."""
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(("run", cmd))
            r = MagicMock()
            r.returncode = 0
            r.stdout = "main\n"
            r.stderr = ""
            return r

        def fake_run_script(script, *args, **kwargs):
            calls.append(("script", script, args))
            return MagicMock(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(cycle_post, "_run", fake_run)
        monkeypatch.setattr(cycle_post, "_run_script", fake_run_script)
        monkeypatch.setattr(cycle_post, "_get_working_branch", lambda: "main")
        monkeypatch.setattr(cycle_post, "_worktree_exists", lambda: False)

        data = {
            "cycle_type": "active",
            "cycle_number": 100,
            "commit_message": "test commit",
            "state_commit_message": "state update for cycle 100",
            "config": {"branch_workflow": True},
            "code_commit": {
                "branch": "squidsquad/task/42",
                "message": "implement feature",
            },
        }
        cycle_post._do_commit_push(data, "skill")

        # Verify commit-state was called with state_commit_message
        state_calls = [c for c in calls
                       if c[0] == "script" and "commit-state" in c[2]]
        assert len(state_calls) >= 1, (
            f"Expected commit-state call, got: {[c for c in calls if c[0] == 'script']}"
        )
        # Verify the state message was used
        state_call = state_calls[0]
        assert "state update for cycle 100" in state_call[2]

    def test_state_commit_fallback_on_failure(self, monkeypatch):
        """When commit-state fails, falls back to commit-push."""
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(("run", cmd))
            r = MagicMock()
            r.returncode = 0
            r.stdout = "main\n"
            r.stderr = ""
            return r

        def fake_run_script(script, *args, **kwargs):
            calls.append(("script", script, args))
            r = MagicMock(stdout="", stderr="")
            # commit-state fails
            if "commit-state" in args:
                r.returncode = 1
            else:
                r.returncode = 0
            return r

        monkeypatch.setattr(cycle_post, "_run", fake_run)
        monkeypatch.setattr(cycle_post, "_run_script", fake_run_script)
        monkeypatch.setattr(cycle_post, "_get_working_branch", lambda: "main")
        monkeypatch.setattr(cycle_post, "_worktree_exists", lambda: False)

        data = {
            "cycle_type": "active",
            "cycle_number": 100,
            "commit_message": "test commit",
            "config": {"branch_workflow": True},
            "code_commit": {
                "branch": "squidsquad/task/42",
                "message": "implement feature",
            },
        }
        cycle_post._do_commit_push(data, "skill")

        # After commit-state fails, commit-push should be called as fallback
        fallback_calls = [c for c in calls
                          if c[0] == "script" and "commit-push" in c[2]]
        assert len(fallback_calls) >= 1, (
            f"Expected commit-push fallback, got: {[c for c in calls if c[0] == 'script']}"
        )

    def test_worktree_state_commit_runs_at_end(self, monkeypatch):
        """When worktree exists, _state_commit is called after main commit."""
        state_commit_calls = []

        def fake_run(cmd, **kwargs):
            r = MagicMock()
            r.returncode = 0
            r.stdout = "main\n"
            r.stderr = ""
            return r

        def fake_state_commit(msg, role="unknown"):
            state_commit_calls.append((msg, role))
            return True

        monkeypatch.setattr(cycle_post, "_run", fake_run)
        monkeypatch.setattr(cycle_post, "_run_script",
                            lambda *a, **kw: MagicMock(returncode=0, stdout="", stderr=""))
        monkeypatch.setattr(cycle_post, "_get_working_branch", lambda: "main")
        monkeypatch.setattr(cycle_post, "_worktree_exists", lambda: True)
        monkeypatch.setattr(cycle_post, "_state_commit", fake_state_commit)

        data = {
            "cycle_type": "active",
            "cycle_number": 200,
            "commit_message": "test",
            "config": {"branch_workflow": True},
            "code_commit": {
                "branch": "squidsquad/task/99",
                "message": "fix bug",
            },
        }
        cycle_post._do_commit_push(data, "skill")

        assert len(state_commit_calls) == 1
        assert "cycle 200 state" in state_commit_calls[0][0]
        assert state_commit_calls[0][1] == "skill"

    def test_worktree_state_commit_with_default_path(self, monkeypatch):
        """Worktree commit runs for non-branch-workflow roles too."""
        state_commit_calls = []

        def fake_run(cmd, **kwargs):
            r = MagicMock()
            r.returncode = 0
            r.stdout = "main\n"
            r.stderr = ""
            return r

        def fake_state_commit(msg, role="unknown"):
            state_commit_calls.append((msg, role))
            return True

        monkeypatch.setattr(cycle_post, "_run", fake_run)
        monkeypatch.setattr(cycle_post, "_run_script",
                            lambda *a, **kw: MagicMock(returncode=0, stdout="", stderr=""))
        monkeypatch.setattr(cycle_post, "_get_working_branch", lambda: "main")
        monkeypatch.setattr(cycle_post, "_worktree_exists", lambda: True)
        monkeypatch.setattr(cycle_post, "_state_commit", fake_state_commit)

        data = {
            "cycle_type": "active",
            "cycle_number": 300,
            "commit_message": "pm cycle",
        }
        cycle_post._do_commit_push(data, "pm")

        assert len(state_commit_calls) == 1
        assert "cycle 300 state" in state_commit_calls[0][0]


# ---------------------------------------------------------------------------
# Task-mode logging — #8701
# ---------------------------------------------------------------------------


class TestTaskModeLog:
    """#8701: when cycle-output.json carries a `task` field, write a
    task-log entry instead of the monotonic iter-N.md."""

    def test_task_mode_writes_task_log(self, tmp_path):
        with patch.object(cycle_post, "SQUID_DIR", tmp_path), \
             patch.object(cycle_post, "REPO_ROOT", tmp_path), \
             patch.object(cycle_post, "_run_script") as mock_script:
            cycle_post._do_iteration_log(
                {
                    "task": "8701",
                    "cycle_number": 1125,
                    "cycle_type": "active",
                    "iteration_summary": "task-mode refactor done",
                    "status_transitions": [
                        {"number": 8701, "from": "in-progress", "to": "pending-test"}
                    ],
                },
                "skill",
            )
        # No iter-N.md path taken in task mode
        mock_script.assert_not_called()
        # A task-log file should exist
        log_dir = tmp_path / "skill" / "task-log"
        assert log_dir.is_dir()
        logs = list(log_dir.glob("task-8701-*.md"))
        assert len(logs) == 1
        content = logs[0].read_text(encoding="utf-8")
        assert "Task #8701" in content
        assert "task-mode refactor done" in content
        assert "#8701: in-progress → pending-test" in content

    def test_task_mode_atomic_write(self, tmp_path):
        """Task log uses .tmp + rename so partial writes leave no entry."""
        with patch.object(cycle_post, "SQUID_DIR", tmp_path), \
             patch.object(cycle_post, "REPO_ROOT", tmp_path), \
             patch.object(cycle_post, "_run_script"):
            cycle_post._do_iteration_log(
                {"task": "1", "cycle_number": 1, "cycle_type": "quiet",
                 "iteration_summary": "s"},
                "pm",
            )
        log_dir = tmp_path / "pm" / "task-log"
        # No `.tmp` residue after success
        tmps = list(log_dir.glob(".task-*.tmp"))
        assert tmps == []
        # Final file is present
        assert list(log_dir.glob("task-1-*.md"))

    def test_non_task_mode_unchanged(self, tmp_path):
        """When no `task` field, falls through to the existing iter-N.md path."""
        with patch.object(cycle_post, "SQUID_DIR", tmp_path), \
             patch.object(cycle_post, "REPO_ROOT", tmp_path), \
             patch.object(cycle_post, "_run_script",
                          return_value=MagicMock(returncode=0)) as mock_script:
            cycle_post._do_iteration_log(
                {"cycle_number": 500, "cycle_type": "active",
                 "iteration_summary": "loop cycle"},
                "skill",
            )
        # Should have invoked cycle.py log-iteration at some point (NOT task-log path)
        assert mock_script.called
        invocations = [c[0] for c in mock_script.call_args_list]
        assert any(
            inv[0] == "cycle.py" and inv[1] == "log-iteration"
            for inv in invocations
        ), f"expected log-iteration call in {invocations}"
        # No task-log directory should be created
        assert not (tmp_path / "skill" / "task-log").exists()

    def test_filename_and_content_timestamp_match(self, tmp_path):
        """R1: single datetime.now() drives both filename and content."""
        with patch.object(cycle_post, "SQUID_DIR", tmp_path), \
             patch.object(cycle_post, "REPO_ROOT", tmp_path):
            cycle_post._write_task_log(
                "skill", "8701", "active", "summary",
                {"cycle_number": 1},
            )
        logs = list((tmp_path / "skill" / "task-log").glob("task-8701-*.md"))
        assert len(logs) == 1
        fname = logs[0].name  # task-8701-YYYY-MM-DD-HHMMSS.md
        # Extract the YYYY-MM-DD-HHMMSS portion
        stem = fname[len("task-8701-"):-len(".md")]
        content = logs[0].read_text(encoding="utf-8")
        # Content has ISO format `YYYY-MM-DDTHH:MM:SS`. Derive the same
        # YYYY-MM-DD-HHMMSS form and check it matches the filename stem.
        from datetime import datetime
        # Find the Timestamp line
        ts_line = next(l for l in content.splitlines() if "Timestamp" in l)
        iso = ts_line.split("**: ", 1)[1].strip()
        derived = datetime.fromisoformat(iso).strftime("%Y-%m-%d-%H%M%S")
        assert derived == stem, f"filename {stem} != content {derived}"

    def test_rejects_path_traversal_in_task_id(self, tmp_path, capsys):
        """R2: task_id with `..`, `/`, or `\\` is refused, no file written."""
        with patch.object(cycle_post, "SQUID_DIR", tmp_path), \
             patch.object(cycle_post, "REPO_ROOT", tmp_path):
            for bad in ["../escape", "a/b", "a\\b", "..", ""]:
                cycle_post._write_task_log(
                    "skill", bad, "active", "s", {"cycle_number": 1},
                )
        # No files were ever created under task-log/ (or anywhere outside)
        log_dir = tmp_path / "skill" / "task-log"
        if log_dir.exists():
            assert list(log_dir.iterdir()) == []
        # And nothing escaped the role dir
        all_md = list(tmp_path.rglob("*.md"))
        assert all_md == [], f"unexpected files written: {all_md}"

    def test_retention_prunes_old_task_logs(self, tmp_path):
        """R3: only the N newest entries per task are kept."""
        import time
        with patch.object(cycle_post, "SQUID_DIR", tmp_path), \
             patch.object(cycle_post, "REPO_ROOT", tmp_path):
            for i in range(cycle_post._TASK_LOG_RETENTION_PER_TASK + 3):
                cycle_post._write_task_log(
                    "skill", "8701", "active", f"run {i}",
                    {"cycle_number": i},
                )
                # ensure distinct mtimes; filenames carry seconds so we
                # also need a sub-second nudge between calls
                time.sleep(1.05)
        logs = list((tmp_path / "skill" / "task-log").glob("task-8701-*.md"))
        assert len(logs) == cycle_post._TASK_LOG_RETENTION_PER_TASK

    def test_retention_keeps_other_tasks(self, tmp_path):
        """R3: pruning is scoped to the current task_id only."""
        with patch.object(cycle_post, "SQUID_DIR", tmp_path), \
             patch.object(cycle_post, "REPO_ROOT", tmp_path):
            cycle_post._write_task_log(
                "skill", "1234", "active", "other task",
                {"cycle_number": 1},
            )
            import time
            time.sleep(1.05)
            for i in range(cycle_post._TASK_LOG_RETENTION_PER_TASK + 2):
                cycle_post._write_task_log(
                    "skill", "8701", "active", f"r{i}",
                    {"cycle_number": i},
                )
                time.sleep(1.05)
        log_dir = tmp_path / "skill" / "task-log"
        # 1234 untouched
        assert len(list(log_dir.glob("task-1234-*.md"))) == 1
        # 8701 pruned
        assert len(list(log_dir.glob("task-8701-*.md"))) == \
            cycle_post._TASK_LOG_RETENTION_PER_TASK

