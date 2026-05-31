"""Tests for compose.py --v2 flag and deploy_alias_v2 (#10386, PRD-A Story A6)."""

import inspect
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import compose  # noqa: E402


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
    # name is `role`.
    src = inspect.getsource(compose.deploy_alias_v2)
    assert "role, _l3_domain" in src, (
        "deploy_alias_v2 must bind the resolved role-class to a variable "
        "named `role` per #10358"
    )


# ---------------------------------------------------------------------------
# deploy_alias_v2: alias resolution + abort semantics
# ---------------------------------------------------------------------------

_FAKE_REGISTRY = {
    "pm": ("pm", None),
    "frontend-1": ("worker", "frontend"),
}


def test_deploy_alias_v2_resolves_via_parser_and_writes_v2_path(tmp_path, monkeypatch):
    monkeypatch.setattr(
        compose._config_module, "parse_aliases_registry",
        lambda: dict(_FAKE_REGISTRY),
    )
    captured = {}

    def fake_deploy_role(role_name, target_root=None, output_name=None,
                         output_filename="CLAUDE.md", regenerate_cmd=None):
        captured["role_name"] = role_name
        captured["output_name"] = output_name
        captured["output_filename"] = output_filename
        captured["regenerate_cmd"] = regenerate_cmd
        out = tmp_path / ".squidsquad" / output_name / output_filename
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("placeholder body\n", encoding="utf-8")
        return out

    monkeypatch.setattr(compose, "deploy_role", fake_deploy_role)

    out = compose.deploy_alias_v2("pm")

    assert captured["role_name"] == "pm"
    assert captured["output_name"] == "pm"
    assert captured["output_filename"] == "CLAUDE.linked.v2.md"
    assert out.name == "CLAUDE.linked.v2.md"
    assert out.parent.name == "pm"


def test_deploy_alias_v2_uses_role_class_not_alias_for_compose_source(tmp_path, monkeypatch):
    monkeypatch.setattr(
        compose._config_module, "parse_aliases_registry",
        lambda: dict(_FAKE_REGISTRY),
    )
    captured = {}

    def fake_deploy_role(role_name, target_root=None, output_name=None,
                         output_filename="CLAUDE.md", regenerate_cmd=None):
        captured["role_name"] = role_name
        captured["output_name"] = output_name
        out = tmp_path / ".squidsquad" / output_name / output_filename
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("x", encoding="utf-8")
        return out

    monkeypatch.setattr(compose, "deploy_role", fake_deploy_role)

    compose.deploy_alias_v2("frontend-1")

    # The compose SOURCE is the role-class ('worker'); the OUTPUT DIR is
    # the alias ('frontend-1') — the path-keying invariant from
    # COMPOSE-ARCHITECTURE §1 + #10386 AC #4.
    assert captured["role_name"] == "worker"
    assert captured["output_name"] == "frontend-1"


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


def test_deploy_alias_v2_passes_registry_through(monkeypatch):
    # DS finding 5: deploy_alias_v2 must NOT re-parse when caller provided
    # a registry — that's both wasteful (deploy-all calls N times) and a
    # TOCTOU window (config.md could shift between parses).
    calls = {"parse": 0}

    def boom():
        calls["parse"] += 1
        raise RuntimeError("must not be called when registry is provided")

    monkeypatch.setattr(compose._config_module, "parse_aliases_registry", boom)
    monkeypatch.setattr(
        compose, "deploy_role",
        lambda *a, **kw: compose.REPO_ROOT / "_fake_pm",
    )
    compose.deploy_alias_v2("pm", registry={"pm": ("pm", None)})
    assert calls["parse"] == 0


def test_deploy_alias_v2_passes_v2_regenerate_cmd_to_deploy_role(monkeypatch):
    # DS finding 3: the regenerate hint embedded in the v2 file header
    # must say `<alias> --v2`, not the v1 role-class shorthand.
    captured = {}

    def fake_deploy_role(role_name, target_root=None, output_name=None,
                         output_filename="CLAUDE.md", regenerate_cmd=None):
        captured["regenerate_cmd"] = regenerate_cmd
        captured["role_name"] = role_name
        return compose.REPO_ROOT / "_fake_pm"

    monkeypatch.setattr(compose, "deploy_role", fake_deploy_role)
    monkeypatch.setattr(
        compose._config_module, "parse_aliases_registry",
        lambda: {"pm": ("pm", None), "frontend-1": ("worker", "frontend")},
    )

    compose.deploy_alias_v2("frontend-1")
    assert captured["regenerate_cmd"] == "frontend-1 --v2"
    assert captured["role_name"] == "worker"


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
