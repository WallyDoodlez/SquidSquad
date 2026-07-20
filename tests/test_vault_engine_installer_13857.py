"""#13857 -- vault consumption engine installer wiring (P1 T3).

VAULT-ARCH section 7.5: the engine ships as Claude Skill packages under
references/skills/ and the wizard materializes them to .claude/skills/ at
install time, preflights Node as a SOFT prerequisite (absent Node the install
succeeds and the feature degrades per 6.2/9.9), and seeds the telemetry shard
dir's merge=union .gitattributes (8.5: installer work, not engine work).

No real node/subprocess dependency: preflight is exercised through mocks.
"""

import inspect
import sys
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import config as config_mod
import wizard


def make_target(tmp_path: Path) -> Path:
    """A minimal target root carrying one packaged skill source."""
    root = tmp_path / "install"
    skill = root / "references" / "skills" / "vault-search"
    (skill / "scripts" / "lib").mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: vault-search\n---\n", encoding="utf-8")
    (skill / "scripts" / "vault-query.mjs").write_text("// engine\n", encoding="utf-8")
    (skill / "scripts" / "lib" / "consumption.mjs").write_text("// lib\n", encoding="utf-8")
    # A non-skill dir (no SKILL.md) that must NOT be deployed.
    (root / "references" / "skills" / "not-a-skill").mkdir()
    return root


class TestInstallVaultEngine:
    def test_deploys_skill_packages_to_claude_skills(self, tmp_path):
        root = make_target(tmp_path)
        result = wizard.install_vault_engine(root)
        assert result["deployed"] == ["vault-search"]
        dest = root / ".claude" / "skills" / "vault-search"
        assert (dest / "SKILL.md").is_file()
        assert (dest / "scripts" / "vault-query.mjs").is_file()
        assert (dest / "scripts" / "lib" / "consumption.mjs").is_file()
        assert not (root / ".claude" / "skills" / "not-a-skill").exists()

    def test_redeploy_refreshes_existing_copy(self, tmp_path):
        root = make_target(tmp_path)
        wizard.install_vault_engine(root)
        src = root / "references" / "skills" / "vault-search" / "scripts" / "vault-query.mjs"
        src.write_text("// engine v2\n", encoding="utf-8")
        wizard.install_vault_engine(root)
        live = root / ".claude" / "skills" / "vault-search" / "scripts" / "vault-query.mjs"
        assert live.read_text(encoding="utf-8") == "// engine v2\n"

    def test_node_absent_degrades_never_fails(self, tmp_path, capsys):
        root = make_target(tmp_path)
        with patch.object(wizard.shutil, "which", return_value=None):
            result = wizard.install_vault_engine(root)
        assert result["node"] is None
        assert result["degraded"] is True
        # Skills still deployed, telemetry still seeded -- degrade, not fail.
        assert result["deployed"] == ["vault-search"]
        assert "NOT blocked" in capsys.readouterr().out

    def test_node_present_records_version(self, tmp_path):
        root = make_target(tmp_path)

        class FakeProc:
            returncode = 0
            stdout = "v24.13.0\n"

        with patch.object(wizard.shutil, "which", return_value="node"), patch.object(
            wizard.subprocess, "run", return_value=FakeProc()
        ):
            result = wizard.install_vault_engine(root)
        assert result["node"] == "v24.13.0"
        assert result["degraded"] is False

    def test_telemetry_gitattributes_seeded_and_idempotent(self, tmp_path):
        root = make_target(tmp_path)
        result = wizard.install_vault_engine(root)
        ga = root / ".squidsquad" / "vault" / ".telemetry" / ".gitattributes"
        assert ga.read_text(encoding="utf-8") == "*.jsonl merge=union\n"
        assert result["telemetry_seeded"] is True
        # Second run: existing file untouched, not re-reported as seeded.
        ga.write_text("*.jsonl merge=union\n# custom\n", encoding="utf-8")
        result2 = wizard.install_vault_engine(root)
        assert result2["telemetry_seeded"] is False
        assert "# custom" in ga.read_text(encoding="utf-8")

    def test_missing_source_dir_is_harmless(self, tmp_path):
        root = tmp_path / "bare"
        root.mkdir()
        result = wizard.install_vault_engine(root)
        assert result["deployed"] == []

    def test_scaffold_install_wires_the_step(self):
        """The production caller actually invokes the deploy (the
        shipped-unwired audit pattern: check at the caller level)."""
        src = inspect.getsource(wizard.scaffold_install)
        assert "install_vault_engine(target_root)" in src
        assert 'summary["vault_engine"]' in src


class TestConfigFlag:
    def test_default_spec_renders_vault_engine_flag(self):
        """generate_default_spec carries vault_engine: True, and the config.md
        writer renders it as a Flags line fresh installs get for free."""
        spec = wizard.generate_default_spec()
        assert spec["flags"]["vault_engine"] is True
        text = wizard.build_config_md(spec)
        assert "- **Vault Engine**: yes" in text

    def test_config_field_map_reads_the_flag(self):
        assert config_mod.FIELD_MAP["vault-engine"] == ("Flags", "Vault Engine")
        text = "# Config\n\n## Flags\n\n- **Vault Engine**: yes\n- **Diagnostics**: yes\n"
        assert config_mod._parse_field(text, "Flags", "Vault Engine") == "yes"
