"""Regression test for #12903 — run_tests.py integration target guard.

main()'s `integration_only` guard must recognize EVERY integration target
that run_integration_tests() dispatches. The two lists drifted when #9398
added `real_agent_subprocess` + `gh_shim_tracker` to the dispatch but not to
the guard, so `run_tests.py real_agent_subprocess` fell through to run the
full static gate first. Both now derive from the shared
`_INTEGRATION_MODULES` registry — these tests lock that invariant.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tests"))

import run_tests  # noqa: E402


EXPECTED_TARGETS = {
    "harness", "status_flow", "event_mode_e2e", "agent_subprocess",
    "real_agent_subprocess", "gh_shim_tracker",
}


def _is_integration_only(targets):
    """Mirror of main()'s guard expression, for isolated testing."""
    return any(t in targets for t in run_tests.INTEGRATION_TARGET_NAMES)


class TestIntegrationTargetGuard12903:
    def test_guard_recognizes_all_six_targets(self):
        assert set(run_tests.INTEGRATION_TARGET_NAMES) == EXPECTED_TARGETS

    def test_previously_omitted_targets_present(self):
        """The exact bug: these two were dispatched but not in the guard."""
        assert "real_agent_subprocess" in run_tests.INTEGRATION_TARGET_NAMES
        assert "gh_shim_tracker" in run_tests.INTEGRATION_TARGET_NAMES

    def test_each_target_alone_is_integration_only(self):
        """Invoking any single integration target must skip the static gate."""
        for name in run_tests.INTEGRATION_TARGET_NAMES:
            assert _is_integration_only([name]), name

    def test_static_and_empty_are_not_integration_only(self):
        assert not _is_integration_only(["static"])
        assert not _is_integration_only([])

    def test_guard_and_dispatch_share_one_source(self):
        """Drift-proofing: the guard names ARE the registry names — no second
        hand-maintained list that can fall out of sync again."""
        assert run_tests.INTEGRATION_TARGET_NAMES == tuple(
            name for name, _ in run_tests._INTEGRATION_MODULES
        )

    def test_registry_modules_exist_on_disk(self):
        """Catch a typo'd module name in the registry without importing the
        (heavy) integration modules."""
        integ = REPO_ROOT / "tests" / "integration"
        for name, module_name in run_tests._INTEGRATION_MODULES:
            assert (integ / f"{module_name}.py").exists(), (name, module_name)
