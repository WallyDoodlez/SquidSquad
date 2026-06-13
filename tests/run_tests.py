#!/usr/bin/env python3
"""SquidSquad Test Runner.

Usage:
    python tests/run_tests.py              # Run all tests (static + integration)
    python tests/run_tests.py static       # Run static analysis only (pytest)
    python tests/run_tests.py harness      # Run harness self-tests only
    python tests/run_tests.py status_flow  # Run E2E status flow only
    python tests/run_tests.py --cleanup    # Just run cleanup (no tests)

Teardown runs automatically after integration tests, even on failure.
Static analysis tests do not require cleanup (no side effects).
"""

import subprocess
import sys
import unittest
from pathlib import Path

# Windows consoles default to cp1252, which cannot encode the em-dash / arrow
# characters used in the static-gate NOTICE reasons (#11394). Force UTF-8 so a
# cosmetic NOTICE line can never crash the gate with a UnicodeEncodeError.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # already-wrapped or non-reconfigurable
        pass

# Ensure tests/ and tests/integration/ are on the path
TESTS_DIR = Path(__file__).resolve().parent
INTEGRATION_DIR = TESTS_DIR / "integration"
sys.path.insert(0, str(TESTS_DIR))
sys.path.insert(0, str(INTEGRATION_DIR))

from integration.harness import cleanup_all, verify_clean

# ---------------------------------------------------------------------------
# Static-gate test discovery (#11394)
#
# The static gate AUTO-DISCOVERS every top-level tests/test_*.py file rather
# than tracking a hand-maintained allowlist. The old STATIC_TEST_MODULES list
# drifted two ways: (1) new test files were forgotten and ran in no gate; (2) a
# deleted file left a dangling entry that broke pytest collection (0 tests
# collected — the gate silently passed nothing, which is exactly how #11503's
# 23-file red set went unnoticed after the v0.44.0 cutover). Auto-discovery
# closes both: the glob only ever yields files that EXIST (a deleted test can
# never break collection again), and every new test file is gated the moment it
# lands unless explicitly excluded below.
#
# Exclusions are explicit, reasoned, and printed as a NOTICE on every run. Three
# layers (their completeness + file-existence is enforced by the AC3 regression
# test tests/test_11394_static_discovery.py):
#   LIVE_SUFFIX      — *_live.py tests hit live network / GitHub / model APIs;
#                      not part of the offline static gate. Matched by suffix.
#   KNOWN_NON_STATIC — valid tests that cannot run in the fast offline static
#                      context (spawn live-model agents, recurse into the full
#                      suite). Run via their own harness.
#   KNOWN_FAILURES   — files that currently fail and are NOT fixed here; each
#                      carries an issue ref. Remove an entry when its issue
#                      lands so the gate re-includes the file automatically.
# Every KNOWN_* entry MUST name an existing file and carry a non-empty reason.
# ---------------------------------------------------------------------------

LIVE_SUFFIX = "_live"

# Valid tests that don't belong in the fast offline static gate.
KNOWN_NON_STATIC = {
    "test_comprehension_1428": "spawns live model via run_comprehension_test.py — CQ harness, not static",
    "test_comprehension_2181": "spawns live model via run_comprehension_test.py — CQ harness, not static",
    "test_comprehension_2183": "spawns live model via run_comprehension_test.py — CQ harness, not static",
    "test_comprehension_2195": "spawns live model via run_comprehension_test.py — CQ harness, not static",
    "test_comprehension_361": "spawns live model via run_comprehension_test.py — CQ harness, not static",
    "test_comprehension_4792": "spawns live model via run_comprehension_test.py — CQ harness, not static",
    "test_comprehension_9184": "spawns live model via run_comprehension_test.py — CQ harness, not static",
    "test_feat_6581_wizard_reframing": "test_tc_10b recursively invokes run_tests.py (full suite incl integration) — unsuitable for static gate; #11503",
}

# Currently-red files quarantined out of the gate. The post-cutover stale-test
# debt (gate went dead at the v0.44.0 cutover, masking these; full detail in
# .squidsquad/skill/planning/11394-reasons.txt) has been worked down under
# #11503. The REMAINING two entries are NOT stale-test debt: they are tests
# that correctly fail on genuinely-incomplete work tracked by OPEN #10360
# (Implement Responsibility compose slot per COMPOSE-ARCHITECTURE §5.2). They
# clear only once #10360 lands the Responsibility slot — do NOT paper over by
# weakening assertions. See the #11503 comment for the full triage.
KNOWN_FAILURES = {
    "test_compose_author_comments_11142": "test_10360_cleanup_markers_preserved: #10360-cleanup breadcrumbs (future-work pointers for OPEN #10360) dropped by #11331 rewrite — blocked on #10360 (the stale boot-bootstrap-marker half is fixed)",
    "test_agent_boundaries": "test_ac7: 20 L3 variant responsibility stubs missing (COMPOSE-ARCH §5.2) — blocked on OPEN #10360. The other 19 assertions (ac4/ac6/ac11) are superseded by the agent-boundaries sub-skill retirement; rewrite the file together once #10360 unblocks it",
}


def discover_static_modules():
    """Auto-discover the static-gate test set (#11394): sorted stems of every
    top-level tests/test_*.py file minus the documented exclusions. Globbing
    existing files means a deleted test can never break collection again."""
    all_stems = {p.stem for p in TESTS_DIR.glob("test_*.py")}
    excluded = (
        {s for s in all_stems if s.endswith(LIVE_SUFFIX)}
        | set(KNOWN_NON_STATIC)
        | set(KNOWN_FAILURES)
    )
    return sorted(all_stems - excluded)


def run_cleanup_only():
    print("Running cleanup...")
    counts = cleanup_all()
    print(f"  Issues cleaned: {counts['issues']}")
    print(f"  Branches cleaned: {counts['branches']}")
    print(f"  Files cleaned: {counts['files']}")
    problems = verify_clean()
    if problems:
        print(f"  WARNING: {problems}")
    else:
        print("  All clean.")


def run_static_tests():
    """Run static analysis tests via pytest (auto-discovered — #11394)."""
    print("\n=== Static Analysis Tests (pytest) ===\n")
    modules = discover_static_modules()
    # Guard: an empty module list would make pytest fall back to recursive
    # auto-discovery from cwd, running EVERY test (incl _live, integration, and
    # the very files we excluded) — silently defeating the exclusion mechanism.
    # An empty gate is always a misconfiguration, so fail fast (#11394).
    if not modules:
        print(
            "ERROR: static-gate discovery returned 0 modules — gate "
            "configuration is broken (all test_*.py excluded?). Refusing to "
            "fall back to recursive auto-discovery."
        )
        return False
    excluded = (
        [(name, "non-static", reason) for name, reason in sorted(KNOWN_NON_STATIC.items())]
        + [(name, "known-failure", reason) for name, reason in sorted(KNOWN_FAILURES.items())]
    )
    live_n = sum(1 for p in TESTS_DIR.glob(f"test_*{LIVE_SUFFIX}.py"))
    if excluded or live_n:
        print(
            f"NOTICE: gating {len(modules)} static test file(s); "
            f"{len(excluded)} excluded by allowlist + {live_n} *_live (run separately):"
        )
        for name, kind, reason in excluded:
            print(f"  - {name} [{kind}]: {reason}")
        print()
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-v", "--tb=short"]
        + [str(TESTS_DIR / f"{mod}.py") for mod in modules],
        cwd=str(TESTS_DIR.parent),
    )
    return result.returncode == 0


def run_integration_tests(targets):
    """Run integration tests via unittest."""
    print("\n=== Integration Tests (unittest) ===\n")
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    if not targets or "harness" in targets:
        from integration import test_harness
        suite.addTests(loader.loadTestsFromModule(test_harness))

    if not targets or "status_flow" in targets:
        from integration import test_status_flow
        suite.addTests(loader.loadTestsFromModule(test_status_flow))

    if not targets or "event_mode_e2e" in targets:
        from integration import test_event_mode_e2e
        suite.addTests(loader.loadTestsFromModule(test_event_mode_e2e))

    if not targets or "agent_subprocess" in targets:
        from integration import test_event_mode_agent_subprocess
        suite.addTests(
            loader.loadTestsFromModule(test_event_mode_agent_subprocess)
        )

    if not targets or "real_agent_subprocess" in targets:
        # #9398 Phase A real-subprocess scenarios. Heavy — spawns real
        # harness + agent subprocesses; ~10-15s per test on Windows.
        from integration import test_9398_real_agent_subprocess
        suite.addTests(
            loader.loadTestsFromModule(test_9398_real_agent_subprocess)
        )

    if not targets or "gh_shim_tracker" in targets:
        # #9398 Phase A — gh PATH-shim ↔ tracker.py handshake.
        # Subprocess-spawns tracker.py with shim on PATH; fast.
        from integration import test_9398_gh_shim_tracker_integration
        suite.addTests(
            loader.loadTestsFromModule(
                test_9398_gh_shim_tracker_integration
            )
        )

    runner = unittest.TextTestRunner(verbosity=2)
    try:
        result = runner.run(suite)
    finally:
        print("\n--- Post-test cleanup ---")
        counts = cleanup_all()
        print(f"  Issues: {counts['issues']}, Branches: {counts['branches']}, Files: {counts['files']}")
        problems = verify_clean()
        if problems:
            print(f"  WARNING: Artifacts remain: {problems}")
        else:
            print("  All test artifacts cleaned up.")

    return result.wasSuccessful()


def main():
    if "--cleanup" in sys.argv:
        run_cleanup_only()
        return 0

    targets = [a for a in sys.argv[1:] if not a.startswith("-")]
    static_only = targets == ["static"]
    integration_only = any(
        t in targets for t in ("harness", "status_flow", "event_mode_e2e", "agent_subprocess")
    )

    all_passed = True

    # Static analysis tests (always run first unless only integration requested)
    if not integration_only:
        if not run_static_tests():
            all_passed = False

    # Integration tests (skip if static-only)
    if not static_only:
        integration_targets = [t for t in targets if t != "static"]
        if not run_integration_tests(integration_targets):
            all_passed = False

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
