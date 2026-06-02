"""Tests for compose.py --v2 flag and deploy_alias_v2 (#10386, PRD-A Story A6)."""

import inspect
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import compose  # noqa: E402
import atomic_emit  # noqa: E402 — needed by the assemble-stub fixture


@pytest.fixture(autouse=True)
def _stub_assemble_pipeline(monkeypatch):
    """A6 tests assert against ``deploy_alias_v2``'s routing + output
    filename contract. PRD-B B9 (#10763) wires the assemble pipeline
    in after the link stage; without a real LLM provider those tests
    would fail. Stub ``atomic_emit.assemble_and_emit`` to write the
    triple deterministically — same content for the linked + assembled
    files so existing assertions on header content still pass."""

    def fake_assemble_and_emit(
        linked_composite, output_dir, *, role_class, model_id=None,
        commit_sha=None, generated_at=None, filename_suffix=".v2.md",
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


def _stage_minimal_catalog(target_root):
    """PRD-D D3 (#10674) added a catalog gate inside ``deploy_alias_v2``
    that reads ``<target_root>/docs/sub-skill-catalog.md`` after
    ``emit_v2_linked`` returns. Tests that mock the emit stage but
    still drive the full ``deploy_alias_v2`` body must provide a
    minimal catalog so the gate's parser can succeed. A single
    ``common/`` row is enough — the emitted body in these tests
    contains no ``→ run sub-skill:`` references for the gate to look
    up, so the catalog only needs to be parseable.
    """
    catalog = Path(target_root) / "docs" / "sub-skill-catalog.md"
    catalog.parent.mkdir(parents=True, exist_ok=True)
    catalog.write_text(
        "## `common/` — Cross-cutting\n\n"
        "| Sub-skill | One-liner | Used by |\n"
        "|---|---|---|\n"
        "| `boot-bootstrap` | Mode detection | all |\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# deploy_role: backward compatibility for v1 (output_filename default)
# ---------------------------------------------------------------------------

def test_deploy_role_output_filename_defaults_to_v1():
    sig = inspect.signature(compose.deploy_role)
    assert sig.parameters["output_filename"].default == "CLAUDE.md"


def test_deploy_role_preserves_role_parameter_name():
    # #10358: the public signature keeps `role_name` (compose's existing
    # name for what the rest of the code treats as the role-class).
    sig = inspect.signature(compose.deploy_role)
    assert "role_name" in sig.parameters
    # First positional param.
    first = next(iter(sig.parameters))
    assert first == "role_name"


def test_deploy_alias_v2_preserves_role_variable_name_per_10358():
    # #10358: variable name `role` is preserved in code signatures. The
    # PUBLIC argument here is an alias (because the caller passes one),
    # but the INNER variable that holds the resolved role-class must
    # still be called `role`. Read the source and assert the binding
    # name is `role`. A2f (#10492) uses both `role` and `l3_domain` —
    # the underscore guard that A6 relied on is no longer correct.
    src = inspect.getsource(compose.deploy_alias_v2)
    assert "role, l3_domain" in src, (
        "deploy_alias_v2 must bind the resolved role-class to a variable "
        "named `role` per #10358 (A2f uses l3_domain — no underscore)"
    )


# ---------------------------------------------------------------------------
# deploy_alias_v2: alias resolution + abort semantics
# ---------------------------------------------------------------------------

_FAKE_REGISTRY = {
    "pm": ("pm", None),
    "frontend-1": ("worker", "frontend"),
}


def test_deploy_alias_v2_resolves_via_parser_and_writes_v2_path(tmp_path, monkeypatch):
    """A2f (#10492): deploy_alias_v2 walks v2 link stage; output lands at the v2 filename.

    Prior to A2f the body delegated to deploy_role and this test mocked
    that call. A2f replaces that with collect_sources_for_validation +
    emit_v2_linked; we mock those instead so the test stays focused on
    the routing contract (alias resolves to role-class, output filename
    is CLAUDE.linked.v2.md).
    """
    monkeypatch.setattr(
        compose._config_module, "parse_aliases_registry",
        lambda: dict(_FAKE_REGISTRY),
    )
    import v2_link_stage
    captured = {}

    def fake_emit(role_class, l3_domain, *, repo_root=None, l4_path=None):
        captured["role_class"] = role_class
        return "v2 body\n"

    monkeypatch.setattr(v2_link_stage, "collect_sources_for_validation",
                        lambda role_class, l3_domain, repo_root=None: [])
    monkeypatch.setattr(v2_link_stage, "emit_v2_linked", fake_emit)
    _stage_minimal_catalog(tmp_path)

    out = compose.deploy_alias_v2("pm", target_root=tmp_path)

    assert captured["role_class"] == "pm"
    # PRD-B B9 (#10763): post-wire, deploy_alias_v2 returns the
    # assembled CLAUDE.v2.md (the runtime artifact) rather than the
    # linked composite. Both live in the alias dir.
    assert out.name == "CLAUDE.v2.md"
    assert out.parent.name == "pm"
    assert out.exists()
    assert (out.parent / "CLAUDE.linked.v2.md").exists()


def test_deploy_alias_v2_uses_role_class_not_alias_for_compose_source(tmp_path, monkeypatch):
    """The compose SOURCE is the role-class; the OUTPUT DIR is the alias.

    Path-keying invariant from COMPOSE-ARCHITECTURE §1 + #10386 AC #4.
    A2f preserves it — collect_sources_for_validation receives the
    role-class, output lands under the alias.
    """
    monkeypatch.setattr(
        compose._config_module, "parse_aliases_registry",
        lambda: dict(_FAKE_REGISTRY),
    )
    import v2_link_stage
    captured = {}

    def fake_collect(role_class, l3_domain, repo_root=None):
        captured["role_class"] = role_class
        return []

    monkeypatch.setattr(v2_link_stage, "collect_sources_for_validation", fake_collect)
    monkeypatch.setattr(v2_link_stage, "emit_v2_linked",
                        lambda role_class, l3_domain, *, repo_root=None, l4_path=None: "x")
    _stage_minimal_catalog(tmp_path)

    out = compose.deploy_alias_v2("frontend-1", target_root=tmp_path)

    assert captured["role_class"] == "worker"
    assert out.parent.name == "frontend-1"


def test_deploy_alias_v2_aborts_on_unknown_alias(monkeypatch, capsys):
    monkeypatch.setattr(
        compose._config_module, "parse_aliases_registry",
        lambda: dict(_FAKE_REGISTRY),
    )
    with pytest.raises(SystemExit) as exc:
        compose.deploy_alias_v2("bogus-alias")
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "bogus-alias" in err
    assert "not found" in err


def test_deploy_alias_v2_lists_known_aliases_in_diagnostic(monkeypatch, capsys):
    monkeypatch.setattr(
        compose._config_module, "parse_aliases_registry",
        lambda: dict(_FAKE_REGISTRY),
    )
    with pytest.raises(SystemExit):
        compose.deploy_alias_v2("ghost")
    err = capsys.readouterr().err
    # Sorted list helps the operator find a close match.
    assert "frontend-1" in err
    assert "pm" in err


@pytest.mark.parametrize(
    "bad_alias",
    ["../etc", "a/b", "a\\b", "", ".hidden", "with space", None, 42, "a\x00b"],
)
def test_deploy_alias_v2_rejects_disallowed_alias_characters(bad_alias, capsys):
    with pytest.raises(SystemExit) as exc:
        compose.deploy_alias_v2(bad_alias)
    assert exc.value.code == 1
    assert "disallowed characters" in capsys.readouterr().err


def test_deploy_alias_v2_passes_registry_through(tmp_path, monkeypatch):
    # DS finding 5: deploy_alias_v2 must NOT re-parse when caller provided
    # a registry — that's both wasteful (deploy-all calls N times) and a
    # TOCTOU window (config.md could shift between parses).
    calls = {"parse": 0}

    def boom():
        calls["parse"] += 1
        raise RuntimeError("must not be called when registry is provided")

    monkeypatch.setattr(compose._config_module, "parse_aliases_registry", boom)
    import v2_link_stage
    monkeypatch.setattr(v2_link_stage, "collect_sources_for_validation",
                        lambda role_class, l3_domain, repo_root=None: [])
    monkeypatch.setattr(v2_link_stage, "emit_v2_linked",
                        lambda role_class, l3_domain, *, repo_root=None, l4_path=None: "body")
    _stage_minimal_catalog(tmp_path)
    compose.deploy_alias_v2("pm", registry={"pm": ("pm", None)}, target_root=tmp_path)
    assert calls["parse"] == 0


def test_deploy_alias_v2_v2_regenerate_cmd_in_output_header(tmp_path, monkeypatch):
    """A2f writes its own header; the regenerate hint says ``deploy <alias>``.

    Replaces the A6-era test that asserted regenerate_cmd was forwarded
    to deploy_role. A2f no longer delegates, so we read the written file
    and assert the same hint is in the GENERATED comment. Post-E6
    cutover (#10685) the ``--v2`` flag is retired — the hint is the
    bare ``deploy <alias>`` form.
    """
    monkeypatch.setattr(
        compose._config_module, "parse_aliases_registry",
        lambda: {"pm": ("pm", None), "frontend-1": ("worker", "frontend")},
    )
    import v2_link_stage
    monkeypatch.setattr(v2_link_stage, "collect_sources_for_validation",
                        lambda role_class, l3_domain, repo_root=None: [])
    monkeypatch.setattr(v2_link_stage, "emit_v2_linked",
                        lambda role_class, l3_domain, *, repo_root=None, l4_path=None: "body")
    _stage_minimal_catalog(tmp_path)

    out = compose.deploy_alias_v2("frontend-1", target_root=tmp_path)
    header = out.read_text(encoding="utf-8")
    assert "GENERATED by compose.py deploy frontend-1." in header
    assert "Regenerate: python references/scripts/compose.py deploy frontend-1" in header
    # Sanity: post-E6 the hint must NOT mention the retired flag.
    assert "--v2" not in header


def test_deploy_role_default_regenerate_cmd_preserves_v1_header(monkeypatch):
    # When regenerate_cmd is not passed, the v1 header must say
    # `deploy <role_name>` — same wording as pre-A6 (§9a byte-equivalence
    # already verified via stash/restore/diff, but lock it at unit level too).
    sig = inspect.signature(compose.deploy_role)
    assert sig.parameters["regenerate_cmd"].default is None


def test_deploy_alias_v2_aborts_on_malformed_registry(monkeypatch, capsys):
    def boom():
        raise compose._config_module.AliasesRegistryError("malformed table")
    monkeypatch.setattr(compose._config_module, "parse_aliases_registry", boom)
    with pytest.raises(SystemExit) as exc:
        compose.deploy_alias_v2("pm")
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "malformed table" in err


# ---------------------------------------------------------------------------
# CLI argv parsing: --v2 is silently stripped for backward compat
# ---------------------------------------------------------------------------

def test_main_strips_v2_flag_and_routes_to_v2(monkeypatch):
    """Post-E6 cutover (#10685): ``--v2`` is silently stripped from argv;
    the surviving compose path is ``deploy_alias_v2`` regardless of the
    flag's presence. Pre-cutover this test asserted that ``--v2`` was the
    opt-in for ``deploy_alias_v2``; that distinction is retired.
    """
    called = {}

    def fake_v2(alias, registry=None):
        called["v2"] = alias
        return compose.REPO_ROOT / "_fake"

    monkeypatch.setattr(compose, "deploy_alias_v2", fake_v2)
    monkeypatch.setattr(Path, "read_text", lambda self, encoding=None: "x\n")

    monkeypatch.setattr(sys, "argv", ["compose.py", "deploy", "pm", "--v2"])
    compose.main()
    assert called.get("v2") == "pm"


def test_main_no_v2_flag_takes_v2_path(monkeypatch):
    """Post-E6 cutover (#10685): the bare ``deploy <alias>`` invocation
    routes to the v2 alias-aware path. Pre-E6 this test asserted the v1
    fallback; the v1 path is now retired."""
    called = {}

    def fake_v2(alias, registry=None):
        called["v2"] = alias
        return compose.REPO_ROOT / "_fake_x"

    monkeypatch.setattr(compose, "deploy_alias_v2", fake_v2)
    monkeypatch.setattr(Path, "read_text", lambda self, encoding=None: "x\n")

    monkeypatch.setattr(sys, "argv", ["compose.py", "deploy", "pm"])
    compose.main()
    assert called.get("v2") == "pm"


@pytest.mark.parametrize(
    "argv",
    [
        ["compose.py", "deploy", "pm", "--v2"],
        ["compose.py", "deploy", "--v2", "pm"],
        ["compose.py", "--v2", "deploy", "pm"],
    ],
)
def test_main_v2_flag_position_does_not_matter(monkeypatch, argv):
    called = {}

    def fake_v2(alias, registry=None):
        called["v2"] = alias
        return compose.REPO_ROOT / "_fake_x"

    monkeypatch.setattr(compose, "deploy_alias_v2", fake_v2)
    monkeypatch.setattr(Path, "read_text", lambda self, encoding=None: "x\n")

    monkeypatch.setattr(sys, "argv", argv)
    compose.main()
    assert called.get("v2") == "pm"


def test_main_accepts_legacy_v2_flag_silently(monkeypatch, capsys):
    """Post-E6 cutover (#10685): ``--v2`` is silently stripped from argv
    for backward compatibility with pre-cutover wrappers / docs /
    muscle memory. The pre-cutover warning ("--v2 has no effect on …")
    is retired.
    """
    monkeypatch.setattr(compose, "compose_all", lambda: "stub\n")
    monkeypatch.setattr(compose, "OUTPUT_FILE", compose.REPO_ROOT / "_fake_all")
    monkeypatch.setattr(Path, "write_text", lambda self, content, encoding=None: len(content))

    monkeypatch.setattr(sys, "argv", ["compose.py", "all", "--v2"])
    compose.main()
    err = capsys.readouterr().err
    assert "--v2" not in err


def test_main_deploy_all_v2_iterates_registry(monkeypatch, tmp_path):
    captured_aliases = []

    def fake_v2(alias, registry=None):
        captured_aliases.append(alias)
        out = compose.REPO_ROOT / f"_fake_{alias}"
        return out

    monkeypatch.setattr(compose, "deploy_alias_v2", fake_v2)
    monkeypatch.setattr(
        compose._config_module, "parse_aliases_registry",
        lambda: {"pm": ("pm", None), "dm": ("dm", None), "skill": ("worker", None)},
    )
    monkeypatch.setattr(Path, "read_text", lambda self, encoding=None: "x\n")
    # Post-cutover the deploy-all path no longer returns after the alias
    # loop — it falls through to install topology bookkeeping (mandatory-
    # role check + generate_local_config). Stub those so the test stays
    # isolated and does NOT touch the real ``.squidsquad/.local-config``.
    monkeypatch.setattr(compose, "_collect_all_roles", lambda: ["pm", "verifier", "dm"])
    monkeypatch.setattr(compose, "_check_mandatory_roles", lambda roles: [])
    # ``generate_local_config`` must return a Path under REPO_ROOT because
    # compose.py prints it via ``.relative_to(REPO_ROOT)``. Use a fake
    # under-root path; never reach disk.
    monkeypatch.setattr(
        compose, "generate_local_config", lambda roles: compose.REPO_ROOT / "_fake_local_config"
    )
    monkeypatch.setattr(Path, "write_text", lambda self, content, encoding=None: len(content))

    monkeypatch.setattr(sys, "argv", ["compose.py", "deploy-all", "--v2"])
    compose.main()

    assert captured_aliases == ["dm", "pm", "skill"]  # sorted


# DS-10685-phase2 F3: ``test_main_deploy_v2_returns_without_calling_event_contracts``
# deleted. Post-cutover both ``deploy`` and ``deploy-all`` retired the
# ``derive_and_write_event_contracts`` call from all paths, so asserting
# "v2 doesn't call it" is now a tautology that gives false confidence.
# The distinction the test was designed to validate (v2 path leaves v1
# side-effects untouched) no longer exists because there is no v1 path.


# ---------------------------------------------------------------------------
# _V2_LINKED_FILENAME constant — single source of truth
# ---------------------------------------------------------------------------

def test_v2_filename_constant_matches_pm_narrowed_scope():
    # PM's narrowed-scope comment on #10386 recommends this exact path.
    assert compose._V2_LINKED_FILENAME == "CLAUDE.linked.v2.md"
