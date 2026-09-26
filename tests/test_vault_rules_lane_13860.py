"""#13860 P4 commit 1 -- the binding-rules lane (VAULT-ARCH 11 #3, 9.3).

The operator resolved 11 #3 as a dedicated `rule` type. P4's rules matching
scans that lane only, so the type must be registered everywhere the registry
is read (framework seed, engine defaults), must have a template, must pass
registry-driven validation, and the engine must be able to restrict a search
to it (`--types rule`).
"""

import json
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import vault_check  # noqa: E402
import vault_entity  # noqa: E402

SEED = REPO / "references" / "vault-schema-default.json"
QUERY = REPO / "references" / "skills" / "vault-search" / "scripts" / "vault-query.mjs"
CONSUMPTION = REPO / "references" / "skills" / "vault-search" / "scripts" / "lib" / "consumption.mjs"
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="node unavailable -- engine degrades per VAULT-ARCH 9.9")

IDENTITY = ["--instance-id", "test-uuid", "--alias", "skill", "--task", "13860", "--no-write"]


def note(vault: Path, folder: str, slug: str, body: str) -> Path:
    d = vault / folder
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{slug}.md"
    p.write_text(textwrap.dedent(body), encoding="utf-8")
    return p


class TestRegistration:
    def test_seed_profile_registers_rule(self):
        rule = json.loads(SEED.read_text(encoding="utf-8"))["types"]["rule"]
        assert rule == {"folder": "galaxy", "traversal": "budgeted", "weight": 1.0,
                        "hub": False, "prefix": "rule-"}

    def test_rule_registered_after_decision(self):
        """galaxy's untyped-note default weight is the FIRST-registered galaxy
        type (deriveSchema contract) -- adding `rule` must not displace it."""
        types = list(json.loads(SEED.read_text(encoding="utf-8"))["types"])
        assert types.index("decision") < types.index("rule")

    @needs_node
    def test_engine_default_config_registers_rule(self):
        script = (f"import('{CONSUMPTION.as_uri()}').then(m => "
                  "console.log(JSON.stringify(m.DEFAULT_CONFIG.types.rule)))")
        out = subprocess.run([NODE, "-e", script], capture_output=True, text=True, check=True).stdout
        assert json.loads(out) == {"folder": "galaxy", "traversal": "budgeted", "weight": 1.0,
                                   "hub": False, "prefix": "rule-"}

    def test_template_shipped_by_installer(self):
        assert (REPO / "references" / "vault-templates" / "rule.md").is_file()
        listed = (REPO / "references" / "installer-files.txt").read_text(encoding="utf-8").splitlines()
        assert "references/vault-templates/rule.md" in listed


class TestTemplateAndCreation:
    def test_rule_resolves_own_template(self):
        path, generic = vault_entity.resolve_template("rule", REPO / "references")
        assert generic is False and path.name == "rule.md"

    def test_template_carries_rule_scope_why(self):
        text = (REPO / "references" / "vault-templates" / "rule.md").read_text(encoding="utf-8")
        assert "type: rule" in text
        for section in ("## Rule", "## Scope", "## Why"):
            assert section in text

    def test_create_rule_note_lands_prefixed_in_galaxy(self, tmp_path):
        vault = tmp_path / "vault"
        vault.mkdir()
        shutil.copy(SEED, vault / "vault-schema.json")
        dest = vault_entity.create_note("rule", "no-bare-gh-close", vault, today="2026-09-26")
        assert dest == vault / "galaxy" / "rule-no-bare-gh-close.md"
        assert "type: rule" in dest.read_text(encoding="utf-8")


class TestValidation:
    def test_rule_note_passes_structure_check(self, tmp_path, monkeypatch):
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "BRIEFING.md").write_text("# B\n", encoding="utf-8")
        shutil.copy(SEED, vault / "vault-schema.json")
        for f in ("projects", "areas", "resources", "archives", "systems"):
            (vault / f).mkdir()
        note(vault, "galaxy", "rule-x", "---\ntype: rule\n---\n# x\n")
        monkeypatch.setattr(vault_check, "VAULT_DIR", vault)
        assert vault_check.check_structure() == []

    def test_unprefixed_rule_fails_prefix_check(self, tmp_path, monkeypatch):
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "BRIEFING.md").write_text("# B\n", encoding="utf-8")
        shutil.copy(SEED, vault / "vault-schema.json")
        for f in ("projects", "areas", "resources", "archives", "systems"):
            (vault / f).mkdir()
        note(vault, "galaxy", "decision-y", "---\ntype: rule\n---\n# y\n")
        monkeypatch.setattr(vault_check, "VAULT_DIR", vault)
        assert any("prefix<->type" in i for i in vault_check.check_structure())


def make_lane_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    vault.mkdir()
    shutil.copy(SEED, vault / "vault-schema.json")
    note(vault, "galaxy", "decision-merge-policy", """\
        ---
        type: decision
        status: active
        updated: 2026-09-01
        tags: [merge, git]
        ---
        # Merge policy
        Always merge. Enforced by [[rule-never-rebase]].
        """)
    note(vault, "galaxy", "rule-never-rebase", """\
        ---
        type: rule
        status: active
        updated: 2026-09-01
        tags: [git, rebase]
        ---
        # Never rebase shared branches
        Parent: [[decision-merge-policy]]
        """)
    note(vault, "galaxy", "learning-rebase-incident", """\
        ---
        type: learning
        status: active
        updated: 2026-09-01
        tags: [git, rebase]
        ---
        # Rebase incident
        See [[rule-never-rebase]].
        """)
    return vault


def run_query(vault: Path, *args: str):
    proc = subprocess.run([NODE, str(QUERY), "--vault", str(vault), *IDENTITY, *args],
                          capture_output=True, text=True, cwd=str(REPO))
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


@needs_node
class TestTypesLaneFilter:
    def test_types_rule_surfaces_only_rules(self, tmp_path):
        out = run_query(make_lane_vault(tmp_path), "--tags", "git", "--types", "rule")
        assert [r["slug"] for r in out["results"]] == ["rule-never-rebase"]
        assert out["traversed"] == []  # non-rule connectors are walked, never surfaced
        assert out["query"]["types"] == ["rule"]

    def test_no_types_flag_is_unfiltered(self, tmp_path):
        out = run_query(make_lane_vault(tmp_path), "--tags", "git")
        assert {r["slug"] for r in out["results"]} == {
            "decision-merge-policy", "rule-never-rebase", "learning-rebase-incident"}
        assert "types" not in out["query"]

    def test_traversal_reaches_rule_through_non_rule_note(self, tmp_path):
        """A rule linked from a matched-but-filtered decision still surfaces as
        a traversed connector: the lane filters output, not the walk."""
        out = run_query(make_lane_vault(tmp_path), "--tags", "merge", "--types", "rule")
        assert out["results"] == []
        assert [t["slug"] for t in out["traversed"]] == ["rule-never-rebase"]

    @pytest.mark.parametrize("tail", [["--types"], ["--types", "--no-write"], ["--types", ""]])
    def test_valueless_types_is_usage_error(self, tmp_path, tail):
        """A dropped --types value must exit 2, never an empty lane that reads
        as a genuine 'no rules matched' (review finding on commit 1)."""
        proc = subprocess.run([NODE, str(QUERY), "--vault", str(make_lane_vault(tmp_path)),
                               *IDENTITY, "--tags", "git", *tail],
                              capture_output=True, text=True, cwd=str(REPO))
        assert proc.returncode == 2 and "--types requires a value" in proc.stderr

    def test_multiple_types_comma_list(self, tmp_path):
        out = run_query(make_lane_vault(tmp_path), "--tags", "rebase", "--types", "rule,learning")
        assert {r["slug"] for r in out["results"]} == {"rule-never-rebase", "learning-rebase-incident"}
