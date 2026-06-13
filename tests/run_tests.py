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

# Currently-red files quarantined out of the gate. Triage/fix tracked in #11503
# (gate went dead at the v0.44.0 cutover, masking these). Reasons are the
# first-failure cause; full detail in .squidsquad/skill/planning/11394-reasons.txt.
KNOWN_FAILURES = {
    "test_references": "asserts removed v1 references/agent-instructions.md — #11503",
    "test_state_bus": "asserts git pull --rebase; code is --no-rebase per never-rebase rule — #11503",
    "test_comms_sub_skills": "chat-etiquette.md heading-format assertion (possibly real) — #11503",
    "test_event_mode_fragments": "expects includes.yml to list common/boot-bootstrap (v2 changed includes) — #11503",
    "test_cycle_pre": "asserts 'verifier' in alias set; #6274 rename partial — #11503 / #6274",
    "test_4792_fragment_hygiene": "asserts removed 'sole liveness signal' phrase in composed skill — #11503",
    "test_deterministic_qa_framework": "asserts '\"Deferred\"' in composed QA (drifted) — #11503",
    "test_dm_verify_before_block": "reads removed references/sub-skills/roles/dm/prohibitions.md — #11503",
    "test_own_domain_autofix": "asserts removed v1 {{include:}} directive syntax (#11049 Path A) — #11503",
    "test_vault_synthesis": "asserts 'create-task' in restructured pm source (drifted) — #11503",
    "test_pickup_comment_fidelity_9946": "reads removed references/roles/dev/includes.yml (pre-rename) — #11503",
    "test_terminology_dual_aware_6274": "asserts pre-rename ('dev','skill'); #6274 landed → ('worker','skill') — #11503",
    "test_compose_a2f_10492": "compose section-list golden drifted — #11503",
    "test_atomic_emit_b7": "compose section-list golden drifted — #11503",
    "test_a3_golden_link_stage": "compose golden drifted — #11503",
    "test_compose_author_comments_11142": "asserts boot-bootstrap wrapper marker in restructured worker/instructions.md — #11503",
    "test_config_functions": "SAMPLE_CONFIG fixture missing new FIELD_MAP entries (code-review-model, effort-*, event-driven) — #11503",
    "test_agent_boundaries": "asserts removed responsibility.md + 'Know each other's responsibilities' phrase — #11503",
    "test_feat_9588_lazy_load_bootstrap": "asserts removed '## Boot — Mode Detection (#9588)' heading — #11503",
    "test_stale_tracker_files_ref": "reads removed references/sub-skills/roles/pm/prohibitions.md — #11503",
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
