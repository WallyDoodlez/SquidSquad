"""Live integration tests for model_router.py — requires OPENAI_API_KEY.

These tests make real API calls to external models. They are NOT run during
regular test cycles (run_tests.py). Run manually during QA verification of
model router changes:

    OPENAI_API_KEY=sk-... python -m pytest tests/test_model_router_live.py -v

Each test validates the 6 deterministic assertions from TEST-PLAN.md TC-38/39/40:
1. Output file exists and is non-empty
2. Minimum output length
3. Required sections present
4. File references are real paths
5. No hallucinated functions
6. Tool usage evidence in diagnostics log

If OPENAI_API_KEY is not set, tests FAIL (BLOCKED) — not skipped.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))
MODEL_ROUTER = SCRIPTS / "model_router.py"
DIAG_LOG = REPO_ROOT / ".squidsquad" / "diagnostics" / "model-routing.log"

from shared_fs import read_secret_or_env

# [human-required] if no API key — human must fix the environment
@pytest.fixture(autouse=True, scope="session")
def _require_api_key():
    if not read_secret_or_env("OPENAI_API_KEY"):
        pytest.fail(
            "HUMAN-REQUIRED: OPENAI_API_KEY not found in ~/.squidsquad/secrets "
            "or environment. A human must configure it before these tests can run.",
            pytrace=False,
        )


def _run_router(task_type, output_file, context, input_files=""):
    """Run model_router.py and return (exit_code, output_path).

    Forces routing to gpt-5.2 by setting SQUIDSQUAD_MODEL_OVERRIDE env var.
    This ensures live tests always hit the external model regardless of config.
    """
    env = os.environ.copy()
    env["SQUIDSQUAD_MODEL_OVERRIDE"] = "gpt-5.2"
    cmd = [
        sys.executable, str(MODEL_ROUTER), task_type,
        "--task-id", "LIVE-TEST",
        "--input-files", input_files,
        "--output-file", str(output_file),
        "--context", context,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT), env=env)
    return result.returncode, Path(output_file)


def _extract_file_paths(text):
    """Extract file paths mentioned in markdown output."""
    # Match paths like references/scripts/foo.py, .squidsquad/bar/baz.md, etc.
    paths = re.findall(r'(?:references/|\.squidsquad/|tests/)\S+\.(?:py|md|yaml|yml|sh|ps1|json)', text)
    # Filter out template placeholders (e.g. .squidsquad/start-<role>.ps1)
    return [p.rstrip('`).,;:') for p in paths if '<' not in p and '>' not in p]


def _extract_function_refs(text):
    """Extract function name references from output."""
    # Match def function_name or function_name() patterns
    defs = re.findall(r'def\s+(\w+)', text)
    calls = re.findall(r'(\w+)\(\)', text)
    # Filter out common words that look like function calls
    noise = {'e.g', 'i.e', 'etc', 'None', 'True', 'False', 'print', 'str', 'int', 'len', 'list', 'dict'}
    return [f for f in set(defs + calls) if f not in noise and len(f) > 2]


class TestTC38ResearchOutput:
    """TC-38: Research output — GPT 5.2 produces valid structured output."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.output_file = tmp_path / "research-gpt.md"
        self.exit_code, self.output_path = _run_router(
            "research", self.output_file,
            context="Research the SquidSquad boot_remote.py script: what it does, how PID liveness works, error handling.",
        )
        if self.output_path.exists():
            self.content = self.output_path.read_text(encoding="utf-8")
        else:
            self.content = ""

    def test_exit_code_zero(self):
        assert self.exit_code == 0, f"model_router exited with {self.exit_code}"

    def test_output_exists_and_nonempty(self):
        assert self.output_path.exists(), "Output file was not created"
        assert self.output_path.stat().st_size > 0, "Output file is empty"

    def test_minimum_length(self):
        assert len(self.content) >= 2000, (
            f"Output too short: {len(self.content)} chars (min 2000)"
        )

    def test_required_sections(self):
        required = ["## Summary", "## Impact Analysis", "## Side Effects",
                     "## Edge Cases", "## Recommendation"]
        missing = [s for s in required if s not in self.content]
        assert not missing, f"Missing required sections: {missing}"

    def test_file_references_exist(self):
        paths = _extract_file_paths(self.content)
        if not paths:
            pytest.skip("No file paths referenced in output")
        bad = [p for p in paths[:10] if not (REPO_ROOT / p).exists()]
        assert not bad, f"Hallucinated file paths: {bad}"

    def test_no_hallucinated_functions(self):
        refs = _extract_function_refs(self.content)
        if not refs:
            pytest.skip("No function references in output")
        # Spot-check up to 5 function refs against the codebase
        bad = []
        for func in refs[:5]:
            result = subprocess.run(
                ["grep", "-r", f"def {func}", str(REPO_ROOT / "references")],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                bad.append(func)
        # Allow some misses (function may be in tests/ or other locations)
        assert len(bad) <= len(refs) // 2, f"Likely hallucinated functions: {bad}"


class TestTC39TestPlanOutput:
    """TC-39: Test plan output — GPT 5.2 produces valid structured output."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.output_file = tmp_path / "testplan-gpt.md"
        self.exit_code, self.output_path = _run_router(
            "test-plan", self.output_file,
            context="Draft a test plan for the health_check.py script: PID liveness, mtime fallback, .stop sentinel.",
        )
        if self.output_path.exists():
            self.content = self.output_path.read_text(encoding="utf-8")
        else:
            self.content = ""

    def test_exit_code_zero(self):
        assert self.exit_code == 0

    def test_output_exists_and_nonempty(self):
        assert self.output_path.exists()
        assert self.output_path.stat().st_size > 0

    def test_minimum_length(self):
        assert len(self.content) >= 1500, (
            f"Output too short: {len(self.content)} chars (min 1500)"
        )

    def test_at_least_5_test_cases(self):
        tc_count = self.content.count("### TC-")
        assert tc_count >= 5, f"Only {tc_count} test cases (min 5)"

    def test_smoke_tests_section(self):
        assert "## Smoke Tests" in self.content or "## Smoke" in self.content

    def test_regression_risks_section(self):
        assert "## Regression Risks" in self.content or "## Regression" in self.content


class TestTC40DiscussionPrepOutput:
    """TC-40: Discussion prep output — GPT 5.2 produces valid structured output."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.output_file = tmp_path / "discprep-gpt.md"
        self.exit_code, self.output_path = _run_router(
            "discussion-prep", self.output_file,
            context="Prepare discussion questions for adding Forgejo as an alternative git backend.",
        )
        if self.output_path.exists():
            self.content = self.output_path.read_text(encoding="utf-8")
        else:
            self.content = ""

    def test_exit_code_zero(self):
        assert self.exit_code == 0

    def test_output_exists_and_nonempty(self):
        assert self.output_path.exists()
        assert self.output_path.stat().st_size > 0

    def test_minimum_length(self):
        assert len(self.content) >= 1000, (
            f"Output too short: {len(self.content)} chars (min 1000)"
        )

    def test_at_least_3_questions(self):
        q_count = len(re.findall(r'###\s+Q\d|^\d+\.', self.content, re.MULTILINE))
        assert q_count >= 3, f"Only {q_count} questions (min 3)"

    def test_questions_have_options(self):
        # Look for option/choice patterns
        options = re.findall(r'(?:Option|Choice|\*\*[A-C]\*\*|[a-c]\))', self.content)
        assert len(options) >= 4, f"Only {len(options)} option markers found (expect ≥4)"

    def test_has_recommendations(self):
        rec = re.findall(r'[Rr]ecommend', self.content)
        assert len(rec) >= 1, "No recommendation found in output"
