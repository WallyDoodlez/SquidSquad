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

    def test_legacy_restart_sentinel_still_works(self, patch_dirs, squid_dir):
        """Backward compat: restart_needed still writes .restart."""
        data = {"restart_needed": True, "restart_reason": "context pressure at 80%"}
        result = cycle_post._do_restart_sentinel(data, "skill")
        assert result is True
        sentinel = squid_dir / "skill" / ".restart"
        assert sentinel.exists()


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

    def test_returns_true_when_workflow_disabled(self):
        with patch.dict("sys.modules", {"config": MagicMock()}), \
             patch("config.get_field", side_effect=lambda f: {
                 "branch-workflow": "no",
             }.get(f, "")):
            assert cycle_post._verify_remote_branch(100, role="skill") is True

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


class TestAdvanceEventCursorInsertion:
    """#7440: cursor insertion works after dead no-op removal."""

    def test_inserts_cursor_after_status_line(self, squid_dir, patch_dirs, monkeypatch):
        monkeypatch.setattr(cycle_post, "_state_path", lambda rel: squid_dir / rel)
        ws = squid_dir / "skill" / "working-state.md"
        ws.write_text("# Working State\n\n- **Task**: #100\n- **Status**: in-progress\n\n## Completed Steps\n", encoding="utf-8")
        (squid_dir / "skill" / "cycle-input.json").write_text(json.dumps({"recent_events": [{"id": "abc12345"}]}), encoding="utf-8")
        cycle_post._advance_event_cursor({}, "skill")
        result = ws.read_text(encoding="utf-8")
        assert "- **Last Processed Event ID**: abc12345" in result

    def test_inserts_cursor_after_started_line(self, squid_dir, patch_dirs, monkeypatch):
        monkeypatch.setattr(cycle_post, "_state_path", lambda rel: squid_dir / rel)
        ws = squid_dir / "skill" / "working-state.md"
        ws.write_text("# Working State\n\n- **Task**: #100\n- **Status**: in-progress\n- **Started**: 2026-05-11 01:00\n\n## Completed Steps\n", encoding="utf-8")
        (squid_dir / "skill" / "cycle-input.json").write_text(json.dumps({"recent_events": [{"id": "def67890"}]}), encoding="utf-8")
        cycle_post._advance_event_cursor({}, "skill")
        result = ws.read_text(encoding="utf-8")
        assert "- **Last Processed Event ID**: def67890" in result
        lines = result.splitlines()
        started_idx = next(i for i, l in enumerate(lines) if "**Started**" in l)
        cursor_idx = next(i for i, l in enumerate(lines) if "Event ID" in l)
        assert cursor_idx == started_idx + 1

    def test_replaces_existing_cursor(self, squid_dir, patch_dirs, monkeypatch):
        monkeypatch.setattr(cycle_post, "_state_path", lambda rel: squid_dir / rel)
        ws = squid_dir / "skill" / "working-state.md"
        ws.write_text("# Working State\n\n- **Task**: none\n- **Status**: none\n- **Last Processed Event ID**: old11111\n", encoding="utf-8")
        (squid_dir / "skill" / "cycle-input.json").write_text(json.dumps({"recent_events": [{"id": "new22222"}]}), encoding="utf-8")
        cycle_post._advance_event_cursor({}, "skill")
        result = ws.read_text(encoding="utf-8")
        assert "new22222" in result
        assert "old11111" not in result


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
