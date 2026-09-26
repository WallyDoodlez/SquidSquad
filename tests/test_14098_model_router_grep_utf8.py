"""#14098 — model_router's agentic grep tool decoded rg output with the
locale default (cp1252 on Windows). An unmappable UTF-8 byte (0x9d, from a
right double quote) crashed subprocess's stdout reader thread mid-review.

The fake below reproduces Windows' decode on every OS: it decodes rg's real
UTF-8 bytes with whatever encoding the caller asked for, defaulting to strict
cp1252 exactly like an un-configured Windows text-mode pipe.
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))

import model_router  # noqa: E402

RG_OUTPUT = "references/x.py:1:says “quoted” — done\n".encode("utf-8")


def fake_run(cmd, **kw):
    enc = kw.get("encoding") or "cp1252"
    errors = kw.get("errors") or "strict"
    out = RG_OUTPUT.decode(enc, errors) if kw.get("text") else RG_OUTPUT
    return subprocess.CompletedProcess(cmd, 0, stdout=out, stderr="")


def test_grep_decodes_rg_output_as_utf8(monkeypatch):
    monkeypatch.setattr(model_router.subprocess, "run", fake_run)
    out = model_router._tool_grep({"pattern": "quoted", "path": "references",
                                   "output_mode": "content"})
    assert "“quoted”" in out
    assert not out.startswith("ERROR")


def test_grep_tolerates_missing_stdout(monkeypatch):
    """A decode failure in the reader thread leaves stdout None; the tool
    must report no matches, not an AttributeError."""
    monkeypatch.setattr(
        model_router.subprocess, "run",
        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, stdout=None, stderr=""))
    assert model_router._tool_grep({"pattern": "x"}) == "No matches found."
