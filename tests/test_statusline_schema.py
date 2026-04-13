"""Static checks for statusline.sh schema-awareness (#328 Phase I).

The shell-based statusline script originally parsed a v1-only config.md
field (`- **Dev Agents**: fe, be`) in three places. Phase I replaces that
with a `python references/scripts/config.py list-agents` call resolved
once at the top of the script and stashed in shell variables.

These tests enforce:
  1. The legacy `grep 'Dev Agents'` pattern is gone from both shipped
     copies of statusline.sh (references/ and .squidsquad/).
  2. The schema-aware resolution block exists and uses the new
     config.py list-agents command.
  3. Both statusline.sh files stay in sync — editing one must also
     update the other (the live one is a verbatim copy of references).
  4. The config.py list-agents command produces tab-separated output
     the shell can parse safely.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
REFERENCES_STATUSLINE = REPO_ROOT / "references" / "statusline.sh"
LIVE_STATUSLINE = REPO_ROOT / ".squidsquad" / "statusline.sh"
CONFIG_PY = REPO_ROOT / "references" / "scripts" / "config.py"

sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))


@pytest.fixture(scope="module")
def refs_script():
    assert REFERENCES_STATUSLINE.exists()
    return REFERENCES_STATUSLINE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def live_script():
    if not LIVE_STATUSLINE.exists():
        pytest.skip("no live .squidsquad/statusline.sh on this checkout")
    return LIVE_STATUSLINE.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Legacy grep pattern must be gone from executable code
# ---------------------------------------------------------------------------


class TestNoLegacyDevAgentsGrep:
    def test_references_script_has_no_dev_agents_grep(self, refs_script):
        # A literal `grep 'Dev Agents'` (or double-quoted equivalent) in an
        # executable line would still match the v1-only field. The only
        # surviving occurrences should be inside a `#` comment documenting
        # why it was removed.
        for lineno, line in enumerate(refs_script.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            assert "Dev Agents" not in line, (
                f"references/statusline.sh line {lineno} still references "
                f"the legacy 'Dev Agents' field in executable code: {line!r}"
            )

    def test_live_script_has_no_dev_agents_grep(self, live_script):
        for lineno, line in enumerate(live_script.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            assert "Dev Agents" not in line, (
                f".squidsquad/statusline.sh line {lineno} still references "
                f"the legacy 'Dev Agents' field in executable code: {line!r}"
            )


# ---------------------------------------------------------------------------
# New schema-aware resolution block
# ---------------------------------------------------------------------------


class TestSchemaAwareAgentResolution:
    def test_references_script_calls_list_agents(self, refs_script):
        assert "config.py list-agents" in refs_script, (
            "statusline.sh must call `config.py list-agents` to enumerate "
            "the installed agents schema-agnostically"
        )

    def test_references_script_defines_dev_agents_list(self, refs_script):
        assert "DEV_AGENTS_LIST" in refs_script

    def test_references_script_defines_all_agent_ids(self, refs_script):
        assert "ALL_AGENT_IDS" in refs_script

    def test_references_script_uses_dev_agents_in_backlog_cache(self, refs_script):
        """Backlog cache refresh must loop over DEV_AGENTS_LIST."""
        # Find the cache-refresh background block and confirm it uses the
        # new variable, not a fresh grep.
        assert 'AGENTS_LIST="$DEV_AGENTS_LIST"' in refs_script

    def test_references_script_uses_all_agents_in_pm_health(self, refs_script):
        """PM health check must loop over ALL_AGENT_IDS, not the old grep."""
        assert 'ALL_AGENTS="$ALL_AGENT_IDS"' in refs_script

    def test_references_script_uses_dev_agents_in_dm_work(self, refs_script):
        """DM work counter must loop over DEV_AGENTS_LIST."""
        assert 'AGENTS="$DEV_AGENTS_LIST"' in refs_script


# ---------------------------------------------------------------------------
# references/ and .squidsquad/ copies stay in sync
# ---------------------------------------------------------------------------


class TestStatuslineInSync:
    def test_references_and_live_are_byte_identical(self, refs_script, live_script):
        assert refs_script == live_script, (
            "references/statusline.sh and .squidsquad/statusline.sh are "
            "out of sync — edit references/ and `cp` it to .squidsquad/"
        )


# ---------------------------------------------------------------------------
# config.py list-agents output shape
# ---------------------------------------------------------------------------


class TestListAgentsCommand:
    def test_command_runs_and_returns_tab_separated(self):
        """Live call — must run against the real repo config."""
        result = subprocess.run(
            [sys.executable, str(CONFIG_PY), "list-agents"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip(), "expected at least one agent line"
        for line in result.stdout.strip().splitlines():
            parts = line.split("\t")
            assert len(parts) == 3, (
                f"list-agents line must have 3 tab-separated columns: {line!r}"
            )
            agent_id, role, alias = parts
            assert agent_id and role and alias

    def test_command_output_matches_json_agents(self):
        """Tab output must match the JSON `agents` output agent-for-agent."""
        tab_result = subprocess.run(
            [sys.executable, str(CONFIG_PY), "list-agents"],
            capture_output=True, text=True,
        )
        json_result = subprocess.run(
            [sys.executable, str(CONFIG_PY), "agents"],
            capture_output=True, text=True,
        )
        assert tab_result.returncode == 0
        assert json_result.returncode == 0
        agents = json.loads(json_result.stdout)
        expected_ids = [a["id"] for a in agents]
        actual_ids = [
            line.split("\t")[0] for line in tab_result.stdout.strip().splitlines()
        ]
        assert actual_ids == expected_ids

    def test_help_lists_new_commands(self):
        """The help text must mention the new `list-agents` subcommand."""
        result = subprocess.run(
            [sys.executable, str(CONFIG_PY), "--help"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "agents" in result.stdout
        assert "schema-version" in result.stdout


# ---------------------------------------------------------------------------
# Vault pending questions integration in statusline (#18)
# ---------------------------------------------------------------------------


class TestVaultPendingQuestionsStatusline:
    """Verify statusline.sh is wired to render vault pending-question count."""

    def test_references_script_calls_pending_count(self, refs_script):
        assert "vault_optimize.py pending-count" in refs_script, (
            "statusline.sh must call vault_optimize.py pending-count "
            "to read pending vault questions"
        )

    def test_references_script_defines_vault_q(self, refs_script):
        assert "VAULT_Q=" in refs_script, (
            "statusline.sh must define VAULT_Q variable for vault question display"
        )

    def test_references_script_has_fire_escalation(self, refs_script):
        """Escalating fire emojis at 3+ pending questions per spec."""
        assert "FIRE_COUNT" in refs_script, (
            "statusline.sh must compute FIRE_COUNT for escalating urgency"
        )
        # Cap at 8 fires
        assert "FIRE_COUNT" in refs_script and "-gt 8" in refs_script, (
            "fire emoji count must be capped at 8"
        )

    def test_pm_line1_includes_vault_q(self, refs_script):
        """PM status line must include VAULT_Q segment."""
        # Find the PM block and check VAULT_Q is referenced before CTX_STR
        pm_block = refs_script[refs_script.index("# === PM-specific"):]
        dm_block_start = pm_block.index("# === DM segments")
        pm_block = pm_block[:dm_block_start]
        assert "VAULT_Q" in pm_block, (
            "PM status line must render vault pending questions"
        )

    def test_dm_line1_includes_vault_q(self, refs_script):
        """DM status line must include VAULT_Q segment."""
        dm_block = refs_script[refs_script.index("# === DM segments"):]
        dev_block_start = dm_block.index("# === Dev agent")
        dm_block = dm_block[:dev_block_start]
        assert "VAULT_Q" in dm_block, (
            "DM status line must render vault pending questions"
        )

    def test_dev_line1_includes_vault_q(self, refs_script):
        """Dev agent status line must include VAULT_Q segment."""
        dev_block = refs_script[refs_script.index("# === Dev agent"):]
        assert "VAULT_Q" in dev_block, (
            "Dev agent status line must render vault pending questions"
        )

    def test_vault_q_empty_when_zero_questions(self, refs_script):
        """VAULT_Q stays empty when count is 0 — no icon shown."""
        assert 'VAULT_Q=""' in refs_script, (
            "VAULT_Q must default to empty string"
        )
        assert 'VAULT_Q_COUNT" -gt 0' in refs_script, (
            "VAULT_Q must only be set when count > 0"
        )

    def test_live_script_matches_references(self, refs_script, live_script):
        """Already tested above but re-check after vault pending changes."""
        assert refs_script == live_script
