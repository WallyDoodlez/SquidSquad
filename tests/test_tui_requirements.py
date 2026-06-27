"""Drift guard: requirements-tui.txt must declare every third-party import the
SquidSquad TUI (references/tui/) needs at runtime (#12801 S1.4).

The TUI is a SEPARATE operator-launched process (the #8704 model) — it is NOT
imported by the harness runtime, so its dependency (textual) deliberately does
NOT live in requirements.txt (harness runtime, guarded by
tests/test_runtime_requirements.py) nor requirements-dev.txt (pytest/dev-only).
It lives in its own requirements-tui.txt, and this guard keeps that file honest.

Static (``ast``-based) — does NOT import the TUI or ``textual``, so it runs in
the static gate even where textual is not installed (the TUI dep is optional).
It catches a NEW third-party import added under references/tui/ without a
matching requirements-tui.txt entry.
"""

import ast
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TUI_DIR = REPO_ROOT / "references" / "tui"
REQUIREMENTS_TUI = REPO_ROOT / "requirements-tui.txt"

# import-name -> distribution-name for the rare cases they differ. The TUI's
# current deps match their import name; the hook keeps the guard correct if a
# module whose import name differs from its PyPI distribution ever lands here.
IMPORT_TO_DIST: dict[str, str] = {}


def _tui_py_files() -> list[Path]:
    return sorted(TUI_DIR.glob("*.py"))


def _local_module_names() -> set[str]:
    """Module names that resolve to local references/tui/ files (e.g. app.py
    importing ``harness_client`` — a sibling, not a third-party dep)."""
    return {p.stem for p in _tui_py_files()}


def _imported_top_modules(path: Path) -> set[str]:
    """Top-level module names imported anywhere in ``path`` — including guarded
    (try/except) and lazy (in-function) imports, which ``ast.walk`` reaches."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mods.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            # Absolute imports only (level == 0); relative imports are local.
            if node.level == 0 and node.module:
                mods.add(node.module.split(".")[0])
    return mods


def _declared_dists() -> set[str]:
    dists: set[str] = set()
    for raw in REQUIREMENTS_TUI.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        name = re.split(r"[<>=!~ \[]", line, 1)[0].strip().lower()
        if name:
            dists.add(name)
    return dists


def _third_party_imports() -> set[str]:
    local = _local_module_names()
    stdlib = set(sys.stdlib_module_names)  # py3.10+
    third: set[str] = set()
    for module_file in _tui_py_files():
        for mod in _imported_top_modules(module_file):
            if mod in stdlib or mod in local or mod.startswith("_"):
                continue
            third.add(mod)
    return third


def test_requirements_tui_exists():
    assert REQUIREMENTS_TUI.exists(), (
        "requirements-tui.txt (TUI process deps) is missing — #12801 S1.4 "
        "declares the operator-TUI dependency there (NOT in requirements.txt)."
    )


def test_tui_third_party_imports_are_declared():
    """Every third-party import under references/tui/ must be declared in
    requirements-tui.txt. Fails loudly on drift."""
    declared = _declared_dists()
    missing = []
    for mod in sorted(_third_party_imports()):
        dist = IMPORT_TO_DIST.get(mod, mod).lower()
        if dist not in declared:
            missing.append(f"{mod} (distribution: {dist})")
    assert not missing, (
        "TUI third-party imports not declared in requirements-tui.txt: "
        + ", ".join(missing)
        + ". Add them to requirements-tui.txt (or extend IMPORT_TO_DIST if the "
        "import name differs from the PyPI distribution name)."
    )


def test_textual_declared():
    """Explicit pin: textual (the TUI framework) must stay declared — the TUI
    cannot run without it."""
    assert "textual" in _declared_dists(), (
        "textual missing from requirements-tui.txt — it is the TUI process's "
        "framework dependency (#12801)."
    )
