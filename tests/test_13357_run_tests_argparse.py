"""Regression tests for #13357 — tests/run_tests.py must validate its CLI:
`--help` prints usage and exits 0 (instead of silently launching the full
~5400-test static suite), and an unknown arg / typo'd mode is rejected with a
non-zero exit instead of running the wrong thing.

Backward-compat is the hard constraint: every prior invocation
(no-args / `static` / a target name / `--cleanup`) must still parse the same.
"""
import sys
import unittest
from pathlib import Path

# run_tests.py lives in tests/ alongside this file.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_tests  # noqa: E402


class TestRunTestsArgParsing13357(unittest.TestCase):
    def setUp(self):
        self.parser = run_tests._build_arg_parser()

    # --- backward-compatible valid invocations ---
    def test_no_args_runs_everything(self):
        args = self.parser.parse_args([])
        self.assertEqual(args.targets, [])
        self.assertFalse(args.cleanup)

    def test_static_only(self):
        self.assertEqual(self.parser.parse_args(["static"]).targets, ["static"])

    def test_integration_target(self):
        args = self.parser.parse_args(["event_mode_e2e"])
        self.assertEqual(args.targets, ["event_mode_e2e"])

    def test_every_registered_target_is_valid(self):
        for name in run_tests.INTEGRATION_TARGET_NAMES:
            self.assertEqual(self.parser.parse_args([name]).targets, [name])

    def test_multiple_targets(self):
        args = self.parser.parse_args(["static", "harness"])
        self.assertEqual(args.targets, ["static", "harness"])

    def test_cleanup_flag(self):
        self.assertTrue(self.parser.parse_args(["--cleanup"]).cleanup)

    # --- the #13357 fixes ---
    def test_help_exits_zero(self):
        with self.assertRaises(SystemExit) as cm:
            self.parser.parse_args(["--help"])
        self.assertEqual(cm.exception.code, 0)

    def test_unknown_target_rejected(self):
        with self.assertRaises(SystemExit) as cm:
            self.parser.parse_args(["staitc"])  # typo of "static"
        self.assertEqual(cm.exception.code, 2)

    def test_unknown_flag_rejected(self):
        with self.assertRaises(SystemExit) as cm:
            self.parser.parse_args(["--bogus"])
        self.assertEqual(cm.exception.code, 2)

    def test_valid_target_mixed_with_typo_rejected(self):
        with self.assertRaises(SystemExit):
            self.parser.parse_args(["static", "nope"])


if __name__ == "__main__":
    unittest.main()
