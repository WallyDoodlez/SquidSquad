"""Drift guard: requirements.txt must declare every runtime third-party
import the harness needs (#11403 AC4).

Static (``ast``-based) — does NOT import the harness or its dependencies, so
it runs even when watchdog / fastapi / uvicorn are not installed (which is the
exact failure mode #11403 fixes). It catches a NEW third-party import added to
the harness runtime surface without a matching requirements.txt entry.
"""

import ast
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "references" / "scripts"
REQUIREMENTS = REPO_ROOT / "requirements.txt"

# Harness runtime modules to scan: the server itself plus the L4 file-watch
# subsystem it supervises (watchdog is lazily imported there, not in harness.py
# directly — but it IS a harness runtime dependency).
RUNTIME_MODULES = ["harness.py", "l4_file_watcher.py"]

# import-name -> distribution-name for the rare cases they differ. Our current
# deps all match their import name; the hook keeps the guard correct if e.g.
# a module imported as `yaml` (dist `pyyaml`) ever becomes a harness runtime
# dependency.
IMPORT_TO_DIST = {
    "yaml": "pyyaml",
}


def _local_module_names() -> set[str]:
    """Module names that resolve to local references/scripts/ files."""
    return {p.stem for p in SCRIPTS.glob("*.py")}


def _imported_top_modules(path: Path) -> set[str]:
    """Top-level module names imported anywhere in `path` — including guarded
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
    for raw in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
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
    for module_file in RUNTIME_MODULES:
        for mod in _imported_top_modules(SCRIPTS / module_file):
            if mod in stdlib or mod in local or mod.startswith("_"):
                continue
            third.add(mod)
    return third


def test_requirements_txt_exists():
    assert REQUIREMENTS.exists(), (
        "requirements.txt (runtime deps) is missing — #11403 declares the "
        "harness runtime dependencies there."
    )


def test_runtime_third_party_imports_are_declared():
    """Every third-party import on the harness runtime surface must be
    declared in requirements.txt. Fails loudly on drift."""
    declared = _declared_dists()
    missing = []
    for mod in sorted(_third_party_imports()):
        dist = IMPORT_TO_DIST.get(mod, mod).lower()
        if dist not in declared:
            missing.append(f"{mod} (distribution: {dist})")
    assert not missing, (
        "Harness runtime imports not declared in requirements.txt: "
        + ", ".join(missing)
        + ". Add them to requirements.txt (or extend IMPORT_TO_DIST if the "
        "import name differs from the PyPI distribution name)."
    )


def test_known_harness_deps_present():
    """Explicit pin: the three deps #11403 declared must stay declared."""
    declared = _declared_dists()
    for required in ("fastapi", "uvicorn", "watchdog"):
        assert required in declared, (
            f"{required} missing from requirements.txt — it is a harness "
            "runtime dependency (#11403)."
        )
