"""Tests for #3101 — startup logo: figlet banner with ANSI color support.

Verifies that start-role templates contain the cybermedium figlet banner,
ANSI color detection, monochrome fallback, and version/agent name line.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = REPO_ROOT / "references" / "templates"
SQUIDSQUAD_DIR = REPO_ROOT / ".squidsquad"


@pytest.fixture(scope="module")
def bash_template():
    path = TEMPLATES_DIR / "start-role.sh"
    assert path.exists(), "start-role.sh template not found"
    return path.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def ps1_template():
    path = TEMPLATES_DIR / "start-role.ps1"
    assert path.exists(), "start-role.ps1 template not found"
    return path.read_text(encoding="utf-8")


class TestBashLogo:
    """Verify bash template logo content and ANSI color."""

    def test_figlet_banner_present(self, bash_template):
        """#3101: Cybermedium figlet banner text present."""
        assert "____ ____ _  _ _ ___" in bash_template
        assert "[__  |  |" in bash_template
        assert "___] |_" in bash_template

    def test_no_old_squid_art(self, bash_template):
        """#3101: Old squid Unicode art replaced."""
        assert "▗▄▖" not in bash_template
        assert "▟█ █▙" not in bash_template
        assert "▐█• •█▌" not in bash_template

    def test_ansi_color_detection(self, bash_template):
        """#3101: Terminal color support detected via tput."""
        assert "tput colors" in bash_template

    def test_ansi_red_codes(self, bash_template):
        """#3101: Bold red ANSI escape codes used."""
        assert "1;31m" in bash_template
        assert "[0m" in bash_template

    def test_monochrome_fallback(self, bash_template):
        """#3101: Color vars default to empty (monochrome fallback)."""
        assert '_R="" _N=""' in bash_template or "_R='' _N=''" in bash_template

    def test_version_variable_preserved(self, bash_template):
        """#3101: Version variable reference preserved."""
        assert "${V:-?}" in bash_template

    def test_agent_name_preserved(self, bash_template):
        """#3101: Agent name variable reference preserved."""
        assert "${AGENT_NAME}" in bash_template

    def test_banner_width_under_60(self, bash_template):
        """#3101: Banner lines are under 60 chars wide."""
        for line in bash_template.splitlines():
            if "____" in line and "[__" not in line and "___]" not in line:
                # First banner line
                # Strip echo prefix and ANSI variable refs
                content = re.sub(r'\$\{_[RN]\}', '', line)
                content = re.sub(r'^\s*echo\s+"?', '', content).rstrip('"')
                assert len(content) <= 60, f"Banner line too wide ({len(content)}): {content}"


class TestPowerShellLogo:
    """Verify PowerShell template logo content and ANSI color."""

    def test_figlet_banner_present(self, ps1_template):
        """#3101: Cybermedium figlet banner text present."""
        assert "____ ____ _  _ _ ___" in ps1_template
        assert "[__  |  |" in ps1_template
        assert "___] |_" in ps1_template

    def test_no_old_squid_art(self, ps1_template):
        """#3101: Old squid Unicode art replaced."""
        assert "▗▄▖" not in ps1_template
        assert "▟█ █▙" not in ps1_template

    def test_ansi_color_detection(self, ps1_template):
        """#3101: Color detection for Windows Terminal / VS Code / VirtualTerminal."""
        assert "WT_SESSION" in ps1_template or "VirtualTerminal" in ps1_template

    def test_ansi_red_codes(self, ps1_template):
        """#3101: Bold red ANSI escape codes used."""
        assert "1;31m" in ps1_template
        assert "[0m" in ps1_template

    def test_escape_char_defined(self, ps1_template):
        """#3101: ESC character defined for ANSI codes."""
        assert "[char]27" in ps1_template

    def test_monochrome_fallback(self, ps1_template):
        """#3101: Color vars default to empty (monochrome fallback)."""
        assert '$R = ""' in ps1_template or "$R = ''" in ps1_template

    def test_version_variable_preserved(self, ps1_template):
        """#3101: Version variable reference preserved."""
        assert "$v" in ps1_template

    def test_agent_name_preserved(self, ps1_template):
        """#3101: Agent name variable reference preserved."""
        assert "$AgentName" in ps1_template


class TestDeployedScripts:
    """Verify compose.py boot-all propagated the logo to active role start scripts."""

    @pytest.fixture(autouse=True, scope="class")
    def _check_deployed(self, request):
        """Skip if no deployed scripts exist."""
        if not SQUIDSQUAD_DIR.exists():
            pytest.skip("No .squidsquad directory")

    def _get_active_scripts(self, ext):
        """Get start scripts for actively configured roles (not stale/inactive)."""
        # Active roles: pm + dev-agents from config
        import sys
        sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))
        try:
            from config import get as config_get
            agents = config_get("dev-agents") or ""
        except Exception:
            agents = ""
        roles = [r.strip() for r in agents.split(",") if r.strip()]
        roles.append("pm")
        return [SQUIDSQUAD_DIR / f"start-{r}.{ext}" for r in roles
                if (SQUIDSQUAD_DIR / f"start-{r}.{ext}").exists()]

    def test_deployed_sh_has_banner(self):
        """#3101: Active deployed .sh scripts have the new banner."""
        sh_files = self._get_active_scripts("sh")
        if not sh_files:
            pytest.skip("No active deployed .sh scripts")
        for f in sh_files:
            content = f.read_text(encoding="utf-8")
            assert "____ ____ _  _ _ ___" in content, f"{f.name} missing banner"

    def test_deployed_sh_has_color(self):
        """#3101: Active deployed .sh scripts have ANSI color detection."""
        sh_files = self._get_active_scripts("sh")
        if not sh_files:
            pytest.skip("No active deployed .sh scripts")
        for f in sh_files:
            content = f.read_text(encoding="utf-8")
            assert "tput colors" in content, f"{f.name} missing color detection"

    def test_deployed_ps1_has_banner(self):
        """#3101: Active deployed .ps1 scripts have the new banner."""
        ps1_files = self._get_active_scripts("ps1")
        if not ps1_files:
            pytest.skip("No active deployed .ps1 scripts")
        for f in ps1_files:
            content = f.read_text(encoding="utf-8")
            assert "____ ____ _  _ _ ___" in content, f"{f.name} missing banner"

    def test_deployed_ps1_has_color(self):
        """#3101: Active deployed .ps1 scripts have ANSI color detection."""
        ps1_files = self._get_active_scripts("ps1")
        if not ps1_files:
            pytest.skip("No active deployed .ps1 scripts")
        for f in ps1_files:
            content = f.read_text(encoding="utf-8")
            assert "WT_SESSION" in content or "VirtualTerminal" in content, \
                f"{f.name} missing color detection"
