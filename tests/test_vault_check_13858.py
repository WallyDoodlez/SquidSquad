"""#13858 P2 T2 -- registry-driven vault_check (VAULT-ARCH 4.2a + 3.3).

check-structure validates layout + folder/prefix/type consistency against
vault-schema.json (custom types get validation for free); unregistered types
WARN instead of FAIL (M-track #13862 owns legacy content, 9.9 non-blocking);
check-hub-links is the advisory Level-2 graph-orphan sweep.
"""

import json
import sys
import textwrap
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import vault_check


def note(vault: Path, folder: str, name: str, body: str) -> Path:
    d = vault / folder
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{name}.md"
    p.write_text(textwrap.dedent(body), encoding="utf-8")
    return p


@pytest.fixture
def scratch_vault(tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "BRIEFING.md").write_text("# B\n", encoding="utf-8")
    monkeypatch.setattr(vault_check, "VAULT_DIR", vault)
    return vault


CUSTOM_SCHEMA = {
    "types": {
        "runbook": {"folder": "runbooks", "traversal": "free", "hub": True},
        "entry": {"folder": "entries", "traversal": "budgeted", "prefix": "entry-"},
    }
}


def write_schema(vault: Path, schema=None):
    (vault / "vault-schema.json").write_text(
        json.dumps(schema or CUSTOM_SCHEMA), encoding="utf-8")


class TestRegistryDrivenStructure:
    def test_custom_registry_dirs_required(self, scratch_vault):
        write_schema(scratch_vault)
        issues = vault_check.check_structure()
        assert any("runbooks" in i for i in issues)
        assert any("entries" in i for i in issues)
        # PARAG dirs are NOT required under a custom registry.
        assert not any("galaxy" in i for i in issues)

    def test_clean_custom_vault_passes(self, scratch_vault):
        write_schema(scratch_vault)
        note(scratch_vault, "runbooks", "deploy", "---\ntype: runbook\n---\n# d\n")
        note(scratch_vault, "entries", "entry-a", "---\ntype: entry\n---\n# a\n")
        assert vault_check.check_structure() == []

    def test_folder_type_violation_fails(self, scratch_vault):
        write_schema(scratch_vault)
        (scratch_vault / "entries").mkdir()
        note(scratch_vault, "runbooks", "misplaced", "---\ntype: entry\n---\n# x\n")
        issues = vault_check.check_structure()
        assert any("folder<->type" in i for i in issues)

    def test_prefix_type_violation_fails(self, scratch_vault):
        write_schema(scratch_vault)
        (scratch_vault / "runbooks").mkdir()
        note(scratch_vault, "entries", "unprefixed", "---\ntype: entry\n---\n# x\n")
        issues = vault_check.check_structure()
        assert any("prefix<->type" in i for i in issues)

    def test_unregistered_type_warns_never_fails(self, scratch_vault, capsys):
        write_schema(scratch_vault)
        (scratch_vault / "entries").mkdir()
        note(scratch_vault, "runbooks", "stray", "---\ntype: mystery\n---\n# x\n")
        issues = vault_check.check_structure()
        assert issues == []  # WARN, not FAIL (9.9 / M-track)
        assert "mystery" in capsys.readouterr().out

    def test_grandfathered_style_prefix_silent(self, scratch_vault, capsys):
        """style-* awaits the M-track reclassification -- no warn, no fail."""
        # Default profile (no schema file written; seed fallback applies).
        note(scratch_vault, "galaxy", "style-old", "---\ntype: style\n---\n# s\n")
        for f in ("projects", "areas", "resources", "archives", "systems"):
            (scratch_vault / f).mkdir(exist_ok=True)
        issues = vault_check.check_structure()
        out = capsys.readouterr().out
        assert issues == []
        assert "style-old" not in out


class TestHubLinkSweep:
    def test_graph_orphan_flagged_and_linked_not(self, scratch_vault, capsys):
        write_schema(scratch_vault, {
            "types": {
                "system": {"folder": "systems", "traversal": "free", "hub": True},
                "learning": {"folder": "galaxy", "traversal": "budgeted", "prefix": "learning-"},
            }
        })
        note(scratch_vault, "systems", "harness", "---\ntype: system\n---\n# harness hub\n")
        note(scratch_vault, "galaxy", "learning-linked",
             "---\ntype: learning\n---\n# l\nSee [[harness]].\n")
        note(scratch_vault, "galaxy", "learning-orphan",
             "---\ntype: learning\n---\n# o\nNo hub links here, [[learning-linked]] only.\n")
        warnings = vault_check.check_hub_links()
        joined = "\n".join(warnings)
        assert "learning-orphan" in joined
        assert "learning-linked" not in joined

    def test_no_hub_types_skips(self, scratch_vault, capsys):
        write_schema(scratch_vault, {
            "types": {"entry": {"folder": "entries", "traversal": "budgeted"}}
        })
        assert vault_check.check_hub_links() == []
        assert "SKIP" in capsys.readouterr().out


class TestSchemaLoading:
    def test_vault_schema_wins_over_seed(self, scratch_vault):
        write_schema(scratch_vault)
        views = vault_check._schema_views(vault_check._load_schema())
        assert set(views["folders"]) == {"runbooks", "entries"}

    def test_absent_schema_falls_back_to_seed_profile(self, scratch_vault):
        """No vault schema: the framework seed (or hardcoded PARAG shape)
        applies -- systems/ present, galaxy budgeted, hub types declared."""
        views = vault_check._schema_views(vault_check._load_schema())
        assert "galaxy" in views["folders"]
        assert "system" in views["hub_types"] or "project" in views["hub_types"]

    def test_malformed_schema_falls_back(self, scratch_vault):
        (scratch_vault / "vault-schema.json").write_text("{not json", encoding="utf-8")
        views = vault_check._schema_views(vault_check._load_schema())
        assert "galaxy" in views["folders"]  # fell through to seed/hardcode
