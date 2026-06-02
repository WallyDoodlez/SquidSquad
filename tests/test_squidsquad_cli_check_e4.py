"""Tests for `squidsquad_cli.py check` (#10683, PRD-E E4).

AC8 mandates tests for:
  (a) clean install (stored == current) → exit 0
  (b) drifted install (stored != current) → exit 1 + stderr report
  (c) broken config (malformed state file) → exit 2

Plus AC1/AC2/AC3/AC4/AC7 coverage:
  - subcommand registered + usage string carries `check`
  - reuses compose_freshness.compute_compose_checksum (single source of truth)
  - reads `last_compose_checksum` from `.harness-state.json` (read-only)
  - --full delegates to `compose.py deploy-all --check` (A4)
  - does NOT spawn agents, does NOT mutate state, does NOT run
    `deploy-all` without --check
"""

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import squidsquad_cli as cli  # noqa: E402
import compose_freshness as cf  # noqa: E402


def _stage_minimal_repo(tmp_path):
    """Reuse compose_freshness's minimal-repo shape so the checksum
    helper finds at least one file in each glob."""
    repo = tmp_path
    (repo / ".squidsquad").mkdir()
    (repo / ".squidsquad" / "config.md").write_text("- v: 1\n", encoding="utf-8")
    (repo / ".squidsquad" / "project").mkdir()
    (repo / ".squidsquad" / "project" / "pm.md").write_text("# pm\n", encoding="utf-8")
    (repo / "references" / "sub-skills" / "common").mkdir(parents=True)
    (repo / "references" / "sub-skills" / "common" / "boot.md").write_text(
        "# boot\n", encoding="utf-8")
    (repo / "references" / "sub-skills" / "manifest.md").write_text(
        "# manifest\n", encoding="utf-8")
    (repo / "references" / "roles").mkdir(parents=True)
    (repo / "references" / "roles" / "identity.md").write_text(
        "# identity\n", encoding="utf-8")
    return repo


def _write_state(repo, *, checksum):
    state_dir = repo / ".squidsquad"
    state_dir.mkdir(exist_ok=True)
    state = state_dir / ".harness-state.json"
    state.write_text(json.dumps({
        "harness_pid": 0,
        "start_time": 0,
        "port": 7373,
        "last_compose_checksum": checksum,
        "compose_freshness_failed": False,
        "agents": {},
    }), encoding="utf-8")
    return state


# ---------------------------------------------------------------------------
# AC8 — happy paths
# ---------------------------------------------------------------------------


class TestCleanInstall:
    """AC8(a): stored matches current → exit 0, stdout reports clean."""

    def test_exit_zero_when_stored_matches_current(self, tmp_path, capsys):
        repo = _stage_minimal_repo(tmp_path)
        state = _write_state(repo, checksum=cf.compute_compose_checksum(repo))
        rc = cli.cmd_check(repo_root=repo, state_file=state)
        assert rc == 0
        captured = capsys.readouterr()
        assert "clean" in captured.out.lower()
        assert captured.err == ""


class TestDriftedInstall:
    """AC8(b) + AC6: stored differs from current → exit 1 + structured
    report on stderr."""

    def test_exit_one_with_stderr_report_when_drift(self, tmp_path, capsys):
        repo = _stage_minimal_repo(tmp_path)
        state = _write_state(repo, checksum="0" * 64)  # bogus prior checksum
        rc = cli.cmd_check(repo_root=repo, state_file=state)
        assert rc == 1
        captured = capsys.readouterr()
        # Report goes to STDERR per AC5.
        assert "DRIFT DETECTED" in captured.err
        # Both checksums named (operator can audit).
        assert "0000000000000000" in captured.err
        # Some compose-input files enumerated.
        assert "references/sub-skills/" in captured.err

    def test_drift_report_names_stored_and_current(self, tmp_path, capsys):
        repo = _stage_minimal_repo(tmp_path)
        stored = "a" * 64
        state = _write_state(repo, checksum=stored)
        current = cf.compute_compose_checksum(repo)
        cli.cmd_check(repo_root=repo, state_file=state)
        captured = capsys.readouterr()
        assert stored in captured.err
        assert current in captured.err


class TestBrokenConfig:
    """AC8(c): malformed state file → exit 2."""

    def test_exit_two_on_malformed_state_json(self, tmp_path, capsys):
        repo = _stage_minimal_repo(tmp_path)
        state = repo / ".squidsquad" / ".harness-state.json"
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text("{not valid json", encoding="utf-8")
        rc = cli.cmd_check(repo_root=repo, state_file=state)
        assert rc == 2
        assert "malformed JSON" in capsys.readouterr().err


class TestFirstBootNoStoredChecksum:
    """A fresh install with no state file — or a legacy state file
    without the field — reports first-boot status and exits 0
    (treating it as drift would surface a red signal on a green
    install)."""

    def test_no_state_file_reports_first_boot_and_exits_zero(
        self, tmp_path, capsys,
    ):
        repo = _stage_minimal_repo(tmp_path)
        # state file path that doesn't exist
        missing = repo / ".squidsquad" / "missing.json"
        rc = cli.cmd_check(repo_root=repo, state_file=missing)
        assert rc == 0
        out = capsys.readouterr().out
        assert "first boot" in out.lower() or "no stored checksum" in out.lower()

    def test_legacy_state_file_without_checksum_reports_first_boot(
        self, tmp_path, capsys,
    ):
        repo = _stage_minimal_repo(tmp_path)
        state = repo / ".squidsquad" / ".harness-state.json"
        state.parent.mkdir(parents=True, exist_ok=True)
        # Legacy file shape — has agents but no last_compose_checksum.
        state.write_text(json.dumps({
            "harness_pid": 0, "start_time": 0, "port": 7373, "agents": {},
        }), encoding="utf-8")
        rc = cli.cmd_check(repo_root=repo, state_file=state)
        assert rc == 0


# ---------------------------------------------------------------------------
# AC7 — pure read-only (no spawn, no mutation)
# ---------------------------------------------------------------------------


class TestReadOnly:
    """AC7: check must not spawn agents, mutate state, or run compose
    deploy-all (only the --check dry-run via --full)."""

    def test_does_not_mutate_state_file(self, tmp_path):
        repo = _stage_minimal_repo(tmp_path)
        state = _write_state(repo, checksum=cf.compute_compose_checksum(repo))
        prior = state.read_text(encoding="utf-8")
        cli.cmd_check(repo_root=repo, state_file=state)
        after = state.read_text(encoding="utf-8")
        assert prior == after, (
            "check must not mutate the state file (AC7 read-only)"
        )

    def test_does_not_invoke_deploy_all_without_full(self, tmp_path, monkeypatch):
        # Stub subprocess.run so any sneaky invocation would surface.
        repo = _stage_minimal_repo(tmp_path)
        state = _write_state(repo, checksum=cf.compute_compose_checksum(repo))
        calls = []

        def tracking(*args, **kwargs):
            calls.append((args, kwargs))
            return subprocess.CompletedProcess(args[0], 0, "", "")

        import subprocess
        monkeypatch.setattr(cli.subprocess, "run", tracking)
        cli.cmd_check(repo_root=repo, state_file=state, full=False)
        assert calls == [], (
            "check without --full must NOT invoke compose.py "
            "(AC7 + AC4 — only --full runs the dry-run)"
        )


# ---------------------------------------------------------------------------
# AC4 — --full delegates to A4's compose.py deploy-all --check
# ---------------------------------------------------------------------------


class TestFullFlag:

    def test_full_invokes_compose_deploy_all_check(self, tmp_path, monkeypatch):
        repo = _stage_minimal_repo(tmp_path)
        state = _write_state(repo, checksum=cf.compute_compose_checksum(repo))
        calls = []

        def tracking(argv, **kwargs):
            calls.append(argv)
            import subprocess
            return subprocess.CompletedProcess(argv, 0, "all clean\n", "")

        monkeypatch.setattr(cli.subprocess, "run", tracking)
        rc = cli.cmd_check(repo_root=repo, state_file=state, full=True)
        assert rc == 0
        assert len(calls) == 1
        # First three argv entries are python, compose.py path, "deploy-all".
        assert calls[0][1].endswith("compose.py"), calls[0]
        assert calls[0][2] == "deploy-all"
        assert "--check" in calls[0]

    def test_full_returns_one_when_dry_run_reports_drift(
        self, tmp_path, monkeypatch, capsys,
    ):
        repo = _stage_minimal_repo(tmp_path)
        state = _write_state(repo, checksum=cf.compute_compose_checksum(repo))

        def fake(argv, **kwargs):
            import subprocess
            return subprocess.CompletedProcess(argv, 1, "", "  pm: DRIFT\n")

        monkeypatch.setattr(cli.subprocess, "run", fake)
        rc = cli.cmd_check(repo_root=repo, state_file=state, full=True)
        assert rc == 1
        assert "DRIFT" in capsys.readouterr().err

    def test_full_returns_two_when_dry_run_setup_error(
        self, tmp_path, monkeypatch, capsys,
    ):
        repo = _stage_minimal_repo(tmp_path)
        state = _write_state(repo, checksum=cf.compute_compose_checksum(repo))

        def fake(argv, **kwargs):
            import subprocess
            return subprocess.CompletedProcess(argv, 2, "", "config parse error\n")

        monkeypatch.setattr(cli.subprocess, "run", fake)
        rc = cli.cmd_check(repo_root=repo, state_file=state, full=True)
        assert rc == 2

    def test_full_runs_dry_run_even_when_checksum_already_drifted(
        self, tmp_path, monkeypatch, capsys,
    ):
        # DS-10683 F1 regression: prior to the fix, ``return 1`` fired
        # before ``--full`` could run, so the operator never got the
        # A4 dry-run output on the drift path. The dry-run names the
        # specific composed files that need regeneration — exactly
        # what an operator running ``check --full`` is asking for.
        repo = _stage_minimal_repo(tmp_path)
        state = _write_state(repo, checksum="z" * 64)  # bogus → drift
        calls = []

        def tracking(argv, **kwargs):
            calls.append(argv)
            import subprocess
            return subprocess.CompletedProcess(argv, 0, "all aliases clean\n", "")

        monkeypatch.setattr(cli.subprocess, "run", tracking)
        rc = cli.cmd_check(repo_root=repo, state_file=state, full=True)
        # Checksum still mismatched even though the dry-run was clean;
        # surface as drift (exit 1) so the operator sees both signals.
        assert rc == 1, (
            "checksum mismatch must still surface as drift even if the "
            "dry-run is clean (exit 1) — DS-10683 F1 regression"
        )
        assert len(calls) == 1, (
            "--full must invoke compose.py deploy-all --check EVEN WHEN "
            "the checksum already mismatched (DS-10683 F1 regression)"
        )
        # Drift report still in stderr.
        assert "DRIFT DETECTED" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# AC1 — subcommand registered in main() + usage string carries it
# ---------------------------------------------------------------------------


class TestSubcommandWiring:

    def test_main_dispatch_includes_check(self, monkeypatch):
        # Static-grep on the cli module's main() body.
        src = (SCRIPTS / "squidsquad_cli.py").read_text(encoding="utf-8")
        # main() body must dispatch to cmd_check when cmd == "check".
        main_start = src.index("def main(")
        main_end = src.index('if __name__ == "__main__":', main_start)
        block = src[main_start:main_end]
        assert 'cmd == "check"' in block, (
            "main() must register the check subcommand (AC1)"
        )
        assert "cmd_check" in block

    def test_usage_string_lists_check(self):
        assert "check" in cli.USAGE, (
            "USAGE help must list the check subcommand so operators "
            "discover it (AC1)"
        )

    def test_unrecognized_argument_after_check_returns_2(
        self, tmp_path, monkeypatch, capsys,
    ):
        # Drive through main() to exercise the arg-parser branch.
        monkeypatch.setattr(cli, "_REPO_ROOT", tmp_path)
        monkeypatch.setattr(cli, "_STATE_FILE", tmp_path / ".harness-state.json")
        monkeypatch.setattr(sys, "argv", ["squidsquad", "check", "--bogus"])
        rc = cli.main()
        assert rc == 2
        assert "unrecognized arguments" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# AC2 — reuses compose_freshness.compute_compose_checksum (one source of truth)
# ---------------------------------------------------------------------------


class TestReusesE1Checksum:
    """AC2 requires reuse of E1's checksum function so the diagnostic
    and the boot gate agree on what 'drift' means."""

    def test_check_call_path_imports_compose_freshness(self):
        # cmd_check's body does the lazy import at runtime; reading
        # the source confirms it doesn't reimplement the algorithm.
        src = (SCRIPTS / "squidsquad_cli.py").read_text(encoding="utf-8")
        cmd_start = src.index("def cmd_check(")
        cmd_end = src.index("\ndef ", cmd_start + 1)
        body = src[cmd_start:cmd_end]
        assert "compose_freshness" in body, (
            "cmd_check must reuse compose_freshness.compute_compose_checksum "
            "instead of re-implementing the algorithm (AC2)"
        )


# ---------------------------------------------------------------------------
# DS-10683 F2 regression — drift report tolerates enumeration failure
# ---------------------------------------------------------------------------


class TestDriftReportEnumerationFallback:

    def test_iter_compose_input_files_is_public_api(self):
        # The CLI should consume a public name so a future rename in
        # compose_freshness doesn't break the drift report silently.
        assert hasattr(cf, "iter_compose_input_files"), (
            "compose_freshness must expose iter_compose_input_files "
            "as a public name (DS-10683 F2)"
        )
        # Underscore alias stays for backwards compatibility.
        assert cf._iter_compose_input_files is cf.iter_compose_input_files

    def test_drift_report_falls_back_when_enumeration_raises(
        self, tmp_path, capsys, monkeypatch,
    ):
        repo = _stage_minimal_repo(tmp_path)
        state = _write_state(repo, checksum="b" * 64)  # drift

        def boom(_repo):
            raise RuntimeError("simulated enumeration failure")

        monkeypatch.setattr(cf, "iter_compose_input_files", boom)
        rc = cli.cmd_check(repo_root=repo, state_file=state)
        # Exit code is still 1 (drift) — fallback is in the REPORT,
        # not the exit semantics.
        assert rc == 1
        err = capsys.readouterr().err
        assert "DRIFT DETECTED" in err
        assert "could not enumerate compose-input files" in err
