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

# Ensure tests/ is on the path
TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))

from harness import cleanup_all, verify_clean

STATIC_TEST_MODULES = [
    "test_labels", "test_references", "test_manifest",
    "test_composition", "test_config", "test_roles", "test_vault",
]


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
    """Run static analysis tests via pytest."""
    print("\n=== Static Analysis Tests (pytest) ===\n")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-v", "--tb=short"]
        + [str(TESTS_DIR / f"{mod}.py") for mod in STATIC_TEST_MODULES],
        cwd=str(TESTS_DIR.parent),
    )
    return result.returncode == 0


def run_integration_tests(targets):
    """Run integration tests via unittest."""
    print("\n=== Integration Tests (unittest) ===\n")
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    if not targets or "harness" in targets:
        import test_harness
        suite.addTests(loader.loadTestsFromModule(test_harness))

    if not targets or "status_flow" in targets:
        import test_status_flow
        suite.addTests(loader.loadTestsFromModule(test_status_flow))

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
    integration_only = any(t in targets for t in ("harness", "status_flow"))

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
