"""#14171 — composed agent CLAUDE.md files are pinned to their compose sources.

A deploy recompose rewrites ``.squidsquad/<alias>/CLAUDE.md`` with no owning
PR. Pairing a spec to that generated blob turned the #13575 staleness gate red
for every in-flight PR after each deploy (#14135, then #14171). The gate now
resolves a composed output to the L1-L3 sources compose inlines into it, so a
recompose alone never drifts the baseline and a source change still does, on
the PR that makes it.
"""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "references" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import comprehension_staleness as cs  # noqa: E402
import config  # noqa: E402
import v2_link_stage  # noqa: E402

PM_OUT = ".squidsquad/pm/CLAUDE.md"


def test_every_live_alias_resolves_to_existing_sources():
    for alias in config.parse_aliases_registry():
        srcs = cs.composed_output_sources(f".squidsquad/{alias}/CLAUDE.md")
        assert srcs, f"{alias}: composed CLAUDE.md resolved to no sources"
        for s in srcs:
            assert (REPO_ROOT / s).is_file(), s
            assert s.startswith("references/"), s
            # L4 is main-only state-lane content (#11511): never pinned.
            assert not s.startswith(".squidsquad/"), s
    pm = cs.composed_output_sources(PM_OUT)
    assert "references/roles/instructions.md" in pm
    assert "references/roles/pm/instructions.md" in pm


def test_non_composed_and_unknown_paths_return_none():
    assert cs.composed_output_sources("references/roles/SOUL.md") is None
    assert cs.composed_output_sources(".squidsquad/pm/SOUL.md") is None
    assert cs.composed_output_sources(".squidsquad/pm/planning/CLAUDE.md") is None
    assert cs.composed_output_sources(".squidsquad/no-such-alias/CLAUDE.md") is None


def test_include_directives_are_followed_except_runtime_read(monkeypatch):
    body = ("{{include: common/agent-lifecycle}}\n"
            "{{include: common-events/event-mode-contract}}\n"
            "{{include: common/does-not-exist}}\n")
    monkeypatch.setattr(v2_link_stage, "collect_sources_for_validation",
                        lambda *a, **kw: [SimpleNamespace(
                            path="references/roles/pm/instructions.md",
                            body=body)])
    assert cs.composed_output_sources(PM_OUT) == [
        "references/roles/pm/instructions.md",
        "references/sub-skills/common/agent-lifecycle.md",
    ]


def test_resolution_failure_falls_back_to_the_composed_blob(monkeypatch):
    def boom(*a, **kw):
        raise RuntimeError("registry unreadable")

    monkeypatch.setattr(config, "parse_aliases_registry", boom)
    assert cs.composed_output_sources(PM_OUT) is None
    assert cs.tracked_paths({"files": [PM_OUT]}) == [(PM_OUT, None)]


def test_tracked_paths_expand_dedupe_and_tag_provenance(monkeypatch):
    monkeypatch.setattr(cs, "composed_output_sources", lambda p: {
        ".squidsquad/pm/CLAUDE.md": ["references/roles/SOUL.md",
                                     "references/roles/pm/SOUL.md"],
        ".squidsquad/qa/CLAUDE.md": ["references/roles/SOUL.md",
                                     "references/roles/verifier/SOUL.md"],
    }.get(p))
    got = cs.tracked_paths({"files": [
        "references/roles/SOUL.md", ".squidsquad/pm/CLAUDE.md",
        ".squidsquad/qa/CLAUDE.md"]})
    assert got == [
        ("references/roles/SOUL.md", None),
        ("references/roles/pm/SOUL.md", ".squidsquad/pm/CLAUDE.md"),
        ("references/roles/verifier/SOUL.md", ".squidsquad/qa/CLAUDE.md"),
    ]


def _one_spec(monkeypatch, baseline_sha, live):
    monkeypatch.setattr(cs, "load_specs", lambda: {
        "5_spec.json": {"files": [PM_OUT]}})
    monkeypatch.setattr(cs, "composed_output_sources",
                        lambda p: ["references/roles/pm/SOUL.md"]
                        if p == PM_OUT else None)
    monkeypatch.setattr(cs, "load_baseline", lambda: {
        "5_spec.json": {"references/roles/pm/SOUL.md": baseline_sha}})
    monkeypatch.setattr(cs, "committed_blob_sha", lambda p: live[p])


def test_recompose_alone_does_not_drift(monkeypatch):
    # The #14171 repro: the composed blob moved, its sources did not.
    _one_spec(monkeypatch, "1" * 40, {
        PM_OUT: "9" * 40, "references/roles/pm/SOUL.md": "1" * 40})
    assert cs.check() == []


def test_source_change_flags_spec_naming_composed_output(monkeypatch):
    _one_spec(monkeypatch, "1" * 40, {
        PM_OUT: "1" * 40, "references/roles/pm/SOUL.md": "2" * 40})
    v = cs.check()
    assert len(v) == 1
    assert "references/roles/pm/SOUL.md (composed into .squidsquad/pm/CLAUDE.md)" in v[0]


def test_dropped_source_is_flagged(monkeypatch):
    # DS review F1: a source deleted (or no longer composed in) leaves the
    # tracked set; its baseline key must not be silently ignored.
    _one_spec(monkeypatch, "1" * 40, {
        PM_OUT: "1" * 40, "references/roles/pm/SOUL.md": "1" * 40})
    monkeypatch.setattr(cs, "load_baseline", lambda: {"5_spec.json": {
        "references/roles/pm/SOUL.md": "1" * 40,
        "references/roles/pm/retired.md": "3" * 40}})
    v = cs.check()
    assert v == ["5_spec.json <- references/roles/pm/retired.md no longer "
                 "tracked (deleted, or no longer composed in) since last review"]


def test_dropped_key_check_is_scoped_to_composed_specs(monkeypatch):
    # Specs naming no composed output keep the pre-#14171 scope: a retired
    # explicit fragment is a different staleness class.
    monkeypatch.setattr(cs, "load_specs", lambda: {
        "6_spec.json": {"files": ["references/roles/SOUL.md"]}})
    monkeypatch.setattr(cs, "load_baseline", lambda: {"6_spec.json": {
        "references/roles/SOUL.md": "1" * 40,
        "references/roles/retired.md": "3" * 40}})
    monkeypatch.setattr(cs, "committed_blob_sha", lambda p: "1" * 40)
    assert cs.check() == []


def test_alias_grammar_matches_compose():
    # DS review F2: every alias compose.deploy_alias_v2 accepts is recognized.
    import compose
    assert compose._V2_ALIAS_RE.pattern == r"^[A-Za-z0-9][A-Za-z0-9_.-]*$"
    for alias in ("pm", "worker.fe", "web-2", "a_b"):
        assert cs._COMPOSED_OUTPUT_RE.match(f".squidsquad/{alias}/CLAUDE.md")
    assert not cs._COMPOSED_OUTPUT_RE.match(".squidsquad/.hidden/CLAUDE.md")


def test_resolution_failure_against_source_keyed_entry_says_so(monkeypatch):
    # DS review F3: the fallback must not report a fake sha drift against a
    # baseline that is keyed on sources.
    monkeypatch.setattr(cs, "load_specs", lambda: {
        "7_spec.json": {"files": [PM_OUT]}})
    monkeypatch.setattr(cs, "composed_output_sources", lambda p: None)
    monkeypatch.setattr(cs, "load_baseline", lambda: {"7_spec.json": {
        "references/roles/pm/SOUL.md": "1" * 40}})
    monkeypatch.setattr(cs, "committed_blob_sha", lambda p: "1" * 40)
    v = cs.check()
    assert len(v) == 1
    assert "cannot resolve its compose sources" in v[0]
    assert "changed since last review" not in v[0]


def test_resolution_failure_against_blob_keyed_entry_compares_blob(monkeypatch):
    monkeypatch.setattr(cs, "load_specs", lambda: {
        "8_spec.json": {"files": [PM_OUT]}})
    monkeypatch.setattr(cs, "composed_output_sources", lambda p: None)
    monkeypatch.setattr(cs, "load_baseline", lambda: {"8_spec.json": {
        PM_OUT: "1" * 40}})
    monkeypatch.setattr(cs, "committed_blob_sha", lambda p: "1" * 40)
    assert cs.check() == []


def test_live_baseline_pins_no_composed_output():
    baseline = json.loads(cs.BASELINE.read_text(encoding="utf-8"))
    for spec, entry in baseline.items():
        if spec.startswith("_"):
            continue
        for path in entry:
            if cs._COMPOSED_OUTPUT_RE.match(path):
                assert cs.composed_output_sources(path) is None, (
                    f"{spec} pins generated {path}; refresh it so it keys "
                    f"on the compose sources (#14171)")
