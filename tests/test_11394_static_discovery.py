"""#11394 regression: static-gate auto-discovery invariants.

The static gate (tests/run_tests.py) auto-discovers tests/test_*.py instead of
a hand-maintained STATIC_TEST_MODULES allowlist. These tests lock the two drift
modes the old list suffered:

  1. forgotten-add  — a new test_*.py file that no gate ran (silent ungating).
  2. deleted-listed — a dangling list entry pointing at a deleted file, which
                      aborted pytest collection (0 tests collected, gate dead).

The mechanism closes both. This suite asserts the invariants that keep it closed.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = REPO_ROOT / "tests"
sys.path.insert(0, str(TESTS_DIR))

from run_tests import (  # noqa: E402
    LIVE_SUFFIX,
    KNOWN_NON_STATIC,
    KNOWN_FAILURES,
    discover_static_modules,
)


def _all_top_level_stems():
    return {p.stem for p in TESTS_DIR.glob("test_*.py")}


def test_no_silent_ungating():
    """Every top-level test_*.py is accounted for: it is gated, or excluded by
    exactly one documented mechanism (live suffix / non-static / known-failure)."""
    all_stems = _all_top_level_stems()
    gated = set(discover_static_modules())
    live = {s for s in all_stems if s.endswith(LIVE_SUFFIX)}
    accounted = gated | live | set(KNOWN_NON_STATIC) | set(KNOWN_FAILURES)
    orphans = all_stems - accounted
    assert orphans == set(), (
        f"Test files neither gated nor documented-excluded (silent ungating): "
        f"{sorted(orphans)}. Add to the static gate (default) or to a "
        f"KNOWN_NON_STATIC/KNOWN_FAILURES entry with a reason."
    )


def test_gated_and_exclusions_are_disjoint():
    """A file is gated XOR excluded — never both."""
    gated = set(discover_static_modules())
    assert gated.isdisjoint(KNOWN_NON_STATIC), (
        f"Gated files also in KNOWN_NON_STATIC: {gated & set(KNOWN_NON_STATIC)}"
    )
    assert gated.isdisjoint(KNOWN_FAILURES), (
        f"Gated files also in KNOWN_FAILURES: {gated & set(KNOWN_FAILURES)}"
    )


def test_exclusion_entries_reference_existing_files():
    """Deleted-listed drift guard: every exclusion entry must name an existing
    file. A deleted test should drop out of the gate, not linger as a stale
    exclusion (the failure mode that killed the gate after the v0.44.0 cutover)."""
    missing = [
        m for m in (set(KNOWN_NON_STATIC) | set(KNOWN_FAILURES))
        if not (TESTS_DIR / f"{m}.py").exists()
    ]
    assert missing == [], (
        f"Exclusion dicts reference nonexistent files: {sorted(missing)}."
    )


def test_every_exclusion_has_a_reason():
    """Each exclusion must carry a non-empty reason (self-documenting allowlist)."""
    blank = [
        name for name, reason in {**KNOWN_NON_STATIC, **KNOWN_FAILURES}.items()
        if not (reason and reason.strip())
    ]
    assert blank == [], f"Exclusion entries missing a reason: {sorted(blank)}"


def test_discovery_only_returns_existing_files():
    """discover_static_modules() globs existing files, so a deleted test can
    never break collection again."""
    for stem in discover_static_modules():
        assert (TESTS_DIR / f"{stem}.py").exists(), (
            f"discover_static_modules() returned non-existent file: {stem}"
        )


def test_live_suffix_files_are_never_gated():
    """*_live.py tests are excluded by suffix, regardless of the dicts."""
    gated = set(discover_static_modules())
    gated_live = {s for s in gated if s.endswith(LIVE_SUFFIX)}
    assert gated_live == set(), (
        f"*_live tests must not be in the static gate: {sorted(gated_live)}"
    )


def test_gate_survives_a_deleted_gated_file(tmp_path, monkeypatch):
    """Simulate the cutover regression: a previously-gated file is deleted.
    Auto-discovery must simply omit it — no crash, no dangling reference."""
    import run_tests

    real_glob = type(TESTS_DIR).glob

    # Pretend one currently-gated file vanished from disk.
    gated = discover_static_modules()
    assert gated, "expected a non-empty gated set"
    vanished = gated[0]

    def fake_glob(self, pattern):
        for p in real_glob(self, pattern):
            if p.stem != vanished:
                yield p

    monkeypatch.setattr(type(TESTS_DIR), "glob", fake_glob)
    after = discover_static_modules()
    assert vanished not in after, "deleted file should drop out of the gate"
    # And the function still returns a coherent, all-existing set.
    assert all((TESTS_DIR / f"{s}.py").exists() for s in after)
