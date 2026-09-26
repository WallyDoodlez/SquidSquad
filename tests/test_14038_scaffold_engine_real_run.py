"""#14038 -- the REAL scaffold_install must produce the vault-engine
artifacts, asserted on the result, not on source text.

Prior guard was `inspect.getsource(scaffold_install)` string-matching the
install_vault_engine call -- a refactor that renames/moves the step could
keep the string green while the real deploy silently stops firing (the
shipped-unwired audit pattern). This drives the REAL `scaffold_install`
(same offline harness as the #13514 seam tests: default spec, stubbed
deploy_role_v2, no gh/network) with the engine sources seeded into the
scaffold target, and asserts the step-5b outputs exist on disk afterwards:
the deployed skill package, the .telemetry merge=union seed, and
vault-schema.json. Supersedes
test_vault_engine_installer_13857::test_scaffold_install_wires_the_step.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..",
                                "references", "scripts"))

import compose  # noqa: E402
import wizard  # noqa: E402


class _GhMiss:
    """gh not consulted -- repo_info falls back to the target dir name."""
    returncode = 1
    stdout = ""
    stderr = ""


def _offline(monkeypatch):
    monkeypatch.setattr(wizard, "ensure_labels", lambda dry_run=False: {"created": 0})
    monkeypatch.setattr(wizard, "_run", lambda *a, **k: _GhMiss())
    # Compose is out of scope here -- record a plausible path, never fail.
    def ok(compose_name, target_root=None, output_name=None):
        return os.path.join(str(target_root), ".squidsquad", output_name, "CLAUDE.md")
    monkeypatch.setattr(compose, "deploy_role_v2", ok)


def _seed_engine_sources(target_root):
    """What a real fetched install carries before the wizard runs: the
    packaged skill sources + the schema seed (per installer-files.txt)."""
    skill = target_root / "references" / "skills" / "vault-search"
    (skill / "scripts" / "lib").mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: vault-search\n---\n", encoding="utf-8")
    (skill / "scripts" / "vault-query.mjs").write_text("// engine\n", encoding="utf-8")
    (skill / "scripts" / "lib" / "consumption.mjs").write_text("// lib\n", encoding="utf-8")
    (target_root / "references" / "vault-schema-default.json").write_text(
        json.dumps({"types": {"learning": {"folder": "galaxy",
                                           "traversal": "budgeted",
                                           "weight": 1.0}}}),
        encoding="utf-8")


def test_real_scaffold_install_produces_engine_artifacts(tmp_path, monkeypatch):
    _offline(monkeypatch)
    _seed_engine_sources(tmp_path)

    spec = wizard.generate_default_spec({}, {"name": "engineprobe"})
    result = wizard.scaffold_install(spec, tmp_path, overwrite_existing=True)

    # 1. The result records the step ran (production-caller wiring).
    ve = result.get("vault_engine")
    assert ve is not None, (
        "scaffold_install result carries no vault_engine summary -- "
        "the install_vault_engine step did not fire")
    assert ve["deployed"] == ["vault-search"]

    # 2. The artifacts exist on disk in the scaffold target.
    deployed = tmp_path / ".claude" / "skills" / "vault-search"
    assert (deployed / "SKILL.md").is_file()
    assert (deployed / "scripts" / "vault-query.mjs").is_file()
    assert (deployed / "scripts" / "lib" / "consumption.mjs").is_file()

    ga = tmp_path / ".squidsquad" / "vault" / ".telemetry" / ".gitattributes"
    assert ga.is_file()
    assert "merge=union" in ga.read_text(encoding="utf-8")

    schema = tmp_path / ".squidsquad" / "vault" / "vault-schema.json"
    assert schema.is_file()
    assert "learning" in schema.read_text(encoding="utf-8")


def test_real_scaffold_install_engine_step_degrades_without_sources(tmp_path, monkeypatch):
    """Negative control: a target with NO engine sources (the pre-existing
    test_wizard.py fixtures' shape) must still scaffold -- the step no-ops
    gracefully (deployed: []) rather than failing the install. This is the
    exact silent shape that made the old real-run tests assert nothing."""
    _offline(monkeypatch)

    spec = wizard.generate_default_spec({}, {"name": "bareprobe"})
    result = wizard.scaffold_install(spec, tmp_path, overwrite_existing=True)

    ve = result.get("vault_engine")
    assert ve is not None
    assert ve["deployed"] == []
    assert not (tmp_path / ".claude" / "skills" / "vault-search").exists()
