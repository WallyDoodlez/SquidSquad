"""#14025 -- model_router error-exit contract: honest messages, no artifact.

The router printed "Falling back to Claude." on error paths while exiting
nonzero WITHOUT falling back (the fallback is the caller's job, triggered by
the exit code), and left a "# STATUS: error" stub at --output-file that at
least one live artifact-existence caller consumed as a completed review
(CODE-REVIEW-13890.md, 2026-07-20). Contract now pinned here: every error
exit (a) states that the CALLER falls back, never claiming an in-process
fallback, and (b) leaves NO file at --output-file -- including the mid-run
progress stub and any stale artifact from a prior run.
"""

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "references" / "scripts"))

import model_router  # noqa: E402


def _wire(monkeypatch, adapter, model="deepseek-chat"):
    monkeypatch.setattr(model_router, "get_model_for_task", lambda t: model)
    monkeypatch.setattr(model_router, "_load_provider_manifest",
                        lambda m: ("fake", {"auth": {}}))
    monkeypatch.setattr(model_router, "_ensure_deps", lambda m: None)
    monkeypatch.setattr(model_router, "_load_adapter", lambda m: adapter)
    monkeypatch.setattr(model_router, "_log_diagnostic", lambda e: None)


def _route(tmp_path, task_type="research"):
    inp = tmp_path / "input.md"
    inp.write_text("input\n", encoding="utf-8")
    out = tmp_path / "OUT.md"
    code = model_router.route(task_type, "14025-test", str(inp), str(out), "ctx")
    return code, out


class _RaisingAdapter:
    exc = RuntimeError("boom -- api exploded")

    @classmethod
    def call(cls, **kwargs):
        raise cls.exc


class _TimeoutAdapter:
    @staticmethod
    def call(**kwargs):
        raise TimeoutError("read timed out")


class _ShortAdapter:
    @staticmethod
    def call(**kwargs):
        return "too short"


class _GoodAdapter:
    @staticmethod
    def call(**kwargs):
        return "A perfectly reasonable long-form result about input.md. " * 10


class TestNoArtifactOnError:
    def test_api_error_exits_1_no_artifact(self, monkeypatch, tmp_path):
        _wire(monkeypatch, _RaisingAdapter)
        code, out = _route(tmp_path)
        assert code == 1
        assert not out.exists(), "error exit left a consumable artifact"

    def test_timeout_exits_3_no_artifact(self, monkeypatch, tmp_path):
        _wire(monkeypatch, _TimeoutAdapter)
        code, out = _route(tmp_path)
        assert code == 3
        assert not out.exists()

    def test_quality_gate_exits_1_no_artifact(self, monkeypatch, tmp_path):
        _wire(monkeypatch, _ShortAdapter)
        code, out = _route(tmp_path)
        assert code == 1
        assert not out.exists()

    def test_no_provider_discards_stale_artifact(self, monkeypatch, tmp_path):
        monkeypatch.setattr(model_router, "get_model_for_task", lambda t: "ghost-model")
        monkeypatch.setattr(model_router, "_load_provider_manifest", lambda m: (None, None))
        monkeypatch.setattr(model_router, "_log_diagnostic", lambda e: None)
        inp = tmp_path / "input.md"
        inp.write_text("input\n", encoding="utf-8")
        out = tmp_path / "OUT.md"
        out.write_text("# stale artifact from a prior run\n", encoding="utf-8")
        code = model_router.route("research", "14025-test", str(inp), str(out), "ctx")
        assert code == 1
        assert not out.exists(), "stale prior artifact survived an error exit"

    def test_claude_locked_delegate_discards_stale_artifact(self, monkeypatch, tmp_path):
        monkeypatch.setattr(model_router, "_log_diagnostic", lambda e: None)
        inp = tmp_path / "input.md"
        inp.write_text("input\n", encoding="utf-8")
        out = tmp_path / "OUT.md"
        out.write_text("# stale artifact\n", encoding="utf-8")
        # comprehension is CLAUDE_LOCKED -- route returns 1, caller uses Agent tool
        code = model_router.route("comprehension", "14025-test", str(inp), str(out), "ctx")
        assert code == 1
        assert not out.exists()

    def test_success_writes_artifact(self, monkeypatch, tmp_path):
        _wire(monkeypatch, _GoodAdapter)
        code, out = _route(tmp_path)
        assert code == 0
        assert "input.md" in out.read_text(encoding="utf-8")


class TestMessageHonesty:
    """No error path may claim an in-process fallback; each states that the
    CALLER falls back."""

    def _stderr(self, capsys):
        return capsys.readouterr().err

    def test_api_error_message(self, monkeypatch, tmp_path, capsys):
        _wire(monkeypatch, _RaisingAdapter)
        _route(tmp_path)
        err = self._stderr(capsys)
        assert "Falling back to Claude." not in err
        assert "caller falls back" in err

    def test_timeout_message(self, monkeypatch, tmp_path, capsys):
        _wire(monkeypatch, _TimeoutAdapter)
        _route(tmp_path)
        err = self._stderr(capsys)
        assert "Falling back to Claude." not in err
        assert "caller falls back" in err

    def test_quality_gate_message(self, monkeypatch, tmp_path, capsys):
        _wire(monkeypatch, _ShortAdapter)
        _route(tmp_path)
        err = self._stderr(capsys)
        assert "Falling back to Claude." not in err
        assert "caller falls back" in err

    def test_no_in_process_fallback_claim_anywhere(self):
        """Source-level pin: the misleading exact phrase is gone from every
        print in model_router (the quota banner's reworded line names the
        CALLER explicitly)."""
        src = (REPO / "references" / "scripts" / "model_router.py").read_text(
            encoding="utf-8")
        assert "Falling back to Claude." not in src


class TestDiscardHelper:
    def test_discard_absent_file_is_noop(self, tmp_path):
        model_router._discard_output_artifact(str(tmp_path / "nope.md"))

    def test_discard_removes_file(self, tmp_path):
        f = tmp_path / "x.md"
        f.write_text("y", encoding="utf-8")
        model_router._discard_output_artifact(str(f))
        assert not f.exists()
