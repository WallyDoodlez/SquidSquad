"""Unit tests for the install wizard's Phase 0 dependency gather-all detection
and provisioning (#11613, INSTALLER-ARCH §4.1).

The model under test is gather-all -> present -> ONE consent -> provision ->
re-verify. Detection and per-platform install dispatch are deterministic Python
in wizard.py; the consent prompt itself lives in the WIZARD.md runbook and is
NOT exercised here. All environment probes (shutil.which, wizard._run,
importlib.util.find_spec, platform.system) are stubbed — no test talks to the
real gh CLI, pip, npm, or a real package manager.
"""

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))

import wizard  # noqa: E402


# ---------------------------------------------------------------------------
# Stubbing helpers
# ---------------------------------------------------------------------------

def _fake_proc(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(
        args=["stub"], returncode=returncode, stdout=stdout, stderr=stderr,
    )


def _which_from(present):
    """Return a fake shutil.which: resolves names in `present`, else None."""
    present = set(present)
    return lambda name: (f"/usr/bin/{name}" if name in present else None)


def _run_router(mapping, default_rc=0):
    """Stub wizard._run keyed by command prefix tuple (longest prefix wins)."""
    def _fake(cmd, **kwargs):
        best = None
        for prefix, proc in mapping.items():
            if tuple(str(c) for c in cmd[: len(prefix)]) == prefix:
                if best is None or len(prefix) > len(best[0]):
                    best = (prefix, proc)
        if best is not None:
            return best[1]
        return _fake_proc(returncode=default_rc)
    return _fake


def _find_spec_from(available_modules):
    """Fake importlib.util.find_spec: truthy for available modules."""
    available = set(available_modules)
    return lambda name: (object() if name in available else None)


@pytest.fixture
def healthy_env(monkeypatch):
    """A fully-provisioned environment: every dep satisfied."""
    monkeypatch.setattr(wizard.platform, "system", lambda: "Linux")
    monkeypatch.setattr(
        wizard.shutil, "which",
        _which_from({"gh", "python3", "python", "pip", "claude", "npm",
                     "apt-get"}),
    )
    monkeypatch.setattr(wizard, "_run", _run_router({
        ("gh", "auth", "status"): _fake_proc(0),
        (sys.executable, "-m", "pip", "--version"): _fake_proc(0, "pip 24.0"),
    }))
    monkeypatch.setattr(
        wizard.importlib.util, "find_spec",
        _find_spec_from({"fastapi", "starlette", "uvicorn", "watchdog", "yaml"}),
    )
    return monkeypatch


# ---------------------------------------------------------------------------
# _detect_os
# ---------------------------------------------------------------------------

class TestDetectOs:
    @pytest.mark.parametrize("sysname,expected", [
        ("Windows", "windows"),
        ("Darwin", "macos"),
        ("Linux", "linux"),
        ("FreeBSD", "unknown"),
    ])
    def test_normalizes(self, monkeypatch, sysname, expected):
        monkeypatch.setattr(wizard.platform, "system", lambda: sysname)
        assert wizard._detect_os() == expected


# ---------------------------------------------------------------------------
# _packages_from_requirements
# ---------------------------------------------------------------------------

class TestPackagesFromRequirements:
    def test_parses_names_and_maps_import(self, tmp_path):
        (tmp_path / "requirements.txt").write_text(
            "# a comment\n"
            "fastapi>=0.100.0   # inline comment\n"
            "starlette>=0.27.0\n"
            "uvicorn>=0.23.0\n"
            "watchdog>=3.0.0\n"
            "pyyaml>=6.0\n"
            "-r other.txt\n"
            "\n"
            "somepkg[extra]>=1.0 ; python_version >= '3.8'\n",
            encoding="utf-8",
        )
        pairs = wizard._packages_from_requirements(tmp_path)
        names = [p[0] for p in pairs]
        imports = dict(pairs)
        assert names == ["fastapi", "starlette", "uvicorn", "watchdog",
                         "pyyaml", "somepkg"]
        # pyyaml's import name is `yaml`.
        assert imports["pyyaml"] == "yaml"
        # default mapping = dist name with '-'->'_'
        assert imports["fastapi"] == "fastapi"
        # extras + markers stripped, dash->underscore default
        assert imports["somepkg"] == "somepkg"

    def test_missing_file_returns_empty(self, tmp_path):
        assert wizard._packages_from_requirements(tmp_path) == []

    def test_dash_to_underscore_default_import(self, tmp_path):
        (tmp_path / "requirements.txt").write_text(
            "some-dist==1.2.3\n", encoding="utf-8",
        )
        pairs = wizard._packages_from_requirements(tmp_path)
        assert pairs == [("some-dist", "some_dist")]


# ---------------------------------------------------------------------------
# _missing_packages
# ---------------------------------------------------------------------------

class TestMissingPackages:
    def test_reports_only_unavailable(self, tmp_path, monkeypatch):
        (tmp_path / "requirements.txt").write_text(
            "fastapi>=0.1\npyyaml>=6.0\nwatchdog>=3.0\n", encoding="utf-8",
        )
        monkeypatch.setattr(
            wizard.importlib.util, "find_spec",
            _find_spec_from({"fastapi"}),  # yaml + watchdog missing
        )
        missing = wizard._missing_packages(tmp_path)
        assert missing == ["pyyaml", "watchdog"]

    def test_find_spec_valueerror_counts_as_missing(self, tmp_path, monkeypatch):
        (tmp_path / "requirements.txt").write_text("fastapi>=0.1\n", encoding="utf-8")

        def _boom(name):
            raise ValueError("bad spec")

        monkeypatch.setattr(wizard.importlib.util, "find_spec", _boom)
        assert wizard._missing_packages(tmp_path) == ["fastapi"]


# ---------------------------------------------------------------------------
# _choose_pkg_manager
# ---------------------------------------------------------------------------

class TestChoosePkgManager:
    def test_windows_prefers_winget(self, monkeypatch):
        monkeypatch.setattr(wizard.shutil, "which", _which_from({"winget", "choco"}))
        mgr, builder = wizard._choose_pkg_manager("windows")
        assert mgr == "winget"
        assert builder("GitHub.cli")[0] == "winget"
        assert "--silent" in builder("GitHub.cli")

    def test_windows_falls_back_to_choco(self, monkeypatch):
        monkeypatch.setattr(wizard.shutil, "which", _which_from({"choco"}))
        mgr, builder = wizard._choose_pkg_manager("windows")
        assert mgr == "choco"
        assert builder("gh") == ["choco", "install", "gh", "-y"]

    def test_macos_brew(self, monkeypatch):
        monkeypatch.setattr(wizard.shutil, "which", _which_from({"brew"}))
        mgr, builder = wizard._choose_pkg_manager("macos")
        assert mgr == "brew"
        assert builder("gh") == ["brew", "install", "gh"]

    def test_linux_apt_then_dnf(self, monkeypatch):
        monkeypatch.setattr(wizard.shutil, "which", _which_from({"dnf"}))
        mgr, builder = wizard._choose_pkg_manager("linux")
        assert mgr == "dnf"
        assert builder("gh") == ["dnf", "install", "-y", "gh"]

    def test_no_manager_available(self, monkeypatch):
        monkeypatch.setattr(wizard.shutil, "which", _which_from(set()))
        assert wizard._choose_pkg_manager("linux") == (None, None)

    def test_no_sudo_injected(self, monkeypatch):
        """provision must never inject sudo (would hang on a password prompt)."""
        monkeypatch.setattr(wizard.shutil, "which", _which_from({"apt-get"}))
        _, builder = wizard._choose_pkg_manager("linux")
        assert "sudo" not in builder("gh")


# ---------------------------------------------------------------------------
# gather_deps
# ---------------------------------------------------------------------------

class TestGatherDeps:
    def test_all_satisfied(self, tmp_path, healthy_env):
        (tmp_path / "requirements.txt").write_text("fastapi>=0.1\n", encoding="utf-8")
        result = wizard.gather_deps(base_dir=tmp_path)
        assert result["ok"] is True
        assert result["missing"] == []
        assert set(result["satisfied"]) >= {
            "gh", "gh_auth", "python3", "pip", "packages", "claude"}

    def test_gh_missing_is_auto_when_pkg_mgr_present(self, tmp_path, monkeypatch):
        monkeypatch.setattr(wizard.platform, "system", lambda: "Darwin")
        monkeypatch.setattr(
            wizard.shutil, "which",
            _which_from({"python3", "pip", "claude", "brew"}),  # no gh
        )
        monkeypatch.setattr(wizard, "_run", _run_router({
            (sys.executable, "-m", "pip", "--version"): _fake_proc(0),
        }))
        monkeypatch.setattr(
            wizard.importlib.util, "find_spec",
            _find_spec_from({"fastapi", "yaml"}),
        )
        (tmp_path / "requirements.txt").write_text("fastapi\npyyaml\n", encoding="utf-8")
        result = wizard.gather_deps(base_dir=tmp_path)
        gh = next(m for m in result["missing"] if m["id"] == "gh")
        assert gh["action"]["auto"] is True
        assert gh["action"]["command"][0] == "brew"
        assert "gh" in result["auto_ids"]

    def test_gather_all_does_not_bail_on_first(self, tmp_path, monkeypatch):
        """Every missing dep is enumerated in one pass — no fail-fast."""
        monkeypatch.setattr(wizard.platform, "system", lambda: "Linux")
        monkeypatch.setattr(wizard.shutil, "which", _which_from(set()))  # nothing
        monkeypatch.setattr(wizard, "_run", _run_router({
            (sys.executable, "-m", "pip", "--version"): _fake_proc(1),  # pip absent
        }))
        monkeypatch.setattr(
            wizard.importlib.util, "find_spec", _find_spec_from(set()))
        (tmp_path / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
        result = wizard.gather_deps(base_dir=tmp_path)
        assert result["ok"] is False
        missing_ids = {m["id"] for m in result["missing"]}
        # gh, gh_auth, python3, pip, packages, claude all reported together.
        assert missing_ids == {
            "gh", "gh_auth", "python3", "pip", "packages", "claude"}

    def test_gh_auth_blocked_when_gh_absent(self, tmp_path, monkeypatch):
        monkeypatch.setattr(wizard.platform, "system", lambda: "Linux")
        monkeypatch.setattr(
            wizard.shutil, "which",
            _which_from({"python3", "pip", "claude", "apt-get"}),  # no gh
        )
        monkeypatch.setattr(wizard, "_run", _run_router({
            (sys.executable, "-m", "pip", "--version"): _fake_proc(0),
        }))
        monkeypatch.setattr(
            wizard.importlib.util, "find_spec", _find_spec_from({"fastapi"}))
        (tmp_path / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
        result = wizard.gather_deps(base_dir=tmp_path)
        auth = next(m for m in result["missing"] if m["id"] == "gh_auth")
        assert auth["action"]["auto"] is False
        assert auth["action"].get("blocked_by") == "gh"
        assert "gh_auth" in result["guided_ids"]

    def test_gh_installed_but_unauthenticated(self, tmp_path, monkeypatch):
        monkeypatch.setattr(wizard.platform, "system", lambda: "Linux")
        monkeypatch.setattr(
            wizard.shutil, "which",
            _which_from({"gh", "python3", "pip", "claude", "apt-get"}),
        )
        monkeypatch.setattr(wizard, "_run", _run_router({
            ("gh", "auth", "status"): _fake_proc(1, stderr="not logged in"),
            (sys.executable, "-m", "pip", "--version"): _fake_proc(0),
        }))
        monkeypatch.setattr(
            wizard.importlib.util, "find_spec", _find_spec_from({"fastapi"}))
        (tmp_path / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
        result = wizard.gather_deps(base_dir=tmp_path)
        assert "gh" in result["satisfied"]
        auth = next(m for m in result["missing"] if m["id"] == "gh_auth")
        assert auth["action"]["type"] == "interactive"
        assert auth["action"]["command"] == ["gh", "auth", "login"]

    def test_claude_guided_npm_when_present(self, tmp_path, monkeypatch):
        monkeypatch.setattr(wizard.platform, "system", lambda: "Linux")
        monkeypatch.setattr(
            wizard.shutil, "which",
            _which_from({"gh", "python3", "pip", "npm", "apt-get"}),  # no claude
        )
        monkeypatch.setattr(wizard, "_run", _run_router({
            ("gh", "auth", "status"): _fake_proc(0),
            (sys.executable, "-m", "pip", "--version"): _fake_proc(0),
        }))
        monkeypatch.setattr(
            wizard.importlib.util, "find_spec", _find_spec_from({"fastapi"}))
        (tmp_path / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
        result = wizard.gather_deps(base_dir=tmp_path)
        claude = next(m for m in result["missing"] if m["id"] == "claude")
        assert claude["action"]["type"] == "npm"
        assert claude["action"]["auto"] is True
        assert claude["action"]["command"][:3] == ["npm", "install", "-g"]

    def test_claude_instruct_when_no_npm(self, tmp_path, monkeypatch):
        monkeypatch.setattr(wizard.platform, "system", lambda: "Linux")
        monkeypatch.setattr(
            wizard.shutil, "which",
            _which_from({"gh", "python3", "pip", "apt-get"}),  # no claude, no npm
        )
        monkeypatch.setattr(wizard, "_run", _run_router({
            ("gh", "auth", "status"): _fake_proc(0),
            (sys.executable, "-m", "pip", "--version"): _fake_proc(0),
        }))
        monkeypatch.setattr(
            wizard.importlib.util, "find_spec", _find_spec_from({"fastapi"}))
        (tmp_path / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
        result = wizard.gather_deps(base_dir=tmp_path)
        claude = next(m for m in result["missing"] if m["id"] == "claude")
        assert claude["action"]["type"] == "instruct"
        assert claude["action"]["auto"] is False
        assert claude["action"]["command"] is None
        assert "claude" in result["guided_ids"]

    def test_packages_action_lists_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(wizard.platform, "system", lambda: "Linux")
        monkeypatch.setattr(
            wizard.shutil, "which",
            _which_from({"gh", "python3", "pip", "claude", "apt-get"}),
        )
        monkeypatch.setattr(wizard, "_run", _run_router({
            ("gh", "auth", "status"): _fake_proc(0),
            (sys.executable, "-m", "pip", "--version"): _fake_proc(0),
        }))
        monkeypatch.setattr(
            wizard.importlib.util, "find_spec", _find_spec_from({"fastapi"}))
        (tmp_path / "requirements.txt").write_text(
            "fastapi\npyyaml\nwatchdog\n", encoding="utf-8")
        result = wizard.gather_deps(base_dir=tmp_path)
        pkgs = next(m for m in result["missing"] if m["id"] == "packages")
        assert pkgs["action"]["type"] == "pip"
        assert pkgs["action"]["packages"] == ["pyyaml", "watchdog"]
        assert pkgs["action"]["command"][:4] == [
            sys.executable, "-m", "pip", "install"]

    def test_pip_missing_uses_ensurepip(self, tmp_path, monkeypatch):
        monkeypatch.setattr(wizard.platform, "system", lambda: "Linux")
        monkeypatch.setattr(
            wizard.shutil, "which",
            _which_from({"gh", "python3", "claude", "apt-get"}),  # no pip on PATH
        )
        monkeypatch.setattr(wizard, "_run", _run_router({
            ("gh", "auth", "status"): _fake_proc(0),
            (sys.executable, "-m", "pip", "--version"): _fake_proc(1),  # pip broken
        }))
        monkeypatch.setattr(
            wizard.importlib.util, "find_spec", _find_spec_from({"fastapi"}))
        (tmp_path / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
        result = wizard.gather_deps(base_dir=tmp_path)
        pip = next(m for m in result["missing"] if m["id"] == "pip")
        assert pip["action"]["auto"] is True
        assert "ensurepip" in pip["action"]["command"]


# ---------------------------------------------------------------------------
# provision_deps
# ---------------------------------------------------------------------------

class TestProvisionDeps:
    def _missing_env(self, tmp_path, monkeypatch, run_mapping):
        """gh + packages missing on linux with apt; gh_auth guided."""
        monkeypatch.setattr(wizard.platform, "system", lambda: "Linux")
        monkeypatch.setattr(
            wizard.shutil, "which",
            _which_from({"python3", "pip", "claude", "apt-get"}),  # no gh
        )
        monkeypatch.setattr(wizard, "_run", _run_router(run_mapping))
        monkeypatch.setattr(
            wizard.importlib.util, "find_spec", _find_spec_from(set()))
        (tmp_path / "requirements.txt").write_text("fastapi\n", encoding="utf-8")

    def test_provisions_all_auto_by_default(self, tmp_path, monkeypatch):
        calls = []

        def _run(cmd, **kwargs):
            calls.append([str(c) for c in cmd])
            if tuple(str(c) for c in cmd[:4]) == (
                    sys.executable, "-m", "pip", "--version"):
                return _fake_proc(1)  # pip missing -> drives gather
            return _fake_proc(0)

        self._missing_env(tmp_path, monkeypatch, {})
        monkeypatch.setattr(wizard, "_run", _run)
        result = wizard.provision_deps(base_dir=tmp_path)
        # gh (apt), pip (ensurepip), packages (pip install) are auto;
        # gh_auth is guided -> not attempted.
        assert set(result["attempted"]) == {"gh", "pip", "packages"}
        assert "gh_auth" not in result["attempted"]
        assert result["ok"] is True

    def test_guided_items_are_skipped_not_run(self, tmp_path, monkeypatch):
        self._missing_env(tmp_path, monkeypatch, {
            (sys.executable, "-m", "pip", "--version"): _fake_proc(0),
        })
        # Request gh_auth explicitly — it must be skipped (interactive).
        result = wizard.provision_deps(ids=["gh_auth"], base_dir=tmp_path)
        assert result["attempted"] == []
        assert any(s["id"] == "gh_auth" and "not auto" in s["reason"]
                   for s in result["skipped"])

    def test_unknown_id_skipped(self, tmp_path, monkeypatch):
        self._missing_env(tmp_path, monkeypatch, {
            (sys.executable, "-m", "pip", "--version"): _fake_proc(0),
        })
        result = wizard.provision_deps(ids=["nonsense"], base_dir=tmp_path)
        assert any(s["id"] == "nonsense" and "not in missing-set" in s["reason"]
                   for s in result["skipped"])

    def test_failed_command_reports_not_ok(self, tmp_path, monkeypatch):
        def _run(cmd, **kwargs):
            if tuple(str(c) for c in cmd[:4]) == (
                    sys.executable, "-m", "pip", "--version"):
                return _fake_proc(0)
            if cmd[0] == "apt-get":
                return _fake_proc(1, stderr="permission denied")
            return _fake_proc(0)

        self._missing_env(tmp_path, monkeypatch, {})
        monkeypatch.setattr(wizard, "_run", _run)
        result = wizard.provision_deps(ids=["gh"], base_dir=tmp_path)
        assert result["ok"] is False
        gh = next(r for r in result["results"] if r["id"] == "gh")
        assert gh["ok"] is False
        assert "permission denied" in gh["stderr_tail"]

    def test_nothing_to_provision_when_satisfied(self, tmp_path, healthy_env):
        (tmp_path / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
        result = wizard.provision_deps(base_dir=tmp_path)
        assert result["ok"] is True
        assert result["attempted"] == []
        assert result["message"] == "Nothing to provision."

    def test_acts_only_on_real_missing_set(self, tmp_path, monkeypatch):
        """Requesting an already-satisfied id is a no-op skip (acts on the
        live gather, never an invented set)."""
        self._missing_env(tmp_path, monkeypatch, {
            (sys.executable, "-m", "pip", "--version"): _fake_proc(0),
        })
        # python3 is satisfied in this env -> not in missing-set.
        result = wizard.provision_deps(ids=["python3"], base_dir=tmp_path)
        assert result["attempted"] == []
        assert any(s["id"] == "python3" for s in result["skipped"])


# ---------------------------------------------------------------------------
# CLI exit codes
# ---------------------------------------------------------------------------

class TestCliExitCodes:
    def test_gather_deps_exit_1_when_missing(self, monkeypatch, capsys):
        monkeypatch.setattr(wizard, "gather_deps",
                            lambda *a, **k: {"ok": False, "missing": [{"id": "gh"}]})
        rc = wizard.cmd_gather_deps([])
        assert rc == 1

    def test_gather_deps_exit_0_when_ok(self, monkeypatch, capsys):
        monkeypatch.setattr(wizard, "gather_deps",
                            lambda *a, **k: {"ok": True, "missing": []})
        rc = wizard.cmd_gather_deps([])
        assert rc == 0

    def test_provision_deps_passes_ids(self, monkeypatch, capsys):
        captured = {}

        def _fake_provision(ids=None, base_dir=None):
            captured["ids"] = ids
            return {"ok": True}

        monkeypatch.setattr(wizard, "provision_deps", _fake_provision)
        wizard.cmd_provision_deps(["gh", "packages"])
        assert captured["ids"] == ["gh", "packages"]

    def test_provision_deps_none_ids_when_no_args(self, monkeypatch, capsys):
        captured = {}

        def _fake_provision(ids=None, base_dir=None):
            captured["ids"] = ids
            return {"ok": True}

        monkeypatch.setattr(wizard, "provision_deps", _fake_provision)
        wizard.cmd_provision_deps([])
        assert captured["ids"] is None

    def test_dispatch_registers_commands(self):
        # The new commands must be wired into main()'s dispatch table.
        import inspect
        src = inspect.getsource(wizard.main)
        assert '"gather-deps": cmd_gather_deps' in src
        assert '"provision-deps": cmd_provision_deps' in src


# ---------------------------------------------------------------------------
# DS-review hardening (chunk-2 findings)
# ---------------------------------------------------------------------------

class TestRunOSErrorHandling:
    """Finding 1: _run must not let a missing/non-executable binary crash a
    provision loop — it returns a synthetic 127 like the timeout branch."""

    def test_file_not_found_returns_127(self, monkeypatch):
        def _boom(cmd, **kwargs):
            raise FileNotFoundError(2, "No such file or directory")

        monkeypatch.setattr(wizard.subprocess, "run", _boom)
        result = wizard._run(["definitely-not-a-real-binary", "x"])
        assert isinstance(result, subprocess.CompletedProcess)
        assert result.returncode == 127
        assert "failed to run" in result.stderr

    def test_permission_error_returns_127(self, monkeypatch):
        def _boom(cmd, **kwargs):
            raise PermissionError(13, "Permission denied")

        monkeypatch.setattr(wizard.subprocess, "run", _boom)
        result = wizard._run(["brew", "install", "gh"])
        assert result.returncode == 127

    def test_provision_does_not_crash_on_vanished_binary(self, tmp_path, monkeypatch):
        """The whole point: provision_deps still returns a structured dict.

        Patches subprocess.run (not _run) so the REAL _run wrapper's OSError
        catch is exercised end-to-end.
        """
        monkeypatch.setattr(wizard.platform, "system", lambda: "Linux")
        monkeypatch.setattr(
            wizard.shutil, "which",
            _which_from({"python3", "pip", "claude", "apt-get"}),  # no gh
        )

        def _subproc_run(cmd, **kwargs):
            if tuple(str(c) for c in cmd[:4]) == (
                    sys.executable, "-m", "pip", "--version"):
                return _fake_proc(0)
            if cmd[0] == "apt-get":
                raise FileNotFoundError(2, "apt-get vanished")
            return _fake_proc(0)

        monkeypatch.setattr(wizard.subprocess, "run", _subproc_run)
        monkeypatch.setattr(
            wizard.importlib.util, "find_spec", _find_spec_from({"fastapi"}))
        (tmp_path / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
        result = wizard.provision_deps(ids=["gh"], base_dir=tmp_path)
        # structured dict, not an exception
        assert result["ok"] is False
        gh = next(r for r in result["results"] if r["id"] == "gh")
        assert gh["returncode"] == 127


class TestPython3OnPath:
    """Finding 3: a bare `python` is only accepted after a 3.x version probe."""

    def test_python3_present_is_true(self, monkeypatch):
        monkeypatch.setattr(wizard.shutil, "which", _which_from({"python3"}))
        assert wizard._python3_on_path() is True

    def test_no_python_at_all_is_false(self, monkeypatch):
        monkeypatch.setattr(wizard.shutil, "which", _which_from(set()))
        assert wizard._python3_on_path() is False

    def test_python2_only_is_false(self, monkeypatch):
        # `python` resolves but is NOT our interpreter and probes as py2.
        monkeypatch.setattr(wizard.shutil, "which", _which_from({"python"}))
        monkeypatch.setattr(wizard.os.path, "realpath", lambda p: f"/real/{p}")
        monkeypatch.setattr(wizard, "_run",
                            lambda cmd, **k: _fake_proc(1))  # py2 -> nonzero
        assert wizard._python3_on_path() is False

    def test_python3_via_version_probe_is_true(self, monkeypatch):
        monkeypatch.setattr(wizard.shutil, "which", _which_from({"python"}))
        monkeypatch.setattr(wizard.os.path, "realpath", lambda p: f"/real/{p}")
        monkeypatch.setattr(wizard, "_run",
                            lambda cmd, **k: _fake_proc(0))  # py3 -> zero
        assert wizard._python3_on_path() is True


class TestProvisionBrewEnv:
    """Finding 2: provision passes HOMEBREW_NO_AUTO_UPDATE so `brew install`
    doesn't run a slow auto-update."""

    def test_homebrew_no_auto_update_forwarded(self, tmp_path, monkeypatch):
        monkeypatch.setattr(wizard.platform, "system", lambda: "Darwin")
        monkeypatch.setattr(
            wizard.shutil, "which",
            _which_from({"python3", "pip", "claude", "brew"}),  # no gh
        )
        captured = {}

        def _run(cmd, **kwargs):
            if tuple(str(c) for c in cmd[:4]) == (
                    sys.executable, "-m", "pip", "--version"):
                return _fake_proc(0)
            captured["env"] = kwargs.get("env")
            return _fake_proc(0)

        monkeypatch.setattr(wizard, "_run", _run)
        monkeypatch.setattr(
            wizard.importlib.util, "find_spec", _find_spec_from({"fastapi"}))
        (tmp_path / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
        wizard.provision_deps(ids=["gh"], base_dir=tmp_path)
        assert captured["env"]["HOMEBREW_NO_AUTO_UPDATE"] == "1"
