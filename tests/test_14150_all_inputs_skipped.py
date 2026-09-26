"""#14150 -- a routed task whose inputs were ALL skipped fails instead of
passing silently.

`model_router route --task-type code-review --input-files <path>` with a path
outside the repository skipped the file (`SKIPPED: Path outside repository
boundary.`), the model saw no code, answered `NO_FINDINGS`, and the router
exited 0 (`success-sentinel`). The #14055 wrong-target guard exempts the
sentinel, so nothing caught it: a clean review of code nobody reviewed.

route() now classifies the inputs before any model call. When inputs were given
and none is readable (outside the repo, sensitive, or missing), it exits 2 (the
caller's Claude fallback fires), logs `all-inputs-skipped`, and leaves no
artifact. A partial skip only warns.
"""

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "references" / "scripts"))

import model_router  # noqa: E402

IN_REPO_FILE = "references/VERSION"


@pytest.fixture
def wired(monkeypatch):
    """Route with a fake provider; records adapter calls and diagnostics."""
    rec = {"calls": 0, "actions": [], "diag": [], "response": "NO_FINDINGS"}

    class FakeAdapter:
        @staticmethod
        def call(**kwargs):
            rec["calls"] += 1
            return rec["response"]

    monkeypatch.setattr(model_router, "get_model_for_task", lambda t: "deepseek-chat")
    monkeypatch.setattr(model_router, "_load_provider_manifest",
                        lambda m: ("fake", {"auth": {}}))
    monkeypatch.setattr(model_router, "_ensure_deps", lambda m: None)
    monkeypatch.setattr(model_router, "_load_adapter", lambda m: FakeAdapter)

    def diag(e):
        rec["actions"].append(e.get("action"))
        rec["diag"].append(e)
    monkeypatch.setattr(model_router, "_log_diagnostic", diag)
    return rec


def test_issue_repro_outside_repo_no_findings_is_not_a_pass(wired, tmp_path, capsys):
    """The exact #14150 repro: buggy code outside the repo, model says
    NO_FINDINGS -> previously exit 0; now exit 2 before the model is called."""
    bad = tmp_path / "add.py"
    bad.write_text("def add(a, b): return a - b\n", encoding="utf-8")
    out = tmp_path / "REVIEW.md"
    code = model_router.route("code-review", "14150", str(bad), str(out), "ctx")
    assert code == 2
    assert wired["calls"] == 0, "model must not be called with zero readable inputs"
    assert not out.exists()
    assert wired["actions"] == ["all-inputs-skipped"]
    assert "outside repository boundary" in wired["diag"][0]["skipped"][0]
    assert "every input file was skipped" in capsys.readouterr().err


def test_sensitive_only_input_fails(wired, tmp_path):
    out = tmp_path / "OUT.md"
    code = model_router.route("code-review", "14150", str(REPO / ".env"),
                              str(out), "ctx")
    assert code == 2 and wired["calls"] == 0
    assert "sensitive file" in wired["diag"][0]["skipped"][0]


def test_missing_in_repo_input_fails(wired, tmp_path):
    out = tmp_path / "OUT.md"
    code = model_router.route("code-review", "14150",
                              "references/does-not-exist-14150.patch",
                              str(out), "ctx")
    assert code == 2 and wired["calls"] == 0
    assert "not a readable file" in wired["diag"][0]["skipped"][0]


def test_unreadable_in_repo_input_fails(wired, tmp_path, monkeypatch):
    """DS F1: an existing file without read permission is skipped too (the
    reader would only produce an ERROR stub). os.access is stubbed because
    chmod 000 is not enforceable on Windows."""
    real_access = model_router.os.access
    monkeypatch.setattr(model_router.os, "access",
                        lambda p, m: False if p.endswith("VERSION") else real_access(p, m))
    out = tmp_path / "OUT.md"
    code = model_router.route("code-review", "14150", IN_REPO_FILE, str(out), "ctx")
    assert code == 2 and wired["calls"] == 0
    assert "not a readable file" in wired["diag"][0]["skipped"][0]


def test_exit_code_contract_documents_input_error():
    """DS F2: exit 2 is documented as config OR input error."""
    doc = model_router.__doc__ + model_router.route.__doc__
    assert "every input file skipped" in doc


def test_applies_to_every_task_type(wired, tmp_path):
    out = tmp_path / "OUT.md"
    assert model_router.route("research", "14150", str(tmp_path / "x.md"),
                              str(out), "ctx") == 2
    assert wired["calls"] == 0


def test_partial_skip_warns_and_continues(wired, tmp_path, capsys):
    """One readable in-repo input is enough: the call proceeds, with a warning
    naming the skipped one."""
    outside = tmp_path / "outside.patch"
    outside.write_text("x\n", encoding="utf-8")
    out = tmp_path / "OUT.md"
    code = model_router.route("code-review", "14150",
                              f"{IN_REPO_FILE},{outside}", str(out), "ctx")
    assert code == 0
    assert wired["calls"] == 1
    err = capsys.readouterr().err
    assert "WARNING: input" in err and "outside repository boundary" in err
    assert "all-inputs-skipped" not in wired["actions"]


def test_no_inputs_is_not_guarded(wired, tmp_path):
    """A task with no input files at all (context-only) is unaffected."""
    out = tmp_path / "OUT.md"
    assert model_router.route("research", "14150", "", str(out), "ctx") == 0
    assert wired["calls"] == 1


def test_classify_input_files():
    readable, skipped = model_router._classify_input_files(
        f"{IN_REPO_FILE}, ,/definitely/outside/x.py,{REPO / '.env'},"
        "references/nope-14150.md")
    assert readable == [IN_REPO_FILE]
    assert [r for _, r in skipped] == ["outside repository boundary",
                                       "sensitive file", "not a readable file"]
    assert model_router._classify_input_files("") == ([], [])
    assert model_router._classify_input_files(None) == ([], [])
