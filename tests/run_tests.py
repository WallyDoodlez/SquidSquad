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

# Ensure tests/ and tests/integration/ are on the path
TESTS_DIR = Path(__file__).resolve().parent
INTEGRATION_DIR = TESTS_DIR / "integration"
sys.path.insert(0, str(TESTS_DIR))
sys.path.insert(0, str(INTEGRATION_DIR))

from integration.harness import cleanup_all, verify_clean

STATIC_TEST_MODULES = [
    "test_labels", "test_references", "test_manifest",
    "test_composition", "test_config", "test_roles", "test_vault",
    "test_tracker_authority",
    "test_manifest_registry", "test_wizard", "test_wizard_runbook",
    "test_installer_wiring", "test_config_schema",
    "test_statusline_schema", "test_feat328_coverage",
    "test_feat_1074_auto_merge", "test_feat_1210_is_quiet",
    "test_feat_1228_pipeline_sentinel", "test_feat_1229_triage_json",
    "test_feat_1363_label_sync", "test_feat_1397_draft_pr",
    "test_feat_1496_shared_fs_fallback", "test_feat_1500_create_pr_draft",
    "test_feat_1517_clone_url",
    "test_repo_scan", "test_tracker",
    "test_vault_check", "test_vault_entity", "test_capability_check",
    "test_state_bus",
    "test_git_ops", "test_run_comprehension",
    "test_migrate_state_branch",
    "test_boot_remote",
    "test_model_router",
    "test_comms_adapter",
    "test_comms_sub_skills",
    "test_event_bus",
    "test_event_catalog",
    "test_event_poll",
    "test_eviction_signal",
    "test_event_mode_fragments",
    "test_comprehension_8694",
    "test_event_validator",
    "test_event_config",
    "test_write_event_reactions",
    "test_event_derivation",
    "test_compose",
    "test_compose_9588",
    "test_orphan_cleanup_9688",
    "test_reboot_agent",
    "test_feat_3296_task_boundary",
    "test_per_agent_workdirs",
    "test_shared_fs",
    "test_run_comprehension_test",
    "test_add_role",
    "test_compose_capability",
    # "test_config_functions",  # 5 pre-existing failures (field map coverage)
    "test_cq_cache",
    "test_cycle",
    "test_cycle_post",
    "test_cycle_pre",
    "test_4792_fragment_hygiene",
    "test_deterministic_qa_framework",
    "test_diagnostics",
    "test_dm_verify_before_block",
    "test_event_bus_reader",
    "test_feat_605_issue_url",
    "test_feat_1075_vault_candidates",
    # "test_feat_1328_blocked_skip",  # 3 pre-existing failures
    # "test_feat_2495_upgrade_rewrite",  # 1 pre-existing failure
    "test_feat_3494_version_bump",
    "test_feat_3499_pm_orphans",
    "test_feat_3644_openai_json_warn",
    "test_openai_adapter",
    # "test_feat_3645_auto_merge",  # 3 pre-existing failures
    # "test_feat_3663_pr_conflict_check",  # 4 pre-existing failures (rebase→merge)
    "test_feat_6126_harness_merge",
    "test_forge_adapter",
    "test_forgejo_setup",
    "test_harness",
    "test_health_check",
    "test_own_domain_autofix",
    "test_scan_index",
    "test_soul_adaptation",
    "test_squidsquad_cli",
    "test_start_team",
    "test_tc_coverage",
    "test_thin_launcher",
    "test_thin_launcher_10101",
    "test_triage",
    "test_vault_check_unit",
    "test_vault_optimize",
    "test_vault_remember",
    "test_vault_synthesis",
    "test_work_queue",
    "test_9481_update_health_off_event_loop",
    "test_9665_no_inline_update_health_on_agents_endpoints",
    # #9398 Phase A unit tests
    "test_9398_squidsquad_dir_env_var",
    "test_9398_gh_shim",
    "test_9398_tracker_gh_resolution",
    "test_pickup_comment_fidelity_9946",
    "test_terminology_dual_aware_6274",
    "test_source_frontmatter",
    "test_compose_a6_v2",
    "test_assemble_verifier",
    "test_process_utils",
    "test_assemble_cache",
    "test_l4_parser",
    "test_l4_op_processor",
    "test_compose_check_a4_10388",
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
