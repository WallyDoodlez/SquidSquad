"""Static analysis: Verify start script correctness.

Checks that start scripts (bash + PowerShell) for each role have
correct --name flag handling, SQUIDSQUAD_ROLE injection, and
consistent structure.
"""

import re
import pytest
from pathlib import Path

from conftest import SQUIDSQUAD_DIR

# Roles that have start scripts
ROLES = ["skill", "pm", "dm", "qa", "designer"]


class TestStartScriptsExist:
    """All roles have both .sh and .ps1 start scripts."""

    @pytest.mark.parametrize("role", ROLES)
    def test_bash_script_exists(self, role):
        path = SQUIDSQUAD_DIR / f"start-{role}.sh"
        assert path.exists(), f"Missing start-{role}.sh"

    @pytest.mark.parametrize("role", ROLES)
    def test_ps1_script_exists(self, role):
        path = SQUIDSQUAD_DIR / f"start-{role}.ps1"
        assert path.exists(), f"Missing start-{role}.ps1"

    @pytest.mark.parametrize("role", ROLES)
    def test_bash_has_shebang(self, role):
        content = (SQUIDSQUAD_DIR / f"start-{role}.sh").read_text(encoding="utf-8")
        assert content.startswith("#!/bin/bash"), f"start-{role}.sh missing #!/bin/bash shebang"


class TestBashNameFlag:
    """Bash scripts correctly parse --name flag."""

    @pytest.mark.parametrize("role", ROLES)
    def test_has_name_flag_parsing(self, role):
        content = (SQUIDSQUAD_DIR / f"start-{role}.sh").read_text(encoding="utf-8")
        assert "--name)" in content, f"start-{role}.sh missing --name flag case"

    @pytest.mark.parametrize("role", ROLES)
    def test_shift_2_after_name(self, role):
        content = (SQUIDSQUAD_DIR / f"start-{role}.sh").read_text(encoding="utf-8")
        assert "shift 2" in content, (
            f"start-{role}.sh should 'shift 2' after --name to consume flag+value"
        )

    @pytest.mark.parametrize("role", ROLES)
    def test_falls_back_to_config_alias(self, role):
        content = (SQUIDSQUAD_DIR / f"start-{role}.sh").read_text(encoding="utf-8")
        assert f"config.py alias {role}" in content, (
            f"start-{role}.sh should read alias from config.py for {role}"
        )


class TestPS1NameFlag:
    """PowerShell scripts correctly parse --name flag."""

    @pytest.mark.parametrize("role", ROLES)
    def test_has_name_flag_parsing(self, role):
        content = (SQUIDSQUAD_DIR / f"start-{role}.ps1").read_text(encoding="utf-8")
        assert '"--name"' in content, f"start-{role}.ps1 missing --name flag parsing"

    @pytest.mark.parametrize("role", ROLES)
    def test_falls_back_to_config_alias(self, role):
        content = (SQUIDSQUAD_DIR / f"start-{role}.ps1").read_text(encoding="utf-8")
        assert f"config.py alias {role}" in content, (
            f"start-{role}.ps1 should read alias from config.py for {role}"
        )


class TestClaudeLaunchCommand:
    """Start scripts invoke claude with correct flags."""

    @pytest.mark.parametrize("role", ROLES)
    def test_bash_has_correct_role(self, role):
        content = (SQUIDSQUAD_DIR / f"start-{role}.sh").read_text(encoding="utf-8")
        assert f"SQUIDSQUAD_ROLE={role}" in content, (
            f"start-{role}.sh missing SQUIDSQUAD_ROLE={role}"
        )

    @pytest.mark.parametrize("role", ROLES)
    def test_ps1_has_correct_role(self, role):
        content = (SQUIDSQUAD_DIR / f"start-{role}.ps1").read_text(encoding="utf-8")
        assert f"SQUIDSQUAD_ROLE={role}" in content, (
            f"start-{role}.ps1 missing SQUIDSQUAD_ROLE={role}"
        )

    @pytest.mark.parametrize("role", ROLES)
    def test_bash_uses_append_system_prompt(self, role):
        content = (SQUIDSQUAD_DIR / f"start-{role}.sh").read_text(encoding="utf-8")
        assert "--append-system-prompt" in content, (
            f"start-{role}.sh should use --append-system-prompt"
        )

    @pytest.mark.parametrize("role", ROLES)
    def test_ps1_uses_append_system_prompt(self, role):
        content = (SQUIDSQUAD_DIR / f"start-{role}.ps1").read_text(encoding="utf-8")
        assert "--append-system-prompt" in content, (
            f"start-{role}.ps1 should use --append-system-prompt"
        )

    @pytest.mark.parametrize("role", ROLES)
    def test_bash_uses_name_variable(self, role):
        content = (SQUIDSQUAD_DIR / f"start-{role}.sh").read_text(encoding="utf-8")
        # The claude command should pass --name with the agent name variable
        assert '--name "$AGENT_NAME"' in content, (
            f"start-{role}.sh should pass --name \"$AGENT_NAME\" to claude"
        )

    @pytest.mark.parametrize("role", ROLES)
    def test_ps1_uses_name_variable(self, role):
        content = (SQUIDSQUAD_DIR / f"start-{role}.ps1").read_text(encoding="utf-8")
        assert "--name" in content and "AgentName" in content, (
            f"start-{role}.ps1 should pass --name with $AgentName to claude"
        )


class TestStartScriptConsistency:
    """Bash and PS1 scripts for each role are structurally consistent."""

    @pytest.mark.parametrize("role", ROLES)
    def test_both_write_active_role(self, role):
        sh = (SQUIDSQUAD_DIR / f"start-{role}.sh").read_text(encoding="utf-8")
        ps1 = (SQUIDSQUAD_DIR / f"start-{role}.ps1").read_text(encoding="utf-8")
        assert f'echo "{role}"' in sh or f"echo '{role}'" in sh, (
            f"start-{role}.sh should write role to .active-role"
        )
        assert f'"{role}"' in ps1, (
            f"start-{role}.ps1 should write role to .active-role"
        )

    @pytest.mark.parametrize("role", ROLES)
    def test_both_inject_permissions(self, role):
        sh = (SQUIDSQUAD_DIR / f"start-{role}.sh").read_text(encoding="utf-8")
        ps1 = (SQUIDSQUAD_DIR / f"start-{role}.ps1").read_text(encoding="utf-8")
        assert "inject-permissions" in sh, f"start-{role}.sh missing inject-permissions"
        assert "inject-permissions" in ps1, f"start-{role}.ps1 missing inject-permissions"

    @pytest.mark.parametrize("role", ROLES)
    def test_both_init_status_bar(self, role):
        sh = (SQUIDSQUAD_DIR / f"start-{role}.sh").read_text(encoding="utf-8")
        ps1 = (SQUIDSQUAD_DIR / f"start-{role}.ps1").read_text(encoding="utf-8")
        assert "current-state" in sh, f"start-{role}.sh should initialize current-state"
        assert "current-state" in ps1, f"start-{role}.ps1 should initialize current-state"
