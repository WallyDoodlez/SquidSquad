"""#13514 — INDEPENDENT verifier test plan (QA, not the worker's).

The worker's tests (tests/test_13514_setup_yes_surfaces_compose_failure.py) STUB
`scaffold_install` and hardcode ``claude_md == "FAILED"``. That proves the fix's
reaction to a FAILED marker but NOT that the real `scaffold_install` actually
emits that marker on a genuine per-role compose failure — the exact seam the fix
depends on. These tests close that gap by driving the REAL `scaffold_install`
(and the REAL `cmd_setup_yes`) with `compose.deploy_role_v2` patched to raise,
against a throwaway temp target so nothing in the live clone is touched.

AC map (from the #13514 issue body "Fix direction", derived independently):
  AC1  cmd_setup_yes returns non-zero when any role fails to compose
  AC2  a FAILED summary line distinct from "Created N agent(s)" is printed
  AC3  "Created N" counts only agents that produced a valid CLAUDE.md
  AC4  a stubbed failing deploy makes cmd_setup_yes return non-zero (regression)
"""
import os
import sys

import pytest

SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "references", "scripts")
sys.path.insert(0, SCRIPTS)

import wizard  # noqa: E402
import compose  # noqa: E402


class _GhMiss:
    """gh not consulted — force repo_info to fall back to the target dir name."""
    returncode = 1
    stdout = ""
    stderr = ""


def _offline(monkeypatch):
    monkeypatch.setattr(wizard, "ensure_labels", lambda dry_run=False: {"created": 0})
    monkeypatch.setattr(wizard, "_run", lambda *a, **k: _GhMiss())


# ---- SEAM: does the REAL scaffold_install emit claude_md == "FAILED"? ----------

def test_real_scaffold_install_records_FAILED_when_deploy_raises(tmp_path, monkeypatch):
    """TC-S: The seam the worker stubbed. With deploy_role_v2 raising for EVERY
    role, the real scaffold_install must tag every agent claude_md == 'FAILED'."""
    def boom(*a, **k):
        raise RuntimeError("simulated compose blocker (e.g. #13513 missing catalog)")
    monkeypatch.setattr(compose, "deploy_role_v2", boom)

    spec = wizard.generate_default_spec({}, {"name": "seamprobe"})
    result = wizard.scaffold_install(spec, tmp_path, overwrite_existing=True)

    agents = result["agents"]
    assert agents, "spec must yield at least one agent"
    assert all(a["claude_md"] == "FAILED" for a in agents), (
        "real scaffold_install must record claude_md=='FAILED' on deploy failure; "
        f"got {[a['claude_md'] for a in agents]}"
    )


def test_real_scaffold_install_records_real_path_on_success(tmp_path, monkeypatch):
    """TC-S2: negative control — a succeeding deploy records a real path string,
    never the bare 'FAILED' sentinel (so the fix's == check can't false-positive)."""
    def ok(compose_name, target_root=None, output_name=None):
        p = os.path.join(str(target_root), ".squidsquad", output_name, "CLAUDE.md")
        return p
    monkeypatch.setattr(compose, "deploy_role_v2", ok)

    spec = wizard.generate_default_spec({}, {"name": "okprobe"})
    result = wizard.scaffold_install(spec, tmp_path, overwrite_existing=True)
    assert all(a["claude_md"] != "FAILED" for a in result["agents"])


# ---- FULL E2E: real cmd_setup_yes end-to-end (no scaffold_install stub) --------

def test_e2e_cmd_setup_yes_all_roles_fail(tmp_path, monkeypatch, capsys):
    """TC-1 (AC1+AC2+AC3): every role's REAL deploy fails -> rc!=0, Created 0,
    distinct FAILED/ERROR output, and the 'is installed' banner is suppressed."""
    def boom(*a, **k):
        raise RuntimeError("simulated compose blocker")
    monkeypatch.setattr(compose, "deploy_role_v2", boom)
    _offline(monkeypatch)

    rc = wizard.cmd_setup_yes([str(tmp_path)])
    out = "".join(capsys.readouterr())

    assert rc != 0, "AC1: non-zero exit when all roles fail"
    assert "Created 0 agent" in out, "AC3: Created reflects zero composed agents"
    assert "failed to compose" in out.lower(), "AC2: distinct failure summary"
    assert "is installed" not in out, "success banner must be suppressed"


def test_e2e_cmd_setup_yes_partial_failure(tmp_path, monkeypatch, capsys):
    """TC-2 (AC1+AC3): only the PM role's REAL deploy fails; the rest compose for
    real. Created must count only the composed agents and rc must still be !=0."""
    real_deploy = compose.deploy_role_v2

    def selective(compose_name, target_root=None, output_name=None):
        if output_name == "pm" or compose_name == "pm":
            raise RuntimeError("simulated pm compose failure")
        return real_deploy(compose_name, target_root=target_root, output_name=output_name)
    monkeypatch.setattr(compose, "deploy_role_v2", selective)
    _offline(monkeypatch)

    rc = wizard.cmd_setup_yes([str(tmp_path)])
    out = "".join(capsys.readouterr())

    assert rc != 0, "AC1: any per-role failure -> non-zero"
    assert "FAILED to compose" in out, "AC2: failure surfaced in the Created line"
    # exactly one role failed, so Created must be (total agents - 1), never total.
    assert "Created 0 agent" not in out, "at least one role composed for real"
    assert "pm" in out, "AC2: the ERROR names the failed role id"


def test_e2e_cmd_setup_yes_all_roles_compose(tmp_path, monkeypatch, capsys):
    """TC-3 (control): a fully-real successful install returns 0, no FAILED text."""
    _offline(monkeypatch)  # deploy_role_v2 NOT patched — real compose for all roles

    rc = wizard.cmd_setup_yes([str(tmp_path)])
    out = "".join(capsys.readouterr())

    assert rc == 0, "a fully-composed install returns 0"
    assert "FAILED" not in out, "no failure text on a clean install"
    assert "Created" in out and "agent" in out
