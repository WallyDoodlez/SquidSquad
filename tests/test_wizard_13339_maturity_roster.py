"""#13339 — project-maturity probe + workflow→roster mapping heuristic.

docs/INSTALLER-RUNTIME.md §4 ("Adapting to an empty project") + §9 ("Steps 3 &
5–6 — mapping the workflow to a team") ask the installer to (a) detect where a
project sits — empty → scaffolded → established — so it can branch between
"elicit intent" and "analyze what exists", and (b) turn the discovered
stack/workflow into a proposed engineering-team shape.

This suite locks the two deterministic helpers that put a testable floor under
the agent's judgment:

- ``wizard.detect_maturity`` / ``detect-maturity`` — the three-tier classifier
  and its signal transparency, including the source-file boundary.
- ``wizard.propose_roster`` / ``propose-roster`` — worker count + specialization
  from the scan or an ``--intended`` type, with PM/DM/Verifier held as fixed
  singletons (the shipped manifests mark all three always_installed /
  show_in_roster:false; only the worker role carries a variant).
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))

import wizard  # noqa: E402

WIZARD_PY = REPO_ROOT / "references" / "scripts" / "wizard.py"


def _write(root, rel, content=""):
    p = Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# detect_maturity
# ---------------------------------------------------------------------------


class TestDetectMaturity(unittest.TestCase):
    def test_empty_project(self):
        with tempfile.TemporaryDirectory() as d:
            result = wizard.detect_maturity(d)
            self.assertEqual(result["maturity"], "empty")
            self.assertEqual(result["signals"]["source_file_count"], 0)
            self.assertFalse(result["signals"]["has_structure"])

    def test_a_lone_readme_is_still_empty(self):
        """Docs without code or structure don't lift a repo out of empty."""
        with tempfile.TemporaryDirectory() as d:
            _write(d, "README.md", "# my project\n")
            result = wizard.detect_maturity(d)
            self.assertEqual(result["maturity"], "empty")

    def test_scaffolded_manifest_plus_thin_code(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, "package.json", '{"name":"x"}')
            _write(d, "index.js", "const a = 1\n")
            _write(d, "app.js", "const b = 2\n")
            result = wizard.detect_maturity(d)
            self.assertEqual(result["maturity"], "scaffolded")
            self.assertEqual(result["signals"]["source_file_count"], 2)
            self.assertTrue(result["signals"]["has_structure"])
            self.assertFalse(result["signals"]["has_tests"])

    def test_established_by_source_count(self):
        with tempfile.TemporaryDirectory() as d:
            # >= _ESTABLISHED_MIN_SOURCE_FILES recognized source files, no tests.
            for i in range(wizard._ESTABLISHED_MIN_SOURCE_FILES):
                _write(d, f"mod_{i}.py", "x = 1\n")
            result = wizard.detect_maturity(d)
            self.assertEqual(result["maturity"], "established")

    def test_established_by_tests_even_when_small(self):
        """A test suite marks a project worth analyzing even below the count bar."""
        with tempfile.TemporaryDirectory() as d:
            _write(d, "main.py", "x = 1\n")
            _write(d, "conftest.py", "")  # repo_scan → pytest test framework
            result = wizard.detect_maturity(d)
            self.assertTrue(result["signals"]["has_tests"])
            self.assertEqual(result["maturity"], "established")

    def test_source_count_boundary(self):
        """Exactly the threshold is established; one below (no tests/structure)
        is scaffolded — the boundary is inclusive on the established side."""
        n = wizard._ESTABLISHED_MIN_SOURCE_FILES
        with tempfile.TemporaryDirectory() as d:
            for i in range(n):
                _write(d, f"f_{i}.py", "x=1\n")
            self.assertEqual(wizard.detect_maturity(d)["maturity"], "established")
        with tempfile.TemporaryDirectory() as d:
            for i in range(n - 1):
                _write(d, f"f_{i}.py", "x=1\n")
            self.assertEqual(wizard.detect_maturity(d)["maturity"], "scaffolded")

    def test_signals_block_is_transparent(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, "main.py", "x=1\n")
            sig = wizard.detect_maturity(d)["signals"]
            for key in ("source_file_count", "languages", "frameworks",
                        "package_managers", "has_tests", "has_structure"):
                self.assertIn(key, sig)


class TestDetectMaturityCli(unittest.TestCase):
    def _run(self, *args):
        proc = subprocess.run(
            [sys.executable, str(WIZARD_PY), "detect-maturity", *args],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=60, check=False,
        )
        return proc

    def test_cli_emits_ok_envelope(self):
        with tempfile.TemporaryDirectory() as d:
            proc = self._run(d)
            self.assertEqual(proc.returncode, 0)
            out = json.loads(proc.stdout)
            self.assertTrue(out["ok"])
            self.assertEqual(out["maturity"], "empty")


# ---------------------------------------------------------------------------
# propose_roster
# ---------------------------------------------------------------------------


class TestProposeRosterSingletons(unittest.TestCase):
    def test_pm_dm_verifier_always_one(self):
        r = wizard.propose_roster({"frameworks": ["django"]})["roster"]
        self.assertEqual(r["pm"], 1)
        self.assertEqual(r["dm"], 1)
        self.assertEqual(r["verifier"], 1)

    def test_verifier_never_gets_a_worker_style_count(self):
        """Verifier is fixed-singleton infra in the manifest (like pm/dm) — the
        heuristic only ever varies the worker roster, never a verifier count."""
        result = wizard.propose_roster(
            {"frameworks": ["nextjs", "django"], "languages": ["typescript", "python"]})
        self.assertEqual(result["roster"]["verifier"], 1)
        self.assertEqual(sorted(result["singletons"]), ["dm", "pm", "verifier"])
        # only workers is a list of varying length
        self.assertIsInstance(result["roster"]["workers"], list)


class TestProposeRosterFromScan(unittest.TestCase):
    def test_frontend_and_backend_two_workers(self):
        result = wizard.propose_roster(
            {"frameworks": ["nextjs", "django"], "languages": ["typescript", "python"]})
        shapes = sorted(w["shape"] for w in result["roster"]["workers"])
        self.assertEqual(shapes, ["backend", "frontend"])
        self.assertEqual(result["source"], "scan")

    def test_frontend_only_one_fe_worker(self):
        result = wizard.propose_roster(
            {"frameworks": ["nextjs"], "languages": ["typescript"]})
        workers = result["roster"]["workers"]
        self.assertEqual(len(workers), 1)
        self.assertEqual(workers[0]["shape"], "frontend")
        self.assertEqual(workers[0]["alias"], "fe")

    def test_backend_only_one_be_worker(self):
        result = wizard.propose_roster(
            {"frameworks": ["django"], "languages": ["python"]})
        workers = result["roster"]["workers"]
        self.assertEqual(len(workers), 1)
        self.assertEqual(workers[0]["shape"], "backend")

    def test_backend_language_alone_counts_as_backend(self):
        result = wizard.propose_roster({"languages": ["go"]})
        self.assertEqual(result["roster"]["workers"][0]["shape"], "backend")

    def test_frontend_framework_with_backend_lang_is_both(self):
        result = wizard.propose_roster(
            {"frameworks": ["react"], "languages": ["python"]})
        shapes = sorted(w["shape"] for w in result["roster"]["workers"])
        self.assertEqual(shapes, ["backend", "frontend"])

    def test_nothing_decisive_one_fullstack_worker(self):
        for scan in ({}, {"languages": ["typescript"]}):
            result = wizard.propose_roster(scan)
            workers = result["roster"]["workers"]
            self.assertEqual(len(workers), 1)
            self.assertEqual(workers[0]["shape"], "fullstack")
            self.assertEqual(workers[0]["alias"], "worker")


class TestProposeRosterFromIntended(unittest.TestCase):
    def test_both_two_workers(self):
        result = wizard.propose_roster(None, intended="both")
        aliases = sorted(w["alias"] for w in result["roster"]["workers"])
        self.assertEqual(aliases, ["be", "fe"])
        self.assertEqual(result["source"], "intended")

    def test_fullstack_one_worker(self):
        result = wizard.propose_roster(None, intended="fullstack")
        self.assertEqual(len(result["roster"]["workers"]), 1)
        self.assertEqual(result["roster"]["workers"][0]["alias"], "worker")

    def test_backend_and_frontend(self):
        self.assertEqual(
            wizard.propose_roster(None, intended="backend")["roster"]["workers"][0]["shape"],
            "backend")
        self.assertEqual(
            wizard.propose_roster(None, intended="frontend")["roster"]["workers"][0]["shape"],
            "frontend")

    def test_intended_is_case_insensitive(self):
        result = wizard.propose_roster(None, intended="Both")
        self.assertEqual(len(result["roster"]["workers"]), 2)

    def test_unknown_intended_is_not_ok(self):
        result = wizard.propose_roster(None, intended="sideways")
        self.assertFalse(result["ok"])
        self.assertIn("sideways", result["error"])


class TestProposeRosterCli(unittest.TestCase):
    def _run(self, *args):
        return subprocess.run(
            [sys.executable, str(WIZARD_PY), "propose-roster", *args],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=60, check=False,
        )

    def test_intended_both_ok(self):
        proc = self._run("--intended", "both")
        self.assertEqual(proc.returncode, 0)
        out = json.loads(proc.stdout)
        self.assertTrue(out["ok"])
        self.assertEqual(len(out["roster"]["workers"]), 2)

    def test_bad_intended_exits_nonzero(self):
        proc = self._run("--intended", "bogus")
        self.assertEqual(proc.returncode, 1)
        out = json.loads(proc.stdout)
        self.assertFalse(out["ok"])

    def test_unknown_flag_usage_error(self):
        proc = self._run("--nope")
        self.assertEqual(proc.returncode, 2)


if __name__ == "__main__":
    unittest.main()
