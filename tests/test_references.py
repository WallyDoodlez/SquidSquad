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
    """Verify the v2 shared instructions base exists and has sub-skill markers.

    #11503 rebind: v1 references/agent-instructions.md was removed in the
    L1-L4 compose migration.  The v2 equivalent is the shared base layer at
    references/roles/instructions.md, which carries the boot-bootstrap
    <!-- sub-skill: --> marker and is the common foundation assembled into
    every role's composed CLAUDE.md.
    """

    def test_agent_instructions_exists(self):
        # v2: monolithic agent-instructions.md was split; shared base is here.
        path = REFERENCES_DIR / "roles" / "instructions.md"
        assert path.exists(), (
            "Missing v2 shared base instructions at references/roles/instructions.md"
        )

    def test_has_sub_skill_markers(self):
        # v2: sub-skill markers live in per-layer instructions.md files.
        content = (REFERENCES_DIR / "roles" / "instructions.md").read_text(encoding="utf-8")
        assert "<!-- sub-skill:" in content, (
            "references/roles/instructions.md has no sub-skill markers — "
            "v2 shared base must contain at least one <!-- sub-skill: --> block"
        )


class TestRunTestsModuleList:
    """#5435 / #11394 regression: gate exclusion entries must name existing files.

    The hand-maintained STATIC_TEST_MODULES allowlist was replaced by
    auto-discovery (#11394). The original #5435 intent — no dangling references
    to deleted test files — now applies to the KNOWN_NON_STATIC / KNOWN_FAILURES
    exclusion dicts, since a stale entry there silently un-gates a file.
    """

    def test_no_stale_exclusion_entries(self):
        """Every KNOWN_NON_STATIC / KNOWN_FAILURES entry must name an existing file."""
        import sys
        sys.path.insert(0, str(REPO_ROOT / "tests"))
        from run_tests import KNOWN_NON_STATIC, KNOWN_FAILURES

        tests_dir = REPO_ROOT / "tests"
        missing = [
            m for m in (set(KNOWN_NON_STATIC) | set(KNOWN_FAILURES))
            if not (tests_dir / f"{m}.py").exists()
        ]
        assert missing == [], (
            f"Gate exclusion dicts reference nonexistent test files: {missing}. "
            "Remove stale entries (a deleted file should drop out of the gate, "
            "not linger in an exclusion list)."
        )
