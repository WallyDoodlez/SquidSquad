"""Regression tests for #10981 — three token-leak classes that escaped
``deploy_alias_v2`` (and ``deploy_role_v2``) until cycle 1579:

- B1: ``{{include: <path>}}`` directives left in L2 ``instructions.md``
  bodies were emitted verbatim because v1's ``_resolve_includes`` was
  deleted in Phase 3d.5 and no v2 replacement existed.
- B2: ``[ROLE]`` / ``[ACTIVE_AGENTS]`` / ``[OTHER_ROLES]`` / ``[INTERVAL]``
  / ``[ROLE_TEST_CMD]`` / ``[E2E_TEST_CMD]`` / ``[POLLING_FRAGMENT_PATH]``
  placeholders leaked because ``deploy_alias_v2`` skipped the
  ``_substitute_placeholders`` call (and ``deploy_role_v2`` covered B2
  but not B3).
- B3: ``{{role-roster}}`` leaked because ``_inject_role_roster`` had
  zero call sites after Phase 3d.5.

These tests run ``deploy_alias_v2`` and ``deploy_role_v2`` end-to-end
against a hermetic install whose L2 instructions.md contains exactly the
v1-era tokens that leak in production, and assert the assembled CLAUDE.md
carries none of them.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import compose  # noqa: E402
import atomic_emit  # noqa: E402


LEAK_TOKENS = [
    "[ROLE]",
    "[ROLE_UPPER]",
    "[ACTIVE_AGENTS]",
    "[OTHER_ROLES]",
    "[ROLE_TEST_CMD]",
    "[E2E_TEST_CMD]",
    "[INTERVAL]",
    "[POLLING_FRAGMENT_PATH]",
    "{{role-roster}}",
    "{{include:",
    "<!-- ERROR: Missing include:",
]


@pytest.fixture(autouse=True)
def _stub_assemble_pipeline(monkeypatch):
    """Echo-stub the LLM-backed assemble pass — we exercise the deterministic
    substitution chain, not the LLM."""

    def fake_assemble_and_emit(
        linked_composite, output_dir, *, role_class, model_id=None,
        commit_sha=None, generated_at=None, filename_suffix="",
        **kwargs,
    ):
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        if filename_suffix == "":
            base, linked, conflicts = (
                "CLAUDE.md", "CLAUDE.linked.md", "CLAUDE.conflicts.md",
            )
        else:
            base = f"CLAUDE{filename_suffix}"
            linked = f"CLAUDE.linked{filename_suffix}"
            conflicts = f"CLAUDE.conflicts{filename_suffix}"
        (output_dir / base).write_text(linked_composite, encoding="utf-8")
        (output_dir / linked).write_text(linked_composite, encoding="utf-8")
        (output_dir / conflicts).write_text(
            "# Stub conflicts report — assemble bypassed in tests\n",
            encoding="utf-8",
        )
        return (
            output_dir / base,
            output_dir / linked,
            output_dir / conflicts,
        )

    monkeypatch.setattr(atomic_emit, "assemble_and_emit", fake_assemble_and_emit)


@pytest.fixture(autouse=True)
def _stub_soul_seeding(monkeypatch):
    """Stub SOUL.md seeding — orthogonal to the leak surface under test."""

    def fake_assemble_and_write_soul(role_name, target_root, output_name):
        soul_path = Path(target_root) / ".squidsquad" / output_name / "SOUL.md"
        soul_path.parent.mkdir(parents=True, exist_ok=True)
        soul_path.write_text(f"# Stub SOUL.md for {output_name}\n", encoding="utf-8")
        return soul_path

    monkeypatch.setattr(
        compose, "_assemble_and_write_soul", fake_assemble_and_write_soul,
    )


@pytest.fixture(autouse=True)
def _stub_config_reads(monkeypatch):
    """Provide deterministic config values for ``_substitute_placeholders``."""

    def fake_read_config_value(field):
        return {
            "interval": "42",
            "workers": "pm, dm, verifier, skill",
            "e2e-tests": "pytest tests/e2e",
            "skill-tests": "pytest tests/",
        }.get(field, "")

    monkeypatch.setattr(compose, "_read_config_value", fake_read_config_value)


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


def _stage_install_with_leak_surface(tmp_path, alias, role):
    """Install where the L2 instructions.md carries every leak class.

    Per-role placeholder sets mirror production: ``_substitute_placeholders``
    only substitutes ``[OTHER_ROLES]`` / ``[ROLE_TEST_CMD]`` when the
    entry_file is ``dev``/``worker``, and ``[ACTIVE_AGENTS]`` /
    ``[E2E_TEST_CMD]`` only when it ISN'T. Putting all of them in every
    role's body would assert against a contract this helper doesn't claim.
    """
    refs = tmp_path / "references"
    _write_source(refs / "roles" / "identity.md", "identity", 10, "Identity base.")
    _write_source(
        refs / "roles" / "responsibility.md", "responsibility", 10,
        "Responsibility base.",
    )
    _write_source(refs / "roles" / "SOUL.md", "soul", 10, "Soul base.")
    _write_source(
        refs / "roles" / "instructions.md", "instructions", 10,
        "### step:cycle/boot\nBoot body.\n",
    )
    _write_source(refs / "roles" / "vault.md", "vault", 10, "Vault base.")

    is_worker = role in ("worker", "dev")
    role_specific = (
        "Other roles: [OTHER_ROLES]. Tests: `[ROLE_TEST_CMD]`.\n"
        if is_worker
        else "Active agents: **[ACTIVE_AGENTS]**. E2E: `[E2E_TEST_CMD]`.\n"
    )
    l2_body = (
        f"This is the [ROLE] agent ([ROLE_UPPER]).\n"
        f"{role_specific}"
        "Cycle interval: [INTERVAL]m. Polling: [POLLING_FRAGMENT_PATH].\n"
        "\n"
        "{{include: common/example-helper}}\n"
        "\n"
        "{{role-roster}}\n"
    )
    _write_source(
        refs / "roles" / role / "instructions.md", "instructions", 20,
        l2_body, roles=[role],
    )

    # The referenced sub-skill body — must exist for the include to expand
    # without an `<!-- ERROR: Missing include: ... -->` marker.
    sub_skills = refs / "sub-skills" / "common"
    sub_skills.mkdir(parents=True, exist_ok=True)
    (sub_skills / "example-helper.md").write_text(
        _frontmatter("instructions", 30) + "\n\nExample helper body.\n",
        encoding="utf-8",
    )

    catalog = tmp_path / "docs" / "sub-skill-catalog.md"
    catalog.parent.mkdir(parents=True, exist_ok=True)
    catalog.write_text(
        "## `common/` — Cross-cutting\n\n"
        "| Sub-skill | One-liner | Used by |\n"
        "|---|---|---|\n"
        "| `boot-bootstrap` | Mode detection | all |\n"
        "| `example-helper` | Hermetic test fixture | all |\n",
        encoding="utf-8",
    )

    config_md = tmp_path / ".squidsquad" / "config.md"
    config_md.parent.mkdir(parents=True, exist_ok=True)
    config_md.write_text(
        "## Aliases\n\n"
        "| alias | role-class | L3 domain |\n"
        "|---|---|---|\n"
        f"| {alias} | {role} | |\n",
        encoding="utf-8",
    )
    return tmp_path


def _mk_registry(alias, role):
    return {alias: (role, None)}


def _read_assembled(path):
    return Path(path).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# B1 + B2 + B3 — deploy_alias_v2 (operator + harness path)
# ---------------------------------------------------------------------------

class TestDeployAliasV2NoTokenLeaks:
    """The operator-facing ``deploy <alias>`` path must emit a clean
    CLAUDE.md across every leak class.

    ``deploy_alias_v2`` doesn't accept a ``source_root`` parameter — it
    reads sub-skills from the module-level ``SUB_SKILLS_DIR``. Tests
    monkeypatch that constant to point at the staged install.
    """

    @pytest.fixture(autouse=True)
    def _redirect_sub_skills_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            compose, "SUB_SKILLS_DIR", tmp_path / "references" / "sub-skills",
        )

    @pytest.mark.parametrize("role", ["pm", "dm", "verifier"])
    def test_no_unresolved_tokens_in_assembled_output(self, tmp_path, role):
        alias = role
        _stage_install_with_leak_surface(tmp_path, alias=alias, role=role)
        out = compose.deploy_alias_v2(
            alias, registry=_mk_registry(alias, role), target_root=tmp_path,
        )
        body = _read_assembled(out)
        leaked = [t for t in LEAK_TOKENS if t in body]
        assert leaked == [], (
            f"#10981 regression for role={role}: tokens leaked into "
            f"assembled CLAUDE.md: {leaked}"
        )

    def test_role_placeholder_substituted_with_alias(self, tmp_path):
        _stage_install_with_leak_surface(tmp_path, alias="pm", role="pm")
        out = compose.deploy_alias_v2(
            "pm", registry=_mk_registry("pm", "pm"), target_root=tmp_path,
        )
        body = _read_assembled(out)
        assert "This is the pm agent" in body, (
            f"[ROLE] should be replaced with alias 'pm'; got body sample: "
            f"{body[:500]}"
        )

    def test_included_sub_skill_body_inlined(self, tmp_path):
        _stage_install_with_leak_surface(tmp_path, alias="pm", role="pm")
        out = compose.deploy_alias_v2(
            "pm", registry=_mk_registry("pm", "pm"), target_root=tmp_path,
        )
        body = _read_assembled(out)
        assert "Example helper body." in body, (
            "{{include: common/example-helper}} should expand to the "
            "sub-skill body"
        )
        assert "<!-- sub-skill: example-helper -->" in body, (
            "inlined fragment should be wrapped in canonical "
            "<!-- sub-skill: ... --> markers"
        )


# ---------------------------------------------------------------------------
# B1 + B2 + B3 — deploy_role_v2 (wizard fresh-install path)
# ---------------------------------------------------------------------------

class TestDeployRoleV2NoTokenLeaks:
    """The wizard path must produce the same clean output as the alias
    path — pre-#10981 it covered B2 only and leaked B1 + B3."""

    def test_no_unresolved_tokens_in_assembled_output(self, tmp_path):
        _stage_install_with_leak_surface(tmp_path, alias="pm", role="pm")
        out = compose.deploy_role_v2(
            "pm", target_root=tmp_path, output_name="pm", source_root=tmp_path,
        )
        body = _read_assembled(out)
        leaked = [t for t in LEAK_TOKENS if t in body]
        assert leaked == [], (
            f"#10981 regression in deploy_role_v2: tokens leaked into "
            f"assembled CLAUDE.md: {leaked}"
        )


# ---------------------------------------------------------------------------
# _resolve_includes_v2 unit behaviors
# ---------------------------------------------------------------------------

class TestResolveIncludesV2:
    """Focused tests for the directive-expansion helper."""

    def test_expands_valid_include_directive(self, tmp_path, monkeypatch):
        sub = tmp_path / "sub-skills" / "common"
        sub.mkdir(parents=True)
        (sub / "foo.md").write_text("Foo body.\n", encoding="utf-8")
        monkeypatch.setattr(compose, "SUB_SKILLS_DIR", tmp_path / "sub-skills")
        out = compose._resolve_includes_v2("{{include: common/foo}}\n")
        assert "<!-- sub-skill: foo -->" in out
        assert "Foo body." in out
        assert "<!-- /sub-skill: foo -->" in out
        assert "{{include:" not in out

    def test_missing_include_emits_error_marker(self, tmp_path, monkeypatch):
        monkeypatch.setattr(compose, "SUB_SKILLS_DIR", tmp_path / "sub-skills")
        out = compose._resolve_includes_v2("{{include: common/nonexistent}}\n")
        assert "<!-- ERROR: Missing include: common/nonexistent -->" in out
        assert "{{include:" not in out

    def test_runtime_read_fragment_directive_is_dropped(self):
        # Any path in RUNTIME_READ_FRAGMENTS must not be inlined (the #9588
        # lazy-load fragments are Read at runtime, not at compose time).
        rt_path = next(iter(compose.RUNTIME_READ_FRAGMENTS))
        out = compose._resolve_includes_v2(f"{{{{include: {rt_path}}}}}\n")
        assert "{{include:" not in out
        assert "<!-- sub-skill:" not in out, (
            f"runtime fragment '{rt_path}' should be dropped, not inlined"
        )

    def test_strips_yaml_frontmatter_from_included_body(self, tmp_path, monkeypatch):
        sub = tmp_path / "sub-skills" / "common"
        sub.mkdir(parents=True)
        (sub / "foo.md").write_text(
            "---\nslot: instructions\nordinal: 30\n---\n\nFoo body.\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(compose, "SUB_SKILLS_DIR", tmp_path / "sub-skills")
        out = compose._resolve_includes_v2("{{include: common/foo}}\n")
        assert "slot: instructions" not in out
        assert "Foo body." in out

    def test_strips_outer_sub_skill_markers_to_avoid_doubling(self, tmp_path, monkeypatch):
        sub = tmp_path / "sub-skills" / "common"
        sub.mkdir(parents=True)
        (sub / "foo.md").write_text(
            "<!-- sub-skill: foo -->\nFoo body.\n<!-- /sub-skill: foo -->\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(compose, "SUB_SKILLS_DIR", tmp_path / "sub-skills")
        out = compose._resolve_includes_v2("{{include: common/foo}}\n")
        # Exactly one open + one close marker — not two of each.
        assert out.count("<!-- sub-skill: foo -->") == 1
        assert out.count("<!-- /sub-skill: foo -->") == 1
