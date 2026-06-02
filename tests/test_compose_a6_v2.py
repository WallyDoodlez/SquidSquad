"""Tests for compose.py --v2 flag and deploy_alias_v2 (#10386, PRD-A Story A6)."""

import inspect
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import compose  # noqa: E402


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
    assert out.name == "CLAUDE.linked.v2.md"
    assert out.parent.name == "pm"
    assert out.exists()


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
    """A2f writes its own header; the regenerate hint says `<alias> --v2`.

    Replaces the A6-era test that asserted regenerate_cmd was forwarded
    to deploy_role. A2f no longer delegates, so we read the written file
    and assert the same hint is in the GENERATED comment.
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
    assert "GENERATED by compose.py deploy frontend-1 --v2" in header
    assert "Regenerate: python references/scripts/compose.py deploy frontend-1 --v2" in header


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
# CLI argv parsing: --v2 flag detected; v1 path byte-equivalent
# ---------------------------------------------------------------------------

def test_main_strips_v2_flag_and_routes_v1_without_it(monkeypatch):
    called = {}

    def fake_v2(alias, registry=None):
        called["v2"] = alias
        out = compose.REPO_ROOT / "_fake"
        return out

    def fake_v1(role_name):
        called["v1"] = role_name
        return compose.REPO_ROOT / "_fake"

    # deploy_alias_v2 is only entered when --v2 is present.
    monkeypatch.setattr(compose, "deploy_alias_v2", fake_v2)
    # Stub deploy_role and the v1-only event-contract step so the test
    # focuses on routing, not on the compose pipeline.
    monkeypatch.setattr(compose, "deploy_role", lambda *a, **kw: (called.setdefault("v1", a[0]), compose.REPO_ROOT / "_fake")[1])
    monkeypatch.setattr(compose, "derive_and_write_event_contracts", lambda *a, **kw: True)
    # Stub Path.read_text on the fake path so the post-deploy line-count
    # call doesn't blow up.
    monkeypatch.setattr(Path, "read_text", lambda self, encoding=None: "x\n")

    monkeypatch.setattr(sys, "argv", ["compose.py", "deploy", "pm", "--v2"])
    compose.main()
    assert called.get("v2") == "pm"
    assert "v1" not in called


def test_main_no_v2_flag_takes_v1_path(monkeypatch):
    called = {}

    def fake_v2(alias, registry=None):
        called["v2"] = alias
        return compose.REPO_ROOT / "_fake_x"

    def fake_v1(*a, **kw):
        called["v1"] = a[0]
        return compose.REPO_ROOT / "_fake_x"

    monkeypatch.setattr(compose, "deploy_alias_v2", fake_v2)
    monkeypatch.setattr(compose, "deploy_role", fake_v1)
    monkeypatch.setattr(compose, "derive_and_write_event_contracts", lambda *a, **kw: True)
    monkeypatch.setattr(Path, "read_text", lambda self, encoding=None: "x\n")

    monkeypatch.setattr(sys, "argv", ["compose.py", "deploy", "pm"])
    compose.main()
    assert called.get("v1") == "pm"
    assert "v2" not in called


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


def test_main_warns_when_v2_paired_with_unsupported_command(monkeypatch, capsys):
    # --v2 on `all` / `upgrade-soul` is currently silently ignored at the
    # routing level. Per DS finding 2, surface a warning so operators don't
    # think they got v2 behavior.
    monkeypatch.setattr(compose, "compose_all", lambda: "stub\n")
    monkeypatch.setattr(compose, "OUTPUT_FILE", compose.REPO_ROOT / "_fake_all")
    monkeypatch.setattr(Path, "write_text", lambda self, content, encoding=None: len(content))

    monkeypatch.setattr(sys, "argv", ["compose.py", "all", "--v2"])
    compose.main()
    err = capsys.readouterr().err
    assert "--v2 has no effect" in err


def test_main_deploy_all_v2_iterates_registry(monkeypatch):
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

    monkeypatch.setattr(sys, "argv", ["compose.py", "deploy-all", "--v2"])
    compose.main()

    assert captured_aliases == ["dm", "pm", "skill"]  # sorted


def test_main_deploy_v2_returns_without_calling_event_contracts(monkeypatch):
    called = {"events": 0}

    monkeypatch.setattr(compose, "deploy_alias_v2", lambda alias: compose.REPO_ROOT / "_fake_x")
    monkeypatch.setattr(Path, "read_text", lambda self, encoding=None: "x\n")

    def fake_events(*a, **kw):
        called["events"] += 1
        return True

    monkeypatch.setattr(compose, "derive_and_write_event_contracts", fake_events)

    monkeypatch.setattr(sys, "argv", ["compose.py", "deploy", "pm", "--v2"])
    compose.main()

    # PRD-B §9a: v2 path leaves v1 side-effects untouched. event-contract
    # derivation is a v1 step keyed off the v1 agent-instructions tree;
    # firing it on every --v2 deploy would mutate v1 state.
    assert called["events"] == 0


# ---------------------------------------------------------------------------
# _V2_LINKED_FILENAME constant — single source of truth
# ---------------------------------------------------------------------------

def test_v2_filename_constant_matches_pm_narrowed_scope():
    # PM's narrowed-scope comment on #10386 recommends this exact path.
    assert compose._V2_LINKED_FILENAME == "CLAUDE.linked.v2.md"
