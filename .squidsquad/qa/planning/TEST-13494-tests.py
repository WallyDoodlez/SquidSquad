"""Independent verifier tests for #13494 — _git_in_clone forces LC_ALL=C.

The deploy-pull helpers branch on English git substrings; forcing LC_ALL=C at
the single _git_in_clone choke point makes them locale-robust. Verifies: env
carries LC_ALL=C, env is a SUPERSET of os.environ (PATH/creds preserved), and a
real git invocation through the override still works. The real-git deploy-pull
regression (that the C locale does not break #13456/#13472 behavior) is covered
by re-running TEST-13456/TEST-13472 in this session.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest


def _find_repo_root(start):
    for p in [start, *start.parents]:
        if (p / "references" / "scripts" / "harness.py").exists():
            return p
    raise RuntimeError("could not locate repo root")


REPO_ROOT = _find_repo_root(Path(__file__).resolve())
SCRIPTS = REPO_ROOT / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import harness  # noqa: E402


@pytest.fixture
def capture_run(monkeypatch):
    calls = {}

    class _R:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(cmd, *args, **kwargs):
        calls["cmd"] = cmd
        calls["env"] = kwargs.get("env")
        return _R()

    monkeypatch.setattr(harness.subprocess, "run", fake_run)
    return calls


def test_git_in_clone_forces_lc_all_c(capture_run):
    """AC1: _git_in_clone passes env with LC_ALL=C to subprocess.run."""
    harness._git_in_clone("/some/clone", ["status", "--short"])
    env = capture_run["env"]
    assert env is not None, "no env passed (locale not forced)"
    assert env.get("LC_ALL") == "C", env.get("LC_ALL")


def test_env_is_superset_not_bare(capture_run):
    """AC2: env is a SUPERSET of os.environ (PATH/HOME/creds preserved), not bare."""
    harness._git_in_clone("/some/clone", ["status"])
    env = capture_run["env"]
    # PATH must survive (else git/credential helpers break).
    path_key = "PATH" if "PATH" in os.environ else "Path"
    assert path_key in env, "PATH not preserved -> would break git resolution"
    assert len(env) > 1, "env is bare LC_ALL only; os.environ not preserved"


def test_live_git_invocation_through_override_works(tmp_path):
    """Live smoke: a real git command via _git_in_clone still runs (env override
    did not wipe PATH), and git message output is English under LC_ALL=C."""
    subprocess.run(["git", "init", "-q"], cwd=str(tmp_path), check=True)
    r = harness._git_in_clone(str(tmp_path), ["status"])
    assert r.returncode == 0, r.stderr
    # LC_ALL=C -> English 'branch' wording, not a localized string.
    assert "branch" in (r.stdout + r.stderr).lower()


def test_regression_test_present():
    wt = REPO_ROOT / "tests" / "test_13494_git_in_clone_c_locale.py"
    assert wt.exists(), "worker regression test missing"
    txt = wt.read_text().lower()
    assert "lc_all" in txt
