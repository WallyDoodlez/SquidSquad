"""#14181 -- the PM forge write-capability probe reads the pinned identity.

PM health-check and pipeline-sentinel halt class (e) told PM to run a bare
``gh api repos/:owner/:repo -q .permissions.push``. That reads gh's flippable
active account: live on 2026-09-26 it returned ``false`` (active account
Naahtec, read-only) while every tracker.py write succeeded under the #13865
pinned identity, which is a false "forge write-outage, escalate". The sub-skills now
call ``tracker.py write-probe``, which runs the same probe GH_TOKEN-pinned.

All subprocess calls mocked -- no real gh runs here.
"""

import re
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import gh_identity  # noqa: E402
import tracker  # noqa: E402


def _result(stdout="", returncode=0):
    r = MagicMock()
    r.stdout = stdout
    r.stderr = ""
    r.returncode = returncode
    return r


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
    monkeypatch.setattr(tracker, "_resolve_gh_bin", lambda: "gh")


def _arm(monkeypatch, verdict_for_token):
    """Fake gh: the push verdict depends on the GH_TOKEN the call carries,
    standing in for 'which identity gh used'. No GH_TOKEN = the active
    account."""
    calls = []

    def fake_run(cmd, **kw):
        env = kw.get("env") or {}
        calls.append((cmd, env.get("GH_TOKEN")))
        return _result(verdict_for_token(env.get("GH_TOKEN")))

    monkeypatch.setattr(tracker.subprocess, "run", fake_run)
    return calls


def test_read_only_active_account_does_not_mask_pinned_push(monkeypatch, capsys):
    # AC1: active account read-only (no GH_TOKEN -> "false"), pinned identity
    # has push -> the documented probe reports true.
    monkeypatch.setattr(gh_identity, "pinned_token", lambda: "pinned-tok")
    calls = _arm(monkeypatch, lambda tok: "true" if tok == "pinned-tok" else "false")
    assert tracker.write_probe() == 0
    assert capsys.readouterr().out.strip() == "true"
    cmd, tok = calls[-1]
    assert cmd[:3] == ["gh", "api", "repos/:owner/:repo"]
    assert ".permissions.push" in cmd
    assert tok == "pinned-tok"


def test_pinned_identity_without_push_reports_false(monkeypatch, capsys):
    # AC2: even with a push-capable active account, a pinned identity that
    # lost push reports false.
    monkeypatch.setattr(gh_identity, "pinned_token", lambda: "pinned-tok")
    _arm(monkeypatch, lambda tok: "false" if tok == "pinned-tok" else "true")
    assert tracker.write_probe() == 1
    assert capsys.readouterr().out.strip() == "false"


@pytest.mark.parametrize("stdout,rc", [("", 1), ("null", 0), ("", 124)])
def test_error_or_odd_output_is_inconclusive(monkeypatch, capsys, stdout, rc):
    monkeypatch.setattr(gh_identity, "pinned_token", lambda: "pinned-tok")
    monkeypatch.setattr(tracker.subprocess, "run",
                        lambda cmd, **kw: _result(stdout, rc))
    assert tracker.write_probe() == 2
    assert capsys.readouterr().out.strip() == "inconclusive"


def test_non_github_adapter_is_inconclusive(monkeypatch, capsys):
    monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: object())
    assert tracker.write_probe() == 2
    assert capsys.readouterr().out.strip() == "inconclusive"


def test_cli_dispatch_and_flag_table():
    assert tracker.KNOWN_FLAGS["write-probe"] == set()
    assert "tracker.py write-probe" in tracker.__doc__


def test_pm_sub_skills_call_write_probe_not_bare_gh():
    # AC3 audit: no sub-skill instructs the bare active-account probe; the
    # two PM consumers call the pinned one.
    bare = re.compile(r"^\s*gh api repos/:owner/:repo -q \.permissions\.push\s*$",
                      re.M)
    inline = re.compile(r"`gh api repos/:owner/:repo -q \.permissions\.push`")
    for md in (REPO_ROOT / "references").rglob("*.md"):
        text = md.read_text(encoding="utf-8")
        assert not bare.search(text), f"{md}: bare active-account probe"
        assert not inline.search(text), f"{md}: bare active-account probe"
    for name in ("health-check.md", "pipeline-sentinel.md"):
        text = (REPO_ROOT / "references/sub-skills/roles/pm" / name).read_text(
            encoding="utf-8")
        assert "tracker.py write-probe" in text, name
