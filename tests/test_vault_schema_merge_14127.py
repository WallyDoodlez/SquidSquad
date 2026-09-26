"""#14127 -- existing installs receive vault-v2 schema additions on upgrade.

The installer seeded vault-schema.json only when absent, so an install that
already had one kept it unchanged on upgrade: no `rule` type (the rules lane
stayed silently empty) and no `dedupThreshold`. An upgrade is a re-run of the
same installer flow (INSTALLER-ARCH §2 commitment 3), and install_vault_engine
now additively merges the framework defaults into an existing schema. Absent
keys and types are added; every present value and every user type is kept.
"""

import json
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import vault_check  # noqa: E402
import vault_consume  # noqa: E402
import vault_entity  # noqa: E402
import wizard  # noqa: E402

DEFAULT = REPO / "references" / "vault-schema-default.json"

# A pre-v2 install's schema: no `rule` type and no `dedupThreshold`, plus a
# user-registered type and a non-default override that must both survive.
PRE_V2 = {
    "traversalBudget": 3,                      # override (default is 2)
    "searchTopK": 12,
    "tieBreakWeights": {"used": 5.0, "impression": 0.25, "walked": 0.5},
    "types": {
        "project": {"folder": "projects", "traversal": "free", "weight": 0.8, "hub": True},
        "area": {"folder": "areas", "traversal": "free", "weight": 0.8, "hub": True},
        "resource": {"folder": "resources", "traversal": "free", "weight": 0.6, "hub": False},
        "decision": {"folder": "galaxy", "traversal": "budgeted", "weight": 1.0,
                     "hub": False, "prefix": "decision-"},
        "pattern": {"folder": "galaxy", "traversal": "budgeted", "weight": 1.0,
                    "hub": False, "prefix": "pattern-"},
        "learning": {"folder": "galaxy", "traversal": "budgeted", "weight": 0.3,
                     "hub": False, "prefix": "learning-"},   # override weight
        "system": {"folder": "systems", "traversal": "free", "weight": 0.8, "hub": True},
        "archive": {"folder": "archives", "traversal": "free", "weight": 0.5, "hub": False},
        "runbook": {"folder": "runbooks", "traversal": "free", "weight": 0.7,
                    "hub": False},                            # user-registered
    },
}


def _write_schema(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _target(tmp_path, schema=PRE_V2):
    """An install root carrying the REAL shipped default and a pre-v2 schema."""
    root = tmp_path / "install"
    (root / "references").mkdir(parents=True)
    shutil.copy2(DEFAULT, root / "references" / "vault-schema-default.json")
    schema_path = root / ".squidsquad" / "vault" / "vault-schema.json"
    if schema is not None:
        _write_schema(schema_path, schema)
    return root, schema_path


class TestMergeVaultSchemaDefaults:
    def test_adds_rule_and_dedup_preserving_custom_type_and_override(self, tmp_path):
        """AC1/AC2: both additions land; the custom type and overrides stay."""
        _, schema = _target(tmp_path)
        added = wizard.merge_vault_schema_defaults(schema, DEFAULT)
        got = json.loads(schema.read_text(encoding="utf-8"))
        assert "types.rule" in added and "dedupThreshold" in added
        assert got["types"]["rule"]["prefix"] == "rule-"
        assert got["dedupThreshold"] == json.loads(
            DEFAULT.read_text(encoding="utf-8"))["dedupThreshold"]
        # User content preserved exactly.
        assert got["types"]["runbook"] == PRE_V2["types"]["runbook"]
        assert got["types"]["learning"]["weight"] == 0.3
        assert got["traversalBudget"] == 3
        assert got["tieBreakWeights"]["used"] == 5.0
        # Missing sub-key of a dict setting is filled.
        assert "tieBreakWeights.recency" in added
        assert got["tieBreakWeights"]["recency"] == 0.25

    def test_idempotent_second_run_writes_nothing(self, tmp_path):
        _, schema = _target(tmp_path)
        wizard.merge_vault_schema_defaults(schema, DEFAULT)
        before = schema.read_bytes()
        assert wizard.merge_vault_schema_defaults(schema, DEFAULT) == []
        assert schema.read_bytes() == before

    def test_current_schema_untouched(self, tmp_path):
        """An install already carrying every default is not rewritten."""
        _, schema = _target(tmp_path, schema=None)
        schema.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(DEFAULT, schema)
        before = schema.read_bytes()
        assert wizard.merge_vault_schema_defaults(schema, DEFAULT) == []
        assert schema.read_bytes() == before

    def test_non_object_schema_raises(self, tmp_path):
        _, schema = _target(tmp_path, schema=None)
        schema.parent.mkdir(parents=True, exist_ok=True)
        schema.write_text("[1, 2]", encoding="utf-8")
        with pytest.raises(ValueError):
            wizard.merge_vault_schema_defaults(schema, DEFAULT)


class TestInstallerUpgradePath:
    def test_install_vault_engine_merges_existing_schema(self, tmp_path):
        """The installer re-run (the upgrade path) performs the merge."""
        root, schema = _target(tmp_path)
        result = wizard.install_vault_engine(root)
        assert result["schema_seeded"] is False
        assert "types.rule" in result["schema_merged"]
        assert "dedupThreshold" in result["schema_merged"]
        got = json.loads(schema.read_text(encoding="utf-8"))
        assert "rule" in got["types"] and "runbook" in got["types"]
        # A second re-run is a no-op.
        assert wizard.install_vault_engine(root)["schema_merged"] == []

    def test_fresh_install_seeds_without_merge(self, tmp_path):
        root, schema = _target(tmp_path, schema=None)
        result = wizard.install_vault_engine(root)
        assert result["schema_seeded"] is True
        assert result["schema_merged"] == []
        assert schema.read_bytes() == DEFAULT.read_bytes()

    def test_broken_schema_reported_not_replaced(self, tmp_path, capsys):
        root, schema = _target(tmp_path, schema=None)
        schema.parent.mkdir(parents=True, exist_ok=True)
        schema.write_text("{not json", encoding="utf-8")
        result = wizard.install_vault_engine(root)
        assert result["schema_merged"] == []
        assert schema.read_text(encoding="utf-8") == "{not json"
        assert "vault-schema seed/merge failed" in capsys.readouterr().err


RULE_NOTE = """---
type: rule
created: 2026-09-26
updated: 2026-09-26
tags: [harness, deploy]
---

# Rule: never respawn over a live deploy

Deploy stalls are recovered through the deploy sequence, never a second spawn.
"""


class TestRulesLaneAfterUpgrade:
    def test_rule_type_registered_after_upgrade(self, tmp_path):
        """Before the merge `rule` is unregistered (vault_entity refuses it);
        after it, rule notes resolve like any registered type."""
        root, schema = _target(tmp_path)
        vault = schema.parent
        with pytest.raises(ValueError):
            vault_entity.resolve_template("rule", vault_dir=vault)
        wizard.install_vault_engine(root)
        assert "rule" in vault_check._load_schema(vault)["types"]
        vault_entity.resolve_template("rule", vault_dir=vault)

    @pytest.mark.skipif(shutil.which("node") is None,
                        reason="vault engine needs node")
    def test_seeded_rule_note_surfaced_by_rules_lane(self, tmp_path):
        """AC3: after upgrade, a seeded rule-* note is surfaced by the
        rules-lane consultation (`--types rule`)."""
        root, schema = _target(tmp_path)
        wizard.install_vault_engine(root)
        vault = schema.parent
        (vault / "galaxy").mkdir(parents=True, exist_ok=True)
        (vault / "galaxy" / "rule-never-respawn-over-live-deploy.md").write_text(
            RULE_NOTE, encoding="utf-8")
        payload, reason = vault_consume.search(
            "skill", tags=("deploy",), types=("rule",), write=False, vault=vault)
        assert reason is None, reason
        slugs = [r["slug"] for r in payload["results"]]
        assert "rule-never-respawn-over-live-deploy" in slugs
