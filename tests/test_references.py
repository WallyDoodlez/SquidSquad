"""Static analysis: Verify reference file consistency.

Checks that reference files (hints, statusline, agent-instructions)
are consistent with their live copies in .squidsquad/.
"""

import pytest
from pathlib import Path

from conftest import REPO_ROOT, SQUIDSQUAD_DIR, REFERENCES_DIR


class TestHintFiles:
    """Verify hints files exist and are non-empty."""

    # #6274 D5: roles renamed dev→worker, qa→verifier in this sub-phase.
    # Reference side: only canonical post-rename names. Live side may still
    # have legacy {dev,qa} names on installs that haven't run wizard D4
    # — test_live_hints_match_reference skips when the live file is absent.
    @pytest.mark.parametrize("role", ["worker", "verifier", "dm", "pm"])
    def test_reference_hints_exist(self, role):
        path = REFERENCES_DIR / f"hints-{role}.txt"
        assert path.exists(), f"Missing reference hints: {path}"
        assert path.stat().st_size > 0, f"Empty hints file: {path}"

    # #6274 D5: roles renamed dev→worker, qa→verifier in this sub-phase.
    # Reference side: only canonical post-rename names. Live side may still
    # have legacy {dev,qa} names on installs that haven't run wizard D4
    # — test_live_hints_match_reference skips when the live file is absent.
    @pytest.mark.parametrize("role", ["worker", "verifier", "dm", "pm"])
    def test_live_hints_match_reference(self, role):
        ref = REFERENCES_DIR / f"hints-{role}.txt"
        live = SQUIDSQUAD_DIR / f"hints-{role}.txt"
        if not live.exists():
            pytest.skip(f"Live hints-{role}.txt not deployed yet")
        ref_content = ref.read_text(encoding="utf-8")
        live_content = live.read_text(encoding="utf-8")
        assert ref_content == live_content, (
            f"hints-{role}.txt differs between references/ and .squidsquad/. "
            "Copy reference to live after changes."
        )


class TestStatusline:
    """Verify statusline script exists and is valid."""

    def test_statusline_exists(self):
        path = REFERENCES_DIR / "statusline.sh"
        assert path.exists(), "Missing statusline.sh in references/"

    def test_statusline_has_shebang(self):
        content = (REFERENCES_DIR / "statusline.sh").read_text(encoding="utf-8")
        assert content.startswith("#!/"), "statusline.sh missing shebang"


class TestAgentInstructions:
    """Verify agent-instructions.md exists and has sub-skill markers."""

    def test_agent_instructions_exists(self):
        path = REFERENCES_DIR / "agent-instructions.md"
        assert path.exists(), "Missing agent-instructions.md in references/"

    def test_has_sub_skill_markers(self):
        content = (REFERENCES_DIR / "agent-instructions.md").read_text(encoding="utf-8")
        assert "<!-- sub-skill:" in content, (
            "agent-instructions.md has no sub-skill markers — "
            "may not be composed from sub-skills"
        )


class TestRunTestsModuleList:
    """#5435 regression: all STATIC_TEST_MODULES entries must exist as files."""

    def test_all_static_test_modules_exist(self):
        """Every entry in STATIC_TEST_MODULES must have a corresponding .py file."""
        import sys
        sys.path.insert(0, str(REPO_ROOT / "tests"))
        from run_tests import STATIC_TEST_MODULES

        tests_dir = REPO_ROOT / "tests"
        missing = [
            m for m in STATIC_TEST_MODULES
            if not (tests_dir / f"{m}.py").exists()
        ]
        assert missing == [], (
            f"STATIC_TEST_MODULES references nonexistent test files: {missing}. "
            "Remove stale entries or restore the missing files."
        )
