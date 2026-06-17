"""Regression guard for #12509 — no test module may shadow a
`references/scripts/` module basename.

The bug: `tests/integration/harness.py` (an integration cleanup helper) shared
the basename `harness` with `references/scripts/harness.py`. Under pytest's
default `prepend` import mode with no package `__init__.py`, a single
`pytest tests/` session imported the helper first, bound it as `harness` in
sys.modules, and every later unit test doing `from harness import HarnessState`
got the wrong module → collection interrupted. Fixed by renaming the helper to
`integration_harness.py`.

These tests fail if anyone re-introduces a colliding basename, which would once
again break a bare `pytest tests/`.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "references" / "scripts"
TESTS_DIR = REPO_ROOT / "tests"


def _module_basenames(directory):
    """Importable (non-dunder, non-__init__) .py basenames directly in *directory*."""
    return {
        p.stem
        for p in directory.glob("*.py")
        if not p.name.startswith("__")
    }


def test_renamed_helper_present_old_name_gone():
    """The integration helper lives at its non-colliding name, not `harness.py`."""
    assert not (TESTS_DIR / "integration" / "harness.py").exists(), (
        "tests/integration/harness.py shadows references/scripts/harness.py — "
        "the #12509 collision. Use a unique basename (integration_harness.py)."
    )
    assert (TESTS_DIR / "integration" / "integration_harness.py").exists(), (
        "the renamed integration helper is missing"
    )


def test_no_test_dir_module_shadows_a_scripts_module():
    """No module basename in tests/ or tests/integration/ collides with a
    references/scripts/ module — the general form of the #12509 shadow.

    `references/scripts/` is placed on sys.path (agents and many tests import
    its modules by bare name), so any same-basename module in a test dir that
    also lands on the path can shadow it in sys.modules during a combined run.
    """
    scripts = _module_basenames(SCRIPTS_DIR)
    for test_dir in (TESTS_DIR, TESTS_DIR / "integration"):
        # Exclude test_*.py / *_test.py — pytest imports those under their own
        # (unique, path-derived) names and they never bind a scripts basename.
        candidates = {
            stem for stem in _module_basenames(test_dir)
            if not stem.startswith("test_") and not stem.endswith("_test")
            and stem != "conftest"
        }
        collisions = candidates & scripts
        assert not collisions, (
            f"{test_dir.relative_to(REPO_ROOT)} has helper module(s) {sorted(collisions)} "
            f"that shadow references/scripts/ modules of the same name — a "
            f"#12509-class basename collision that breaks `pytest tests/`."
        )


def test_bare_harness_import_resolves_to_real_harness():
    """`import harness` resolves to references/scripts/harness.py (the agent
    supervisor), not a test helper — the exact symbol the victims needed.

    Isolation (QA cy251 + cy270 / #12509): assert resolution WITHOUT importing
    or executing the module. The earlier attempts popped `sys.modules['harness']`
    and did a live `import harness`, which RE-EXECUTES harness.py and creates a
    second, divergent module object — perturbing global import state beyond the
    one key we snapshotted, so a sibling like test_feat_10681's
    `patch("harness.HARNESS_STATE_FILE", ...)` ended up patching a different
    object than its collection-time `HarnessState` binding (order-dependent
    failures). `importlib.util.find_spec` resolves the module against sys.path
    and returns its origin WITHOUT executing it or mutating sys.modules — zero
    contamination, and it still proves the rename removed the basename shadow.
    """
    import importlib.util

    # Ensure the scripts dir is importable (idempotent; matches the codebase
    # pattern — many test modules add it permanently). This is a sys.path add,
    # not a sys.modules mutation, so it is not the contamination vector.
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))

    spec = importlib.util.find_spec("harness")
    assert spec is not None and spec.origin, "harness must be importable"
    assert Path(spec.origin).resolve() == (SCRIPTS_DIR / "harness.py").resolve(), (
        f"`import harness` must resolve to the real supervisor module, "
        f"got {spec.origin!r}"
    )
