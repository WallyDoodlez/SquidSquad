"""#13858 P2 T3 -- registry-derived templates (VAULT-ARCH 3.5 / 8.4).

Template set derives from the type registry: <type>.md per registered type,
_generic.md fallback for custom types, creation stamps dates and honors the
type's declared prefix + folder.
"""

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import vault_entity


@pytest.fixture
def custom_vault(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "vault-schema.json").write_text(json.dumps({
        "types": {
            "decision": {"folder": "galaxy", "traversal": "budgeted", "prefix": "decision-"},
            "runbook": {"folder": "runbooks", "traversal": "free"},
        }
    }), encoding="utf-8")
    return vault


class TestResolveTemplate:
    def test_registered_type_resolves_typed_template(self, custom_vault):
        path, generic = vault_entity.resolve_template("decision", custom_vault)
        assert path.name == "decision.md" and generic is False

    def test_custom_type_without_template_gets_generic(self, custom_vault):
        path, generic = vault_entity.resolve_template("runbook", custom_vault)
        assert path.name == "_generic.md" and generic is True

    def test_unregistered_type_rejected(self, custom_vault):
        with pytest.raises(ValueError):
            vault_entity.resolve_template("ghost", custom_vault)

    def test_default_profile_full_coverage(self):
        """Every type in the shipped default profile resolves a NON-generic
        template (the S2.3 'note creation for every registered type resolves
        its template' AC, seed-side)."""
        seed = json.loads(
            (SCRIPTS.parent / "vault-schema-default.json").read_text(encoding="utf-8"))
        for t in seed["types"]:
            if t == "archive":
                continue  # archives is a status, not a creatable type (3.4)
            path, generic = vault_entity.resolve_template(t, SCRIPTS.parent.parent)
            assert generic is False, f"default-profile type '{t}' lacks a template"


class TestCreateNote:
    def test_create_stamps_and_prefixes(self, custom_vault):
        dest = vault_entity.create_note("decision", "use-x", custom_vault, today="2026-07-20")
        assert dest.name == "decision-use-x.md"
        text = dest.read_text(encoding="utf-8")
        assert "type: decision" in text
        assert "created: 2026-07-20" in text and "updated: 2026-07-20" in text

    def test_create_refuses_overwrite(self, custom_vault):
        vault_entity.create_note("decision", "use-x", custom_vault, today="2026-07-20")
        with pytest.raises(FileExistsError):
            vault_entity.create_note("decision", "use-x", custom_vault, today="2026-07-20")

    def test_create_custom_type_via_generic(self, custom_vault):
        dest = vault_entity.create_note("runbook", "deploy", custom_vault, today="2026-07-20")
        assert dest.parent.name == "runbooks"
        assert "type: runbook" in dest.read_text(encoding="utf-8")
