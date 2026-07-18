"""#13575 — comprehension-spec staleness gate.

``tests/comprehension/*_spec.json`` are permanent PASS-stamped records of a
fresh-agent comprehension check against LLM-consumed fragments at authoring
time. A later commit to a named fragment can silently overrule a spec's
recorded expectations (live case: #13569's Case E defer fix overruled
``13175_spec.json``'s honor-on-reach answer — now ``superseded_by: 13569``).

Design (see ``references/scripts/comprehension_staleness.py``): a checked-in
baseline maps each spec to the blob sha of every fragment it names, as of the
last review of that pair. This gate fails when a fragment's HEAD blob drifts
from the baseline (fragment changed, nobody re-reviewed the dependent specs)
or when a fragment-naming spec is missing from the baseline entirely.

Remediation is part of the fragment-changing PR: re-review each flagged spec,
then either ``comprehension_staleness.py refresh <spec>`` (still valid) or add
``"superseded_by": <issue>`` to the spec (overruled — permanent, kept as
historical record). The baseline was initialized 2026-07-18: pairs existing
then were grandfathered at their current shas WITHOUT retroactive re-review
(recorded in the baseline's ``_note``).
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "references" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import comprehension_staleness as cs  # noqa: E402


def test_baseline_file_exists():
    assert cs.BASELINE.is_file(), (
        "tests/comprehension/.staleness-baseline.json missing — the #13575 "
        "gate cannot run; regenerate via comprehension_staleness.py refresh --all")


def test_no_silently_stale_comprehension_specs():
    violations = cs.check()
    assert not violations, (
        "Fragment(s) changed since their comprehension spec(s) were last "
        "reviewed (#13575). In THIS PR: re-review each pair, then run "
        "'python references/scripts/comprehension_staleness.py refresh "
        "<spec>' if the spec still holds, or add 'superseded_by: <issue>' "
        "to the spec if the change overrules it. Pairs:\n  "
        + "\n  ".join(violations))


def test_fragment_extraction_handles_all_spec_shapes():
    """Every field shape in the live corpus (files list / target prose /
    source_file string / brace-set) yields paths; specs naming nothing are
    skipped, not crashed on."""
    frags = cs.spec_fragment_paths({
        "files": ["references/sub-skills/common/l4-curation.md"],
        "target": "references/roles/SOUL.md -> some section (PR #1)",
        "source_file": "references/scripts/tracker.py",
    })
    assert "references/sub-skills/common/l4-curation.md" in frags
    assert "references/roles/SOUL.md" in frags
    assert "references/scripts/tracker.py" in frags
    # nonexistent paths are filtered (a renamed/retired fragment is a different
    # staleness class, out of #13575's scope) and no-field specs are skipped
    assert cs.spec_fragment_paths(
        {"source_file": "references/wizard/DOES-NOT-EXIST.md"}) == []
    assert cs.spec_fragment_paths({"issue": 1, "questions": []}) == []


def test_brace_expansion():
    assert cs._expand_braces("a/{x,y}/b.md") == ["a/x/b.md", "a/y/b.md"]
    assert cs._expand_braces("a/b.md") == ["a/b.md"]
    # Sonnet-review F2: multiple groups expand cartesian; whitespace stripped.
    assert cs._expand_braces("{a,b}/{x, y}.md") == [
        "a/x.md", "a/y.md", "b/x.md", "b/y.md"]


def test_committed_blob_sha_survives_git_absence(monkeypatch):
    # Sonnet-review F1: a hung/absent git degrades to None (skip), never a
    # crash/hang of the fleet-wide static gate.
    import subprocess as sp

    def boom(*a, **kw):
        raise FileNotFoundError("git not on PATH")

    monkeypatch.setattr(cs.subprocess, "run", boom)
    assert cs.committed_blob_sha("references/roles/SOUL.md") is None


def test_refresh_prunes_deleted_specs_and_keeps_note(tmp_path, monkeypatch):
    # Sonnet-review F3: refresh prunes entries for deleted specs but the _note
    # metadata key must always survive.
    baseline_file = tmp_path / ".staleness-baseline.json"
    baseline_file.write_text(json.dumps({
        "_note": "keep me",
        "gone_spec.json": {"references/roles/SOUL.md": "0" * 40},
        "live_spec.json": {"references/roles/SOUL.md": "0" * 40},
    }), encoding="utf-8")
    monkeypatch.setattr(cs, "BASELINE", baseline_file)
    monkeypatch.setattr(cs, "load_specs", lambda: {
        "live_spec.json": {"files": ["references/roles/SOUL.md"]}})
    monkeypatch.setattr(cs, "committed_blob_sha", lambda p: "1" * 40)
    cs.refresh(["live_spec.json"])
    after = json.loads(baseline_file.read_text(encoding="utf-8"))
    assert after["_note"] == "keep me"
    assert "gone_spec.json" not in after
    assert after["live_spec.json"] == {"references/roles/SOUL.md": "1" * 40}


def test_superseded_specs_are_ignored(monkeypatch):
    monkeypatch.setattr(cs, "load_specs", lambda: {
        "1_spec.json": {"superseded_by": 99,
                        "files": ["references/roles/SOUL.md"]}})
    monkeypatch.setattr(cs, "load_baseline", lambda: {})
    assert cs.check() == []


def test_missing_baseline_entry_is_a_violation(monkeypatch):
    monkeypatch.setattr(cs, "load_specs", lambda: {
        "2_spec.json": {"files": ["references/roles/SOUL.md"]}})
    monkeypatch.setattr(cs, "load_baseline", lambda: {})
    v = cs.check()
    assert len(v) == 1 and "not in baseline" in v[0]


def test_sha_drift_is_a_violation(monkeypatch):
    monkeypatch.setattr(cs, "load_specs", lambda: {
        "3_spec.json": {"files": ["references/roles/SOUL.md"]}})
    monkeypatch.setattr(cs, "load_baseline", lambda: {
        "3_spec.json": {"references/roles/SOUL.md": "0" * 40}})
    monkeypatch.setattr(cs, "committed_blob_sha", lambda p: "1" * 40)
    v = cs.check()
    assert len(v) == 1 and "changed since last review" in v[0]


def test_matching_sha_is_clean(monkeypatch):
    monkeypatch.setattr(cs, "load_specs", lambda: {
        "4_spec.json": {"files": ["references/roles/SOUL.md"]}})
    monkeypatch.setattr(cs, "load_baseline", lambda: {
        "4_spec.json": {"references/roles/SOUL.md": "1" * 40}})
    monkeypatch.setattr(cs, "committed_blob_sha", lambda p: "1" * 40)
    assert cs.check() == []
