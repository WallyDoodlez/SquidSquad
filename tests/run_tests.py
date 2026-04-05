#!/usr/bin/env python3
"""SquidSquad Integration Test Runner.

Usage:
    python tests/run_tests.py              # Run all tests
    python tests/run_tests.py harness      # Run harness self-tests only
    python tests/run_tests.py status_flow  # Run E2E status flow only
    python tests/run_tests.py --cleanup    # Just run cleanup (no tests)

Teardown runs automatically after all tests, even on failure.
"""

import sys
import unittest
from pathlib import Path

# Ensure tests/ is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness import cleanup_all, verify_clean


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


def main():
    if "--cleanup" in sys.argv:
        run_cleanup_only()
        return 0

    # Determine which test modules to run
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    targets = [a for a in sys.argv[1:] if not a.startswith("-")]

    if not targets or "harness" in targets:
        import test_harness
        suite.addTests(loader.loadTestsFromModule(test_harness))

    if not targets or "status_flow" in targets:
        import test_status_flow
        suite.addTests(loader.loadTestsFromModule(test_status_flow))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    try:
        result = runner.run(suite)
    finally:
        # Always clean up, even on failure
        print("\n--- Post-test cleanup ---")
        counts = cleanup_all()
        print(f"  Issues: {counts['issues']}, Branches: {counts['branches']}, Files: {counts['files']}")
        problems = verify_clean()
        if problems:
            print(f"  WARNING: Artifacts remain: {problems}")
        else:
            print("  All test artifacts cleaned up.")

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
