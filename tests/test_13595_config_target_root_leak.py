"""Regression test for #13595: compose's config-value placeholder substitution
must read the TARGET install's own config.md, not the installing clone's.

Root cause: config.py's CONFIG_PATH is fixed at import time to the installing
clone's own repo root. compose.py's _substitute_placeholders -> _read_config_value
-> config.get_field always read that fixed path, so every foreign
deploy_role_v2/deploy_alias_v2(target_root=foreign) call silently substituted
the INSTALLING clone's own config values (workers/aliases/test-commands/
project-name/interval) into the foreign target's composed CLAUDE.md.

Fix: config.config_path_override (a contextvar) lets compose.py redirect
get_field() reads to target_root's own config.md for the duration of
_substitute_placeholders, without touching any other get_field() call site.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import compose  # noqa: E402
import config  # noqa: E402
import atomic_emit  # noqa: E402


@pytest.fixture(autouse=True)
def _stub_assemble_pipeline(monkeypatch):
    """Bypass the LLM assemble pipeline — write the linked composite verbatim
    (same stub pattern as test_compose_a2f_10492.py)."""

    def fake_assemble_and_emit(
        linked_composite, output_dir, *, role_class, model_id=None,
        commit_sha=None, generated_at=None, filename_suffix=".v2.md",
        **kwargs,
    ):
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        if filename_suffix == "":
            base, linked, conflicts = "CLAUDE.md", "CLAUDE.linked.md", "CLAUDE.conflicts.md"
        else:
            base = f"CLAUDE{filename_suffix}"
            linked = f"CLAUDE.linked{filename_suffix}"
            conflicts = f"CLAUDE.conflicts{filename_suffix}"
        (output_dir / base).write_text(linked_composite, encoding="utf-8")
        (output_dir / linked).write_text(linked_composite, encoding="utf-8")
        (output_dir / conflicts).write_text("# stub\n", encoding="utf-8")
        return output_dir / base, output_dir / linked, output_dir / conflicts

    monkeypatch.setattr(atomic_emit, "assemble_and_emit", fake_assemble_and_emit)


def _frontmatter(slot, ordinal, roles=None):
    lines = ["---", f"slot: {slot}", f"ordinal: {ordinal}"]
    if roles is not None:
        lines.append(f"roles: [{', '.join(roles)}]")
    lines.append("---")
    return "\n".join(lines)


def _write_source(path, slot, ordinal, body, roles=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = _frontmatter(slot, ordinal, roles=roles) + "\n\n" + body
    path.write_text(text, encoding="utf-8")


def _stage_minimal_install(root, alias="pm", role="pm", pm_alias_value="pm"):
    """Stage a tiny fixture install under `root`, whose own config.md sets
    `alias-pm` to `pm_alias_value` — the value a foreign compose must read."""
    refs = root / "references"
    _write_source(refs / "roles" / "identity.md", "identity", 10, "Identity base.")
    _write_source(refs / "roles" / "responsibility.md", "responsibility", 10, "Responsibility base.")
    _write_source(refs / "roles" / "SOUL.md", "soul", 10, "Soul base.")
    _write_source(refs / "roles" / "instructions.md", "instructions", 10,
                  "### step:cycle/boot\nBoot body. [PM_ALIAS]\n")
    _write_source(refs / "roles" / "vault.md", "vault", 10, "Vault base.")
    _write_source(refs / "roles" / role / "instructions.md", "instructions", 20,
                  "### step:cycle/work\nWork body.\n", roles=[role])

    catalog = root / "docs" / "sub-skill-catalog.md"
    catalog.parent.mkdir(parents=True, exist_ok=True)
    catalog.write_text(
        "## `common/` — Cross-cutting\n\n"
        "| Sub-skill | One-liner | Used by |\n"
        "|---|---|---|\n"
        "| `boot-bootstrap` | Mode detection | all |\n",
        encoding="utf-8",
    )

    config_md = root / ".squidsquad" / "config.md"
    config_md.parent.mkdir(parents=True, exist_ok=True)
    config_md.write_text(
        "## Aliases\n\n"
        "| alias | role-class | L3 domain |\n"
        "|---|---|---|\n"
        f"| {alias} | {role} | |\n\n"
        f"- **pm**: {pm_alias_value}\n\n"
        "## Iteration Interval\n\n"
        "- **Minutes**: 30\n",
        encoding="utf-8",
    )
    return root


def _mk_registry(alias_to_role):
    return {alias: (role, None) for alias, role in alias_to_role.items()}


class TestConfigValuePlaceholderReadsTargetRoot:
    """#13595: a foreign target_root's own config.md must win, never the
    installing clone's ambient config.CONFIG_PATH."""

    def test_deploy_alias_v2_reads_target_config_not_installing_clone(self, tmp_path, monkeypatch):
        # The "installing clone" — a completely separate config.md the
        # compose call must NEVER read from during a foreign install.
        installing_clone_config = tmp_path / "installing-clone" / ".squidsquad" / "config.md"
        installing_clone_config.parent.mkdir(parents=True, exist_ok=True)
        installing_clone_config.write_text(
            "## Aliases\n\n- **pm**: INSTALLING-CLONE-LEAK\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(config, "CONFIG_PATH", installing_clone_config)

        # The foreign target — its own config.md has a DIFFERENT value.
        target_root = tmp_path / "foreign-target"
        _stage_minimal_install(target_root, pm_alias_value="foreign-pm")

        registry = _mk_registry({"pm": "pm"})
        out = compose.deploy_alias_v2("pm", registry=registry, target_root=target_root)
        text = out.read_text(encoding="utf-8")

        assert "foreign-pm" in text, (
            "compose must substitute [PM_ALIAS] from the TARGET's own "
            "config.md — the foreign target's value never appeared"
        )
        assert "INSTALLING-CLONE-LEAK" not in text, (
            "#13595 regression: the installing clone's own config value "
            "leaked into the foreign target's composed output"
        )

    def test_config_get_field_unaffected_outside_override(self, monkeypatch, tmp_path):
        """The contextvar must not leak state across calls — a plain
        get_field() outside any override still reads the ambient CONFIG_PATH,
        unaffected by a prior compose call's override."""
        real_config = tmp_path / "config.md"
        real_config.write_text("## Aliases\n\n- **pm**: real-value\n", encoding="utf-8")
        monkeypatch.setattr(config, "CONFIG_PATH", real_config)

        other = tmp_path / "other-config.md"
        other.write_text("## Aliases\n\n- **pm**: other-value\n", encoding="utf-8")

        with config.config_path_override(other):
            assert config.get_field("alias-pm") == "other-value"

        # Override released — back to the ambient CONFIG_PATH.
        assert config.get_field("alias-pm") == "real-value"

    def test_deploy_role_v2_reads_target_config_not_installing_clone(self, tmp_path, monkeypatch):
        """Same regression, via the wizard's deploy_role_v2 path (hermetic
        install; source_root/target_root split)."""
        installing_clone_config = tmp_path / "installing-clone" / ".squidsquad" / "config.md"
        installing_clone_config.parent.mkdir(parents=True, exist_ok=True)
        installing_clone_config.write_text(
            "## Aliases\n\n- **pm**: INSTALLING-CLONE-LEAK\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(config, "CONFIG_PATH", installing_clone_config)

        source_root = tmp_path / "source"
        _stage_minimal_install(source_root, pm_alias_value="source-unused")

        target_root = tmp_path / "foreign-target"
        _stage_minimal_install(target_root, pm_alias_value="foreign-pm-v2")

        out = compose.deploy_role_v2(
            "pm", target_root=target_root, source_root=source_root,
            output_name="pm",
        )
        text = Path(out).read_text(encoding="utf-8")

        assert "foreign-pm-v2" in text
        assert "INSTALLING-CLONE-LEAK" not in text
