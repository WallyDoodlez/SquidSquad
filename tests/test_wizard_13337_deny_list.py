"""Unit tests for the step-0 consent deny-list merge-writer (#13337).

`wizard.py merge-deny-list` owns the deterministic half of INSTALLER-RUNTIME
§4 step 0: merging deny rules into the TARGET project's `.claude/settings.json`
under `permissions.deny`. The consent conversation (verbatim script,
inform-before-write) is the installer's job; these tests pin the writer:

- create-if-absent (fresh project, no .claude/)
- MERGE with an existing deny list — never clobber, dedupe
- every unrelated key preserved (statusLine, hooks, permissions.allow)
- malformed / non-object / non-list shapes fail closed with NO write
- the minimal cross-platform default deny-list is always included
- --dry-run reports exactly what would be added and writes nothing
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import wizard  # noqa: E402


def _settings_path(tmp_path):
    return tmp_path / ".claude" / "settings.json"


def _read_settings(tmp_path):
    return json.loads(_settings_path(tmp_path).read_text(encoding="utf-8"))


def _write_settings(tmp_path, obj, raw=None):
    p = _settings_path(tmp_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(raw if raw is not None else json.dumps(obj, indent=2),
                 encoding="utf-8")
    return p


class TestFreshProject:
    def test_absent_settings_created_with_defaults(self, tmp_path):
        result = wizard.merge_deny_list(tmp_path)
        assert result["ok"] is True
        assert result["created"] is True
        settings = _read_settings(tmp_path)
        deny = settings["permissions"]["deny"]
        for rule in wizard.DEFAULT_DENY_RULES:
            assert rule in deny
        assert result["total_deny"] == len(deny)

    def test_user_paths_expand_to_read_edit_write(self, tmp_path):
        result = wizard.merge_deny_list(tmp_path, paths=[".env", "secrets/**"])
        assert result["ok"] is True
        deny = _read_settings(tmp_path)["permissions"]["deny"]
        for p in (".env", "secrets/**"):
            for tool in ("Read", "Edit", "Write"):
                assert f"{tool}({p})" in deny

    def test_verbatim_rules_taken_as_is(self, tmp_path):
        result = wizard.merge_deny_list(tmp_path, rules=["Bash(curl * evil.example *)"])
        assert result["ok"] is True
        assert "Bash(curl * evil.example *)" in _read_settings(tmp_path)["permissions"]["deny"]

    def test_empty_file_treated_as_fresh(self, tmp_path):
        _write_settings(tmp_path, None, raw="")
        result = wizard.merge_deny_list(tmp_path)
        assert result["ok"] is True
        deny = _read_settings(tmp_path)["permissions"]["deny"]
        assert list(wizard.DEFAULT_DENY_RULES)[0] in deny

    def test_default_list_covers_root_home_and_windows(self):
        """The cross-platform floor: filesystem root, home dir, and Windows
        equivalents each appear in the default rules."""
        joined = " ".join(wizard.DEFAULT_DENY_RULES)
        assert "rm -rf /" in joined
        assert "rm -rf ~" in joined or "$HOME" in joined
        assert "rd /s /q" in joined
        assert "Remove-Item -Recurse -Force" in joined


class TestMergeSemantics:
    def test_existing_deny_preserved_and_appended(self, tmp_path):
        existing = {"permissions": {"deny": ["Read(private/**)"]}}
        _write_settings(tmp_path, existing)
        result = wizard.merge_deny_list(tmp_path, paths=[".env"])
        assert result["ok"] is True
        deny = _read_settings(tmp_path)["permissions"]["deny"]
        # existing entry survives, in first position (append, not clobber)
        assert deny[0] == "Read(private/**)"
        assert "Read(.env)" in deny

    def test_dedupe_against_existing(self, tmp_path):
        existing = {"permissions": {"deny": [wizard.DEFAULT_DENY_RULES[0], "Read(.env)"]}}
        _write_settings(tmp_path, existing)
        result = wizard.merge_deny_list(tmp_path, paths=[".env"])
        deny = _read_settings(tmp_path)["permissions"]["deny"]
        assert deny.count(wizard.DEFAULT_DENY_RULES[0]) == 1
        assert deny.count("Read(.env)") == 1
        assert wizard.DEFAULT_DENY_RULES[0] in result["skipped"]
        assert "Read(.env)" in result["skipped"]

    def test_dedupe_path_and_rule_overlap(self, tmp_path):
        """A --rule that duplicates one of a --path's expansions lands in
        skipped, never doubled (Sonnet review Finding 2)."""
        result = wizard.merge_deny_list(
            tmp_path, paths=[".env"], rules=["Read(.env)"]
        )
        deny = _read_settings(tmp_path)["permissions"]["deny"]
        assert deny.count("Read(.env)") == 1
        assert "Read(.env)" in result["skipped"]

    def test_dedupe_within_candidates(self, tmp_path):
        result = wizard.merge_deny_list(tmp_path, paths=[".env", ".env"])
        deny = _read_settings(tmp_path)["permissions"]["deny"]
        assert deny.count("Read(.env)") == 1
        assert result["ok"] is True

    def test_unrelated_keys_preserved(self, tmp_path):
        existing = {
            "statusLine": {"type": "command", "command": "bash x.sh"},
            "hooks": {"SessionStart": [{"hooks": [{"type": "command"}]}]},
            "permissions": {"allow": ["Bash(git status*)"], "deny": []},
        }
        _write_settings(tmp_path, existing)
        result = wizard.merge_deny_list(tmp_path)
        assert result["ok"] is True
        settings = _read_settings(tmp_path)
        assert settings["statusLine"] == existing["statusLine"]
        assert settings["hooks"] == existing["hooks"]
        assert settings["permissions"]["allow"] == ["Bash(git status*)"]

    def test_idempotent_rerun_adds_nothing(self, tmp_path):
        wizard.merge_deny_list(tmp_path, paths=[".env"])
        before = _read_settings(tmp_path)
        result = wizard.merge_deny_list(tmp_path, paths=[".env"])
        assert result["ok"] is True
        assert result["added"] == []
        assert _read_settings(tmp_path) == before


class TestFailClosed:
    def test_malformed_json_refuses_to_write(self, tmp_path):
        p = _write_settings(tmp_path, None, raw="{not json")
        result = wizard.merge_deny_list(tmp_path, paths=[".env"])
        assert result["ok"] is False
        assert "malformed" in result["error"]
        assert p.read_text(encoding="utf-8") == "{not json"  # untouched

    def test_non_object_top_level_refuses(self, tmp_path):
        p = _write_settings(tmp_path, None, raw="[1, 2]")
        result = wizard.merge_deny_list(tmp_path)
        assert result["ok"] is False
        assert p.read_text(encoding="utf-8") == "[1, 2]"

    def test_permissions_not_object_refuses(self, tmp_path):
        _write_settings(tmp_path, {"permissions": "nope"})
        result = wizard.merge_deny_list(tmp_path)
        assert result["ok"] is False
        assert "permissions" in result["error"]

    def test_deny_not_list_refuses(self, tmp_path):
        p = _write_settings(tmp_path, {"permissions": {"deny": {"a": 1}}})
        before = p.read_text(encoding="utf-8")
        result = wizard.merge_deny_list(tmp_path)
        assert result["ok"] is False
        assert "deny" in result["error"]
        assert p.read_text(encoding="utf-8") == before


class TestDryRun:
    def test_dry_run_reports_added_without_writing_fresh(self, tmp_path):
        result = wizard.merge_deny_list(tmp_path, paths=[".env"], dry_run=True)
        assert result["ok"] is True
        assert result["dry_run"] is True
        assert "Read(.env)" in result["added"]
        assert not _settings_path(tmp_path).exists()

    def test_dry_run_leaves_existing_untouched(self, tmp_path):
        p = _write_settings(tmp_path, {"permissions": {"deny": ["Read(x)"]}})
        before = p.read_text(encoding="utf-8")
        result = wizard.merge_deny_list(tmp_path, paths=[".env"], dry_run=True)
        assert result["ok"] is True
        assert "Read(.env)" in result["added"]
        assert p.read_text(encoding="utf-8") == before


class TestCli:
    def _run(self, tmp_path, *flags):
        # Explicit cwd + encoding (#13397): pin the subprocess environment so a
        # cwd inherited from another test or a locale-dependent stdio encoding
        # cannot perturb the asserted exit code. Matches test_cli_dispatch_registered.
        cmd = [sys.executable, str(SCRIPTS_DIR / "wizard.py"), "merge-deny-list",
               *flags, str(tmp_path)]
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60,
            cwd=str(REPO_ROOT), encoding="utf-8",
        )
        # #13589: a rare Windows full-suite-only flake exits nonzero with
        # BOTH stdout and stderr empty (no envelope, no traceback) — not
        # reproducible in isolation, self-clears on rerun. Signature points
        # to transient subprocess-spawn contention under full-gate load, not
        # a defect in the deny-list logic. A single bounded retry
        # distinguishes that from a real regression that happens to also
        # produce empty output; if the retry ALSO comes back empty, dump
        # diagnostics so the next occurrence is actionable instead of a
        # blank `returncode == 1`. Logged either way — never silently papers
        # over a genuine failure.
        if proc.returncode != 0 and not proc.stdout and not proc.stderr:
            print(f"WARNING (#13589): {cmd} exited {proc.returncode} with "
                  f"empty stdout+stderr — retrying once to check for the "
                  f"known transient flake", file=sys.stderr)
            retry = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60,
                cwd=str(REPO_ROOT), encoding="utf-8",
            )
            if retry.returncode == 0 or retry.stdout or retry.stderr:
                print(f"INFO (#13589): retry returned returncode="
                      f"{retry.returncode} with non-empty output — confirms "
                      f"the known #13589 transient-spawn flake, not a real "
                      f"regression", file=sys.stderr)
                return retry
            diag = (
                f"#13589: BOTH the original and retry runs exited nonzero "
                f"with empty stdout+stderr — this is NOT the known "
                f"transient flake, investigate. cmd={cmd!r} "
                f"cwd={str(REPO_ROOT)!r} sys.executable={sys.executable!r} "
                f"script_exists={(SCRIPTS_DIR / 'wizard.py').exists()!r}"
            )
            print(diag, file=sys.stderr)
            retry.stderr = (retry.stderr or "") + "\n" + diag
            return retry
        return proc

    def test_cli_happy_path_envelope(self, tmp_path):
        proc = self._run(tmp_path, "--path", ".env")
        assert proc.returncode == 0, proc.stderr
        envelope = json.loads(proc.stdout)
        assert envelope["ok"] is True
        assert "Read(.env)" in envelope["added"]
        assert _settings_path(tmp_path).exists()

    def test_cli_dry_run_writes_nothing(self, tmp_path):
        proc = self._run(tmp_path, "--dry-run", "--path", ".env")
        assert proc.returncode == 0, proc.stderr
        assert json.loads(proc.stdout)["dry_run"] is True
        assert not _settings_path(tmp_path).exists()

    def test_cli_malformed_settings_exits_nonzero(self, tmp_path):
        _write_settings(tmp_path, None, raw="{oops")
        proc = self._run(tmp_path)
        assert proc.returncode == 1
        assert json.loads(proc.stdout)["ok"] is False

    def test_cli_unknown_flag_exits_2(self, tmp_path):
        proc = self._run(tmp_path, "--bogus")
        assert proc.returncode == 2

    def test_cli_unknown_flag_exit_2_is_deterministic(self, tmp_path):
        """#13397 regression: the usage-error exit code must be 2 on EVERY run,
        not just usually. A guarded stderr write (wizard._cli_usage_error)
        keeps a transient pipe-write failure under load from turning the
        deterministic exit(2) into a spurious exit(1)."""
        for _ in range(6):
            assert self._run(tmp_path, "--bogus").returncode == 2

    def test_unknown_flag_returns_2_in_process(self):
        """The exit-2 contract at the logic level (no subprocess) — for both
        usage-error sites: an unknown flag and a flag missing its value."""
        assert wizard.cmd_merge_deny_list(["--bogus", "."]) == 2
        assert wizard.cmd_merge_deny_list(["--path"]) == 2  # missing value

    def test_usage_error_returns_2_even_if_stderr_write_fails(self, monkeypatch):
        """#13397 root-cause lock: an unhandled exception on the usage-error
        stderr write would propagate through main()/sys.exit(main()) and exit
        the process with Python's unhandled-exception code 1 instead of 2. The
        guard in _cli_usage_error swallows the write failure so exit stays 2."""
        import builtins
        real_print = builtins.print

        def boom(*a, **k):
            if k.get("file") is sys.stderr:
                raise OSError("simulated pipe write failure under load")
            return real_print(*a, **k)

        monkeypatch.setattr(builtins, "print", boom)
        assert wizard._cli_usage_error("boom") == 2
        assert wizard.cmd_merge_deny_list(["--bogus", "."]) == 2

    def test_cli_dispatch_registered(self):
        """merge-deny-list must be in wizard.py's dispatch table."""
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "wizard.py"), "merge-deny-list",
             "--dry-run"],
            capture_output=True, text=True, timeout=60,
            cwd=str(REPO_ROOT),
        )
        # --dry-run against the repo itself: reads only, must succeed.
        assert proc.returncode == 0, proc.stderr
        assert json.loads(proc.stdout)["dry_run"] is True


class TestCliRunRetryDiagnostics13589:
    """#13589: TestCli._run's single-bounded-retry on the empty-output
    subprocess flake signature (returncode != 0, stdout AND stderr both
    empty) — must retry exactly once, return the retry's result if it
    produced real output, and attach actionable diagnostics if the retry
    ALSO comes back empty (never silently swallow a real failure)."""

    def _flake_result(self, cmd, returncode=1):
        return subprocess.CompletedProcess(cmd, returncode, stdout="", stderr="")

    def _ok_result(self, cmd):
        return subprocess.CompletedProcess(
            cmd, 0, stdout=json.dumps({"ok": True, "added": ["Read(.env)"]}),
            stderr="",
        )

    def test_retries_on_transient_empty_output_flake(self, tmp_path, monkeypatch):
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            if len(calls) == 1:
                return self._flake_result(cmd)
            return self._ok_result(cmd)

        monkeypatch.setattr(subprocess, "run", fake_run)
        proc = TestCli()._run(tmp_path, "--path", ".env")
        assert len(calls) == 2, "must retry exactly once on the flake signature"
        assert proc.returncode == 0
        assert json.loads(proc.stdout)["ok"] is True

    def test_does_not_retry_when_output_present(self, tmp_path, monkeypatch):
        """A real failure (non-empty stderr) must NOT trigger a retry —
        only the specific empty-stdout+empty-stderr signature does."""
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            return subprocess.CompletedProcess(
                cmd, 1, stdout="", stderr="a real error message"
            )

        monkeypatch.setattr(subprocess, "run", fake_run)
        proc = TestCli()._run(tmp_path, "--path", ".env")
        assert len(calls) == 1, "a real (non-empty-output) failure must not retry"
        assert proc.returncode == 1
        assert proc.stderr == "a real error message"

    def test_diagnostics_attached_when_retry_also_empty(self, tmp_path, monkeypatch):
        """If the flake signature persists across the retry, it is NOT the
        known transient flake — actionable diagnostics must be attached
        instead of returning a blank empty-stderr failure."""
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            return self._flake_result(cmd)

        monkeypatch.setattr(subprocess, "run", fake_run)
        proc = TestCli()._run(tmp_path, "--path", ".env")
        assert len(calls) == 2, "must retry exactly once, not loop"
        assert proc.returncode != 0
        assert "#13589" in proc.stderr
        assert "NOT the known" in proc.stderr

    def test_success_on_first_try_does_not_retry(self, tmp_path, monkeypatch):
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            return self._ok_result(cmd)

        monkeypatch.setattr(subprocess, "run", fake_run)
        proc = TestCli()._run(tmp_path, "--path", ".env")
        assert len(calls) == 1
        assert proc.returncode == 0
