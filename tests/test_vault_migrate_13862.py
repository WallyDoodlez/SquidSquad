"""#13862 -- vault v1 -> v2 migration tool (VAULT-ARCH 10): M0 inventory, M1
mechanical transform, M3 manifest apply + reconcile.

Everything runs on tmp_path vaults (the rehearsal model) -- never the live
.squidsquad/vault. `_git_created` is stubbed so no test depends on history.
"""

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "references" / "scripts"))

import vault_migrate as vm  # noqa: E402

TODAY = "2026-09-26"


def w(vault, rel, text):
    p = vault / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="")
    return p


V1_NOTE = """---
name: decision-a
description: summary line
metadata:
  type: decision
type: decision
tags: [harness, posture]
created: 2026-01-01
owner: skill-lead
status: active      # active | superseded | archived
confidence: high
source: conversation
links: [learning-b]
---

# A

See [[style-voice]] and [[learning-b|B]].
"""


@pytest.fixture
def vault(tmp_path, monkeypatch):
    monkeypatch.setattr(vm, "_git_created", lambda rel: "2026-02-02")
    v = tmp_path / "vault"
    w(v, "galaxy/decision-a.md", V1_NOTE)
    w(v, "galaxy/learning-b.md", "---\ntype: learning\ntags: [x]\ncreated: 2026-01-03\n"
      "updated: 2026-01-04\nstatus: active\nowner: qa\n---\n\n# B\n\n## Changelog\n\n"
      "- **2026-01-04** — created.\n\n## Other\n\ntext\n")
    w(v, "galaxy/style-voice.md", "---\ntype: style\ntags: [comms]\ncreated: 2026-01-05\n"
      "status: active\nowner: pm\n---\n\n# Voice\n")
    w(v, "galaxy/learning-nometa.md", "---\nauthor: dm-lead\n---\n\n# no meta\n")
    w(v, "archives/old.md", "---\ntags: [legacy]\ncreated: 2025-01-01\n---\n\n# old\n")
    w(v, "BRIEFING.md", "# Briefing\n\nsee [[project_marketplace]]\n")
    (v / ".relevance-index.json").write_text("{}", encoding="utf-8")
    return v


def fm(path):
    parsed = vm._split(path.read_text(encoding="utf-8"))
    return {k: vm._value(ls) for k, ls in parsed[0] if k}, parsed[1]


class TestInventory:
    def test_counts_and_distributions(self, vault):
        inv = vm.inventory(vault)
        assert inv["count"] == 5  # BRIEFING excluded
        assert set(inv["notes"]) == {"decision-a", "learning-b", "style-voice",
                                     "learning-nometa", "old"}
        assert inv["distributions"]["owner"]["skill-lead"] == 1


class TestTransform:
    def test_frontmatter_rules(self, vault):
        vm.transform(vault, today=TODAY, repo_root=vault)
        a, body = fm(vault / "galaxy/decision-a.md")
        for gone in ("confidence", "source", "links", "name", "metadata"):
            assert gone not in a
        assert a["owner"] == "worker" and a["status"] == "active"
        assert a["updated"] == "2026-01-01"  # filled from created
        assert a["tags"] == "[harness]"  # posture dropped
        assert a["community"] == "" and a["last_optimized"] == ""
        assert a["description"] == "summary line"  # non-schema content kept for M2
        raw = (vault / "galaxy/decision-a.md").read_text(encoding="utf-8")
        assert raw.index("type:") < raw.index("owner:") < raw.index("community:") \
            < raw.index("description:")
        assert f"- **{TODAY}** — migrated to vault v2 (#13862)." in body

    def test_owner_and_fills(self, vault):
        vm.transform(vault, today=TODAY, repo_root=vault)
        assert fm(vault / "galaxy/learning-b.md")[0]["owner"] == "verifier"
        n = fm(vault / "galaxy/learning-nometa.md")[0]
        assert n["type"] == "learning" and n["owner"] == "dm" and n["status"] == "active"
        assert n["created"] == "2026-02-02"  # first git commit (stubbed)
        old = fm(vault / "archives/old.md")[0]
        assert old["type"] == "archive" and old["status"] == "archived"

    def test_changelog_appended_inside_existing_section(self, vault):
        vm.transform(vault, today=TODAY, repo_root=vault)
        body = fm(vault / "galaxy/learning-b.md")[1]
        cl = body.index("## Changelog")
        assert cl < body.index("migrated to vault v2") < body.index("## Other")

    def test_style_folds_into_pattern_with_link_rewrite(self, vault):
        out = vm.transform(vault, today=TODAY, repo_root=vault)
        assert out["redirects"] == {"style-voice": "pattern-voice"}
        assert not (vault / "galaxy/style-voice.md").exists()
        assert fm(vault / "galaxy/pattern-voice.md")[0]["type"] == "pattern"
        body = fm(vault / "galaxy/decision-a.md")[1]
        assert "[[pattern-voice]]" in body and "[[learning-b|B]]" in body

    def test_external_references_flagged_not_rewritten(self, vault, tmp_path):
        repo = tmp_path / "repo"
        doc = w(repo, "docs/x.md", "mentions style-voice here\n")
        out = vm.transform(vault, today=TODAY, repo_root=repo)
        assert out["external_references"] == [{"file": "docs/x.md", "slug": "style-voice"}]
        assert doc.read_text(encoding="utf-8") == "mentions style-voice here\n"

    def test_relevance_index_removed(self, vault):
        assert vm.transform(vault, today=TODAY, repo_root=vault)["relevance_index_removed"]
        assert not (vault / ".relevance-index.json").exists()

    def test_idempotent(self, vault):
        vm.transform(vault, today=TODAY, repo_root=vault)
        snap = {p: p.read_bytes() for p in vault.rglob("*.md")}
        again = vm.transform(vault, today="2026-12-31", repo_root=vault)
        assert again["changed"] == 0
        assert {p: p.read_bytes() for p in vault.rglob("*.md")} == snap

    def test_dry_run_writes_nothing(self, vault):
        snap = {p: p.read_bytes() for p in vault.rglob("*")if p.is_file()}
        out = vm.transform(vault, dry_run=True, today=TODAY, repo_root=vault)
        assert out["changed"] == 5 and out["redirects"]
        assert {p: p.read_bytes() for p in vault.rglob("*") if p.is_file()} == snap

    def test_crlf_note_stays_crlf(self, vault):
        p = vault / "galaxy/learning-b.md"
        p.write_bytes(p.read_bytes().replace(b"\n", b"\r\n"))
        vm.transform(vault, today=TODAY, repo_root=vault)
        raw = p.read_bytes()
        assert raw.count(b"\n") == raw.count(b"\r\n")

    def test_flags_untaggable_and_unknown_owner(self, vault):
        w(vault, "galaxy/learning-c.md", "---\ntype: learning\ncreated: 2026-01-01\n"
          "owner: mystery\nstatus: active\n---\n\n# c\n")
        out = vm.transform(vault, dry_run=True, today=TODAY, repo_root=vault)
        assert any("no tags" in f for f in out["flags"]["learning-c"])
        assert any("unknown owner" in f for f in out["flags"]["learning-c"])

    def test_no_frontmatter_left_untouched(self, vault):
        p = w(vault, "resources/raw.md", "# raw\n")
        vm.transform(vault, today=TODAY, repo_root=vault)
        assert p.read_text(encoding="utf-8") == "# raw\n"

    def test_cli_dry_run(self, vault, capsys):
        assert vm.main(["transform", "--vault", str(vault), "--dry-run"]) == 0
        assert json.loads(capsys.readouterr().out)["dry_run"] is True
        assert vm.main(["bogus"]) == 2


def manifest_file(tmp_path, data, drafts=None):
    d = tmp_path / "m2"
    d.mkdir(exist_ok=True)
    for name, text in (drafts or {}).items():
        (d / name).write_text(text, encoding="utf-8")
    p = d / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


class TestApplyManifest:
    def base(self, vault):
        vm.transform(vault, today=TODAY, repo_root=vault)
        return {"redirects": {"style-voice": "pattern-voice"}, "notes": {
            "decision-a": {"disposition": "keep", "hubs": ["harness"]},
            "learning-b": {"disposition": "merge-into", "target": "decision-a"},
            "pattern-voice": {"disposition": "keep"},
            "learning-nometa": {"disposition": "prune", "reason": "one-off incident"},
            "old": {"disposition": "keep"}},
            "new_hubs": {"harness": "harness.md"},
            "merged_drafts": {"decision-a": "a.md"},
            "link_fixes": {"BRIEFING": {"project_marketplace": None},
                           "decision-a": {"learning-b": "decision-a"}},
            "add_tags": {"learning-nometa": ["merge", "gotcha"]}}

    def test_apply_all_actions(self, vault, tmp_path):
        m = manifest_file(tmp_path, self.base(vault), {
            "harness.md": "---\ntype: system\ntags: [harness]\ncreated: 2026-09-26\n"
                          "updated: 2026-09-26\nstatus: active\nowner: shared\n---\n\n# Harness\n",
            "a.md": "\n# A (merged)\n\nSee [[learning-b|B]] and [[pattern-voice]].\n"})
        out = vm.apply_manifest(m, vault, today=TODAY)
        assert out["applied"], out
        assert (vault / "systems/harness.md").exists()
        b_fm, b_body = fm(vault / "galaxy/learning-b.md")
        assert b_fm["status"] == "superseded" and "superseded by [[decision-a]]" in b_body
        n_fm, n_body = fm(vault / "galaxy/learning-nometa.md")
        assert n_fm["status"] == "archived" and "one-off incident" in n_body
        assert n_fm["tags"] == "[merge, gotcha]"
        a_fm, a_body = fm(vault / "galaxy/decision-a.md")
        assert "# A (merged)" in a_body and a_fm["updated"] == TODAY
        assert "[[decision-a|B]]" in a_body  # link fix applied after the draft
        assert "- [[harness]]" in a_body  # hub link survives the merged draft
        assert (vault / "BRIEFING.md").read_text(encoding="utf-8").endswith("see project_marketplace\n")
        assert all(p.exists() for p in (vault / "galaxy").iterdir()), "nothing deleted"

    def test_keep_adds_hub_link(self, vault, tmp_path):
        data = self.base(vault)
        data.pop("merged_drafts")
        m = manifest_file(tmp_path, data, {"harness.md": "---\ntype: system\n---\n# H\n"})
        vm.apply_manifest(m, vault, today=TODAY)
        body = fm(vault / "galaxy/decision-a.md")[1]
        assert "## Related" in body and "- [[harness]]" in body
        assert body.index("## Related") < body.index("## Changelog")

    @pytest.mark.parametrize("mutate,problem", [
        (lambda d: d["notes"]["learning-b"].update(target="ghost"), "does not exist"),
        (lambda d: d["notes"]["learning-b"].update(target="learning-nometa"), "itself retired"),
        (lambda d: d["notes"]["decision-a"].update(disposition="delete"), "bad disposition"),
        (lambda d: d["link_fixes"]["decision-a"].update(x="nowhere"), "does not exist"),
    ])
    def test_invalid_manifest_refused_whole(self, vault, tmp_path, mutate, problem):
        data = self.base(vault)
        mutate(data)
        snap = {p: p.read_bytes() for p in vault.rglob("*.md")}
        out = vm.apply_manifest(manifest_file(tmp_path, data), vault, today=TODAY)
        assert out["applied"] is False and any(problem in x for x in out["problems"])
        assert {p: p.read_bytes() for p in vault.rglob("*.md")} == snap

    def test_link_fix_reaches_frontmatter(self, vault, tmp_path):
        vm.transform(vault, today=TODAY, repo_root=vault)
        p = vault / "galaxy/learning-b.md"
        p.write_text(p.read_text(encoding="utf-8").replace(
            "owner: verifier", "owner: verifier\ndescription: see [[gone]]"), encoding="utf-8")
        data = {"notes": {}, "link_fixes": {"learning-b": {"gone": None}}}
        assert vm.apply_manifest(manifest_file(tmp_path, data), vault, today=TODAY)["applied"]
        assert "description: see gone" in p.read_text(encoding="utf-8")

    def test_link_fix_keys_match_vault_check(self):
        body = "a [[#13030]] b [[x|X]] c [[y#h]] d [[keep]]"
        out = vm._fix_links(body, {"#13030": None, "x": None, "y#h": "z"})
        assert out == "a #13030 b X c [[z]] d [[keep]]"

    def test_dry_run(self, vault, tmp_path):
        data = self.base(vault)
        m = manifest_file(tmp_path, data, {"harness.md": "---\ntype: system\n---\n# H\n",
                                           "a.md": "# A2\n"})
        snap = {p: p.read_bytes() for p in vault.rglob("*.md")}
        out = vm.apply_manifest(m, vault, dry_run=True, today=TODAY)
        assert out["dry_run"] and out["actions"]
        assert {p: p.read_bytes() for p in vault.rglob("*.md")} == snap


class TestReconcile:
    def test_counts_follow_redirects_and_flag_missing(self, vault, tmp_path):
        inv = tmp_path / "inv.json"
        inv.write_text(json.dumps(vm.inventory(vault)), encoding="utf-8")
        data = {"redirects": {"style-voice": "pattern-voice"}, "notes": {
            "decision-a": {"disposition": "keep"}, "learning-b": {"disposition": "prune"},
            "pattern-voice": {"disposition": "keep"},
            "learning-nometa": {"disposition": "merge-into", "target": "decision-a"}}}
        m = manifest_file(tmp_path, data)
        out = vm.reconcile(inv, m, vault, run_checks=False)
        assert out["undispositioned"] == ["old"] and out["reconciled"] is False
        data["notes"]["old"] = {"disposition": "keep"}
        m.write_text(json.dumps(data), encoding="utf-8")
        out = vm.reconcile(inv, m, vault, run_checks=False)
        assert out["reconciled"] and out["dispositions"] == {"keep": 3, "prune": 1,
                                                            "merge-into": 1}

    def test_vault_checks_target_the_given_vault(self, vault):
        res = vm.vault_checks(vault)
        assert "BRIEFING.md: broken link [[project_marketplace]]" in res["broken_links"]
        assert res["passed"] is False
        import vault_check
        assert vault_check.VAULT_DIR == REPO / ".squidsquad" / "vault", "global restored"
