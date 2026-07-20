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

import argparse
import os
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
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

from integration.integration_harness import cleanup_all, verify_clean

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
# #11503 established this registry; #13890 emptied it. The two long-standing
# entries (test_agent_boundaries, test_compose_author_comments_11142) framed
# their failures as "genuinely-incomplete #10360 work — hold red until #10360
# lands". #13890's root-cause traced every failing assertion to a DELIBERATE
# later cleanup that shipped without retiring its guard (#10366 deleted the 20
# L3 stubs as pure orphans; #13006 deleted the pm/dm L4 seeds; f8d867a9d
# removed the #10360-cleanup breadcrumbs after their migration completed; the
# lineage-tag and roster conventions retired with the agent-boundaries
# sub-skill). The guards were reconciled to the current contract in #13890 —
# assertions rewritten or retired with per-item evidence, NOT weakened-to-
# green — and #10360 remains tracked on its own issue, which is where future
# work belongs (a permanently-red test is signal debt, not a reminder). If
# #10360's slot migration reintroduces stub inventories, its PR ships its own
# guards. Add new entries here ONLY with an issue reference and a removal
# condition.
KNOWN_FAILURES = {}


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


def _static_gate_verdict(returncode, junit_path):
    """Decide PASS/FAIL for a static-gate pytest run WITHOUT trusting the
    process returncode alone (#12408).

    A test that hard-exits the pytest process mid-run (``os._exit(0)``,
    ``sys.exit(0)``, ``pytest.exit(..., returncode=0)``) forces returncode 0
    while skipping pytest's session teardown — so NO junit report is written
    (pytest emits it from ``pytest_sessionfinish``, which the hard-exit
    bypasses), the failure aggregation never runs, and the truncated run
    reports false-green. That is the #12408 bug: a real failure reached
    pending-test because ``run_static_tests()`` returned ``returncode == 0``.

    The durable defense is cause-agnostic: require positive proof the session
    finished — a parseable junit recording >0 tests with 0 failures/errors —
    and fail closed on anything else. A missing junit is the canonical
    mid-run-hard-exit signature (the session-finish hook never fired).

    Returns ``(passed: bool, reason: str)``.
    """
    if not junit_path.exists():
        return False, (
            "INCOMPLETE RUN — pytest never wrote its junit report, so the "
            "session did not reach session-finish (a gated test likely "
            "hard-exited the process mid-run via os._exit/sys.exit, forcing a "
            "false-green returncode 0). Failing the gate closed (#12408)."
        )
    try:
        root = ET.parse(junit_path).getroot()
    except ET.ParseError as exc:
        return False, (
            f"INCOMPLETE RUN — junit report is malformed ({exc}); the session "
            f"did not finish writing it. Failing the gate closed (#12408)."
        )
    # pytest's xunit2 wraps suites in <testsuites>; older/--junit-family=xunit1
    # uses a bare <testsuite> root. Handle both.
    if root.tag == "testsuites":
        suites = root.findall("testsuite")
    elif root.tag == "testsuite":
        suites = [root]
    else:
        suites = root.findall(".//testsuite")
    total = sum(int(s.get("tests", "0")) for s in suites)
    failures = sum(int(s.get("failures", "0")) for s in suites)
    errors = sum(int(s.get("errors", "0")) for s in suites)
    if total == 0:
        return False, (
            "INCOMPLETE RUN — junit recorded 0 tests; nothing executed "
            "(collection error or empty session). Failing the gate closed."
        )
    if failures or errors:
        return False, (
            f"{failures} failure(s) + {errors} error(s) across {total} gated "
            f"test(s)."
        )
    if returncode != 0:
        return False, (
            f"pytest returned non-zero ({returncode}) despite a clean junit — "
            f"failing the gate closed."
        )
    return True, f"{total} gated test(s) passed (0 failures, 0 errors)."


def run_static_tests():
    """Run static analysis tests via pytest (auto-discovered — #11394).

    The gate is fail-closed (#12408): it does not trust pytest's returncode
    alone but requires a complete junit report proving the session reached
    session-finish. See _static_gate_verdict for the rationale.
    """
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
    # Always emit a junit report to a unique temp path. Its later EXISTENCE is
    # our positive proof pytest reached session-finish; a mid-run hard-exit
    # leaves it absent (#12408). Unlink the empty mkstemp placeholder first so
    # only pytest itself can (re)create the file.
    junit_fd, junit_name = tempfile.mkstemp(prefix="sq_static_gate_", suffix=".xml")
    os.close(junit_fd)
    junit_path = Path(junit_name)
    junit_path.unlink()
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-v", "--tb=short",
             "--junit-xml", str(junit_path)]
            + [str(TESTS_DIR / f"{mod}.py") for mod in modules],
            cwd=str(TESTS_DIR.parent),
        )
        passed, reason = _static_gate_verdict(result.returncode, junit_path)
        print(f"\n[static-gate] {'PASS' if passed else 'FAIL'} — {reason}")
        return passed
    finally:
        if junit_path.exists():
            junit_path.unlink()


# #12903: single source of truth for integration target names + their
# modules. Both run_integration_tests() (dispatch) AND main()'s
# `integration_only` guard derive from this tuple, so the two can never
# drift again. (The bug: #9398 added the last two targets to the dispatch
# but not to the guard, so `run_tests.py real_agent_subprocess` fell through
# to run the full static gate first.)
_INTEGRATION_MODULES = (
    ("harness", "test_harness"),
    ("status_flow", "test_status_flow"),
    ("event_mode_e2e", "test_event_mode_e2e"),
    ("agent_subprocess", "test_event_mode_agent_subprocess"),
    # #9398 Phase A real-subprocess scenarios — heavy (spawns real harness +
    # agent subprocesses; ~10-15s per test on Windows).
    ("real_agent_subprocess", "test_9398_real_agent_subprocess"),
    # #9398 Phase A — gh PATH-shim <-> tracker.py handshake (subprocess-spawns
    # tracker.py with the shim on PATH; fast).
    ("gh_shim_tracker", "test_9398_gh_shim_tracker_integration"),
)
# Canonical integration target names — the only names both the guard and the
# dispatch recognize.
INTEGRATION_TARGET_NAMES = tuple(name for name, _ in _INTEGRATION_MODULES)


def run_integration_tests(targets):
    """Run integration tests via unittest."""
    print("\n=== Integration Tests (unittest) ===\n")
    import importlib
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Lazy per-target import preserved (modules import only when their target
    # runs) — now driven by the shared _INTEGRATION_MODULES registry.
    for name, module_name in _INTEGRATION_MODULES:
        if not targets or name in targets:
            module = importlib.import_module(f"integration.{module_name}")
            suite.addTests(loader.loadTestsFromModule(module))

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


def _build_arg_parser():
    """#13357: explicit argparse so ``--help`` prints usage (instead of silently
    launching the full ~5400-test static suite) and an unknown arg / typo'd mode
    (e.g. ``staitc``) is REJECTED with exit 2 instead of running the wrong thing.

    Backward-compatible with every prior invocation:
      run_tests.py               -> static gate + all integration (the default)
      run_tests.py static        -> static gate only
      run_tests.py <target>...   -> those integration target(s) only
      run_tests.py --cleanup     -> cleanup only
    Targets are restricted to the known set (``static`` + the integration
    registry), so a mistyped mode is caught rather than silently no-op'd.
    """
    valid_targets = ["static", *INTEGRATION_TARGET_NAMES]
    parser = argparse.ArgumentParser(
        prog="run_tests.py",
        description="SquidSquad test runner (static gate + integration suites).",
        epilog=(
            "modes: no args = static gate + all integration; "
            "'static' = static gate only (~5400 gated tests, several minutes); "
            "a target name runs that integration suite only "
            f"(targets: {', '.join(INTEGRATION_TARGET_NAMES)}). "
            "The config.md 'Tests' command uses the bare integration mode "
            "(~53 tests, ~70s)."
        ),
    )
    parser.add_argument(
        "targets", nargs="*", choices=valid_targets, metavar="TARGET",
        help="test target(s) to run; omit to run static + all integration",
    )
    parser.add_argument(
        "--cleanup", action="store_true",
        help="run test-artifact cleanup only, then exit",
    )
    return parser


def main(argv=None):
    args = _build_arg_parser().parse_args(sys.argv[1:] if argv is None else argv)
    if args.cleanup:
        run_cleanup_only()
        return 0

    targets = args.targets
    static_only = targets == ["static"]
    # #12903: derive from the shared registry so the guard always matches the
    # set of targets run_integration_tests() actually dispatches.
    integration_only = any(t in targets for t in INTEGRATION_TARGET_NAMES)

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
