"""#12450 Surface 2 — wiring the detected test strategy into the install spec
and the L4 project seed.

`repo_scan.detect_test_strategy` (Surface 1, tested in test_repo_scan.py) returns
``{framework, run_command, location, coverage, detected}``. This file covers the
wizard side:

- ``generate_default_spec`` prefers ``test_strategy.run_command`` over the legacy
  four-framework heuristic, falling back when the strategy is absent/undetected.
- ``_write_l4_project_files`` reads the persisted ``.repo-scan.json`` and emits a
  '### Testing Strategy' block (run command + framework + location) so workers
  reference the detected strategy instead of inventing one — and falls back
  gracefully (legacy '### Test Command' line) when nothing was detected, which is
  also the non-software-dev / empty-repo path (AC4: no invented command).
"""

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "references" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import wizard


class TestGenerateDefaultSpecTestCommand(unittest.TestCase):
    def _skill_agent(self, spec):
        return next(a for a in spec["agents"] if a["role"] == "worker")

    def test_prefers_test_strategy_run_command(self):
        scan = {
            "test_strategy": {
                "framework": "pytest",
                "run_command": "pytest tests/",
                "location": "tests/",
                "coverage": None,
                "detected": True,
            },
            "test_frameworks": ["pytest"],
        }
        spec = wizard.generate_default_spec(scan_data=scan)
        self.assertEqual(self._skill_agent(spec)["test_command"], "pytest tests/")

    def test_strategy_run_command_beats_legacy_heuristic(self):
        """A go-test run_command (no entry in the 4-framework heuristic) must win."""
        scan = {
            "test_strategy": {
                "framework": "go test",
                "run_command": "go test ./...",
                "location": None,
                "coverage": None,
                "detected": True,
            },
            "test_frameworks": [],  # legacy heuristic would yield ""
        }
        spec = wizard.generate_default_spec(scan_data=scan)
        self.assertEqual(self._skill_agent(spec)["test_command"], "go test ./...")

    def test_falls_back_to_legacy_when_no_strategy(self):
        """Older scan artifacts without test_strategy still resolve via heuristic."""
        scan = {"test_frameworks": ["jest"]}
        spec = wizard.generate_default_spec(scan_data=scan)
        self.assertEqual(self._skill_agent(spec)["test_command"], "npx jest")

    def test_falls_back_when_strategy_undetected(self):
        scan = {
            "test_strategy": {"run_command": "", "detected": False},
            "test_frameworks": ["pytest"],
        }
        spec = wizard.generate_default_spec(scan_data=scan)
        self.assertEqual(self._skill_agent(spec)["test_command"], "pytest")

    def test_detected_but_empty_run_command_falls_back(self):
        """DS-F3: detected=True but no run_command (test files found, no runnable
        command) must NOT yield an empty test_command — fall to the heuristic."""
        scan = {
            "test_strategy": {"framework": "pytest", "run_command": "",
                              "location": "tests/", "detected": True},
            "test_frameworks": ["pytest"],
        }
        spec = wizard.generate_default_spec(scan_data=scan)
        self.assertEqual(self._skill_agent(spec)["test_command"], "pytest")

    def test_no_test_data_yields_empty_command(self):
        spec = wizard.generate_default_spec(scan_data={})
        self.assertEqual(self._skill_agent(spec)["test_command"], "")


class TestFormatTestStrategySection(unittest.TestCase):
    def test_detected_emits_specifics(self):
        section = wizard._format_test_strategy_section(
            {
                "framework": "pytest",
                "run_command": "pytest tests/",
                "location": "tests/",
                "coverage": "pytest-cov",
                "detected": True,
            },
            fallback_command=None,
        )
        self.assertIn("### Testing Strategy", section)
        self.assertIn("pytest tests/", section)
        self.assertIn("pytest-cov", section)
        self.assertIn("tests/", section)
        self.assertIn("do not invent", section.lower())

    def test_undetected_emits_legacy_line_with_fallback(self):
        section = wizard._format_test_strategy_section(
            {"detected": False}, fallback_command="make test"
        )
        self.assertIn("### Test Command", section)
        self.assertIn("make test", section)
        self.assertNotIn("Testing Strategy", section)

    def test_undetected_no_fallback_is_not_detected(self):
        section = wizard._format_test_strategy_section({}, fallback_command=None)
        self.assertIn("Not detected", section)

    def test_backtick_in_run_command_is_sanitized(self):
        """DS-F1: a backtick in the run command must not break the inline-code
        span (it would corrupt the generated markdown)."""
        section = wizard._format_test_strategy_section(
            {"run_command": "echo `id`", "framework": "x",
             "location": "y", "detected": True},
            fallback_command=None,
        )
        self.assertNotIn("`id`", section)
        self.assertIn("echo 'id'", section)


class TestWriteL4ReadsRepoScan(unittest.TestCase):
    def _make_spec(self):
        return {
            "project": {"name": "demo"},
            "agents": [
                {"id": "skill", "alias": "skill", "role": "worker",
                 "stack": "Go", "test_command": "go test ./..."},
            ],
        }

    def test_reads_repo_scan_and_emits_strategy_section(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            squid = Path(td) / ".squidsquad"
            project_dir = squid / "project"
            project_dir.mkdir(parents=True)
            (squid / ".repo-scan.json").write_text(json.dumps({
                "test_strategy": {
                    "framework": "go test",
                    "run_command": "go test ./...",
                    "location": "co-located *_test.go",
                    "coverage": None,
                    "detected": True,
                }
            }), encoding="utf-8")
            summary = {}
            wizard._write_l4_project_files(self._make_spec(), project_dir, summary)
            content = (project_dir / "shared-stack-details.md").read_text(
                encoding="utf-8")
            self.assertIn("### Testing Strategy", content)
            self.assertIn("go test ./...", content)
            self.assertIn("co-located *_test.go", content)

    def test_missing_repo_scan_falls_back_gracefully(self):
        """No .repo-scan.json (e.g. non-software-dev / empty repo, AC4) → legacy
        line from the per-agent test_command, no crash, no invented strategy."""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            project_dir = Path(td) / ".squidsquad" / "project"
            project_dir.mkdir(parents=True)
            summary = {}
            wizard._write_l4_project_files(self._make_spec(), project_dir, summary)
            content = (project_dir / "shared-stack-details.md").read_text(
                encoding="utf-8")
            self.assertIn("### Test Command", content)
            self.assertIn("go test ./...", content)
            self.assertNotIn("### Testing Strategy", content)

    def test_malformed_repo_scan_falls_back_gracefully(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            squid = Path(td) / ".squidsquad"
            project_dir = squid / "project"
            project_dir.mkdir(parents=True)
            (squid / ".repo-scan.json").write_text("{ not json", encoding="utf-8")
            summary = {}
            wizard._write_l4_project_files(self._make_spec(), project_dir, summary)
            content = (project_dir / "shared-stack-details.md").read_text(
                encoding="utf-8")
            self.assertIn("### Test Command", content)


class TestFormatScanSummaryTestStrategy(unittest.TestCase):
    """#12450 S3 — the scan summary surfaces the richer detected test strategy
    (run command / location / coverage), so the wizard can confirm it with the
    operator and detect the undetectable (ask-human) case."""

    def test_detected_strategy_surfaced(self):
        scan = {
            "languages": ["Python"],
            "test_strategy": {
                "run_command": "pytest -q",
                "location": "tests/",
                "coverage": "coverage.py",
                "detected": True,
            },
        }
        out = wizard.format_scan_summary(scan)
        self.assertIn("**Test Strategy**", out)
        self.assertIn("pytest -q", out)
        self.assertIn("tests/", out)
        self.assertIn("coverage.py", out)

    def test_undetected_strategy_no_line(self):
        scan = {
            "languages": ["Python"],
            "test_strategy": {"detected": False},
        }
        out = wizard.format_scan_summary(scan)
        self.assertNotIn("**Test Strategy**", out)

    def test_absent_strategy_no_crash(self):
        out = wizard.format_scan_summary({"languages": ["Go"]})
        self.assertNotIn("**Test Strategy**", out)

    def test_detected_but_empty_fields_no_line(self):
        """detected=True but no run_command/location/coverage → no empty line."""
        scan = {"languages": ["Python"], "test_strategy": {"detected": True}}
        out = wizard.format_scan_summary(scan)
        self.assertNotIn("**Test Strategy**", out)


class TestSetTestStrategyCLI(unittest.TestCase):
    """#12450 S3 — the undetectable ask-human path persists the operator's answer
    into .repo-scan.json (the source of truth all downstream consumers read)."""

    def _scan_path(self, td):
        return Path(td) / ".squidsquad" / ".repo-scan.json"

    def test_writes_strategy_to_fresh_repo_scan(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            rc = wizard.cmd_set_test_strategy(
                ["--run-command", "pytest -q", "--framework", "pytest",
                 "--location", "tests/", td])
            self.assertEqual(rc, 0)
            data = json.loads(self._scan_path(td).read_text(encoding="utf-8"))
            ts = data["test_strategy"]
            self.assertTrue(ts["detected"])
            self.assertEqual(ts["source"], "human")
            self.assertEqual(ts["run_command"], "pytest -q")
            self.assertEqual(ts["framework"], "pytest")
            self.assertEqual(ts["location"], "tests/")
            self.assertEqual(data["test_command"], "pytest -q")

    def test_merges_into_existing_repo_scan(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            sp = self._scan_path(td)
            sp.parent.mkdir(parents=True)
            sp.write_text(json.dumps({"languages": ["Python"]}), encoding="utf-8")
            rc = wizard.cmd_set_test_strategy(["--run-command", "npm test", td])
            self.assertEqual(rc, 0)
            data = json.loads(sp.read_text(encoding="utf-8"))
            self.assertEqual(data["languages"], ["Python"])  # preserved
            self.assertEqual(data["test_strategy"]["run_command"], "npm test")
            self.assertTrue(data["test_strategy"]["detected"])

    def test_run_command_required(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            rc = wizard.cmd_set_test_strategy(["--framework", "pytest", td])
            self.assertEqual(rc, 2)

    def test_flag_missing_value_errors(self):
        rc = wizard.cmd_set_test_strategy(["--run-command"])
        self.assertEqual(rc, 2)

    def test_unknown_flag_errors_not_swallowed_as_target(self):
        """A typo flag (e.g. --run-comand) must error, not be treated as a
        target dir — else the strategy writes to the wrong path silently."""
        rc = wizard.cmd_set_test_strategy(
            ["--run-command", "pytest", "--run-comand", "oops"])
        self.assertEqual(rc, 2)

    def test_malformed_existing_scan_overwritten_cleanly(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            sp = self._scan_path(td)
            sp.parent.mkdir(parents=True)
            sp.write_text("{ not json", encoding="utf-8")
            rc = wizard.cmd_set_test_strategy(["--run-command", "go test ./...", td])
            self.assertEqual(rc, 0)
            data = json.loads(sp.read_text(encoding="utf-8"))
            self.assertEqual(data["test_strategy"]["run_command"], "go test ./...")

    def test_registered_in_dispatch(self):
        """The command must be wired into main()'s dispatch table."""
        import inspect
        src = inspect.getsource(wizard.main)
        self.assertIn('"set-test-strategy": cmd_set_test_strategy', src)


if __name__ == "__main__":
    unittest.main()
