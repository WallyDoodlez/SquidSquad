"""#13860 S4.4 -- engine-rerouted dedup, prefer-update-over-create.

Pins VAULT-ARCH 7.2's merge-target test (amended by #14123): a hit becomes the
merge target only if it is a DIRECT filename/wikilink/tag-tier hit, `status:
active`, and Jaccard(slug+title+tags) >= dedupThreshold (default 0.5). The
Stage-2 score is never the signal. The probe is one --no-write search.
"""

import json
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "references" / "scripts"))

import vault_consume as vc  # noqa: E402

SEED = REPO / "references" / "vault-schema-default.json"
NODE = shutil.which("node")


@pytest.fixture(autouse=True)
def _engine_from_source(monkeypatch):
    """Exercise the COMMITTED engine (references/), never a possibly-stale
    per-clone .claude/ install copy."""
    monkeypatch.setattr(vc, "ENGINE_DIRS", (REPO / "references" / "skills" / "vault-search" / "scripts",))
needs_node = pytest.mark.skipif(NODE is None, reason="node unavailable")

DRAFT = vc.tokens("decision-branch-per-feature", "Branch per feature", ["git", "branches"])


def hit(slug, title, tags, tier="filename", status="active", direct=True, score=0.0):
    return {"slug": slug, "path": f"galaxy/{slug}.md", "title": title, "tags": tags,
            "tier": tier, "status": status, "direct": direct, "score": score}


class TestSelectMergeTarget:
    GOOD = hit("decision-branch-per-feature", "Branch per feature", ["git", "branches"])

    def test_qualifying_direct_hit_selected(self):
        target, _ = vc.select_merge_target(DRAFT, {"results": [self.GOOD]}, 0.5)
        assert target["slug"] == "decision-branch-per-feature" and target["similarity"] == 1.0

    def test_unrelated_fresh_note_not_selected(self):
        """A brand-new unrelated note (recency-only Stage-2 ~0.25) never wins:
        the score is ignored, similarity decides."""
        fresh = hit("learning-telemetry-shards", "Telemetry shards", ["telemetry"], score=0.25)
        target, cands = vc.select_merge_target(DRAFT, {"results": [fresh]}, 0.5)
        assert target is None and cands == []

    def test_content_tier_never_qualifies(self):
        content = dict(self.GOOD, tier="content")
        assert vc.select_merge_target(DRAFT, {"results": [content]}, 0.5)[0] is None

    @pytest.mark.parametrize("status", ["archived", "superseded", ""])
    def test_retired_note_never_qualifies_even_at_jaccard_1(self, status):
        retired = dict(self.GOOD, status=status)
        assert vc.select_merge_target(DRAFT, {"results": [retired]}, 0.5)[0] is None

    def test_traversal_reached_never_qualifies(self):
        payload = {"results": [], "traversed": [dict(self.GOOD, tier="walked", direct=False)]}
        assert vc.select_merge_target(DRAFT, payload, 0.5)[0] is None
        # and a direct:false entry that leaked into results is still refused
        assert vc.select_merge_target(DRAFT, {"results": [dict(self.GOOD, direct=False)]}, 0.5)[0] is None

    def test_missing_direct_flag_fails_closed(self):
        # Only an explicit direct: true qualifies; an absent flag is not a direct hit.
        no_flag = {k: v for k, v in self.GOOD.items() if k != "direct"}
        assert vc.select_merge_target(DRAFT, {"results": [no_flag]}, 0.5)[0] is None

    @pytest.mark.parametrize("tier", ["filename", "wikilink", "tag"])
    def test_each_strong_tier_qualifies(self, tier):
        assert vc.select_merge_target(DRAFT, {"results": [dict(self.GOOD, tier=tier)]}, 0.5)[0]

    def test_below_threshold_not_selected(self):
        partial = hit("decision-branch-naming", "Branch naming", ["git"])
        sim = vc.jaccard(DRAFT, vc.tokens(partial["slug"], partial["title"], partial["tags"]))
        assert sim < 0.5
        assert vc.select_merge_target(DRAFT, {"results": [partial]}, 0.5)[0] is None
        assert vc.select_merge_target(DRAFT, {"results": [partial]}, sim)[0]["slug"] == "decision-branch-naming"

    def test_highest_similarity_wins_over_tier_and_score(self):
        weaker = hit("decision-branch-per-feature-flow", "Branch per feature flow", ["git"],
                     tier="filename", score=9.0)
        stronger = dict(self.GOOD, tier="tag", score=0.0)
        target, cands = vc.select_merge_target(DRAFT, {"results": [weaker, stronger]}, 0.5)
        assert target["slug"] == "decision-branch-per-feature"
        assert [c["slug"] for c in cands] == ["decision-branch-per-feature", "decision-branch-per-feature-flow"]

    def test_ties_break_by_tier_then_score(self):
        a = dict(self.GOOD, slug="decision-branch-per-feature", tier="tag", score=5.0)
        b = dict(self.GOOD, slug="decision-branch-per-feature", tier="filename", score=0.0)
        assert vc.select_merge_target(DRAFT, {"results": [a, b]}, 0.5)[0]["tier"] == "filename"
        c = dict(self.GOOD, score=1.0)
        d = dict(self.GOOD, score=3.0)
        assert vc.select_merge_target(DRAFT, {"results": [c, d]}, 0.5)[0]["score"] == 3.0


class TestThresholdConfig:
    def test_shipped_default(self):
        assert json.loads(SEED.read_text(encoding="utf-8"))["dedupThreshold"] == 0.5

    def test_absent_schema_uses_default(self, tmp_path):
        assert vc.dedup_threshold(tmp_path) == 0.5

    def test_override_honored(self, tmp_path):
        (tmp_path / "vault-schema.json").write_text(json.dumps({"dedupThreshold": 0.8}), encoding="utf-8")
        assert vc.dedup_threshold(tmp_path) == 0.8

    @pytest.mark.parametrize("bad", ["x", 1.5, -0.1, None])
    def test_invalid_override_falls_back(self, tmp_path, bad):
        (tmp_path / "vault-schema.json").write_text(json.dumps({"dedupThreshold": bad}), encoding="utf-8")
        assert vc.dedup_threshold(tmp_path) == 0.5

    def test_override_changes_the_decision(self):
        partial = hit("decision-branch-naming", "Branch naming", ["git"])
        assert vc.select_merge_target(DRAFT, {"results": [partial]}, 0.5)[0] is None
        assert vc.select_merge_target(DRAFT, {"results": [partial]}, 0.2)[0] is not None


class TestProbeShape:
    def test_single_no_write_search(self):
        calls = []

        def fake_search(alias, task, entities=(), tags=(), terms=(), write=True, vault=None):
            calls.append({"task": task, "entities": entities, "tags": tags, "terms": terms, "write": write})
            return {"results": [], "traversed": []}, None

        res, reason = vc.dedup("skill", "Use a merge-target test", ["vault"], search_fn=fake_search)
        assert reason is None and res["action"] == "create"
        assert len(calls) == 1 and calls[0]["write"] is False and calls[0]["task"] is None
        assert "a" not in calls[0]["entities"]  # 1-2 char words would match every slug
        assert calls[0]["terms"] == ["Use a merge-target test"]

    def test_engine_unavailable_passes_through(self):
        res, reason = vc.dedup("skill", "x", search_fn=lambda *a, **k: (None, "node not installed"))
        assert res is None and reason == "node not installed"


def note(vault, slug, title, tags, status="active", body=""):
    (vault / "galaxy").mkdir(parents=True, exist_ok=True)
    (vault / "galaxy" / f"{slug}.md").write_text(textwrap.dedent(f"""\
        ---
        type: {slug.split('-')[0]}
        tags: [{', '.join(tags)}]
        created: 2026-09-01
        updated: 2026-09-01
        owner: worker
        status: {status}
        ---
        # {title}
        {body}
        """), encoding="utf-8")


@needs_node
class TestEndToEnd:
    @pytest.fixture
    def vault(self, tmp_path):
        v = tmp_path / "vault"
        v.mkdir()
        shutil.copy(SEED, v / "vault-schema.json")
        note(v, "decision-branch-per-feature", "Branch per feature", ["git", "branches"])
        note(v, "decision-old-branching", "Branch per feature", ["git", "branches"], status="superseded")
        note(v, "learning-shard-merge", "Shard merge union", ["telemetry"],
             body="branch per feature is mentioned in passing here")
        return v

    def test_duplicate_subject_lands_as_update(self, vault):
        res, reason = vc.dedup("skill", "Branch per feature", ["git", "branches"],
                               slug="decision-branch-per-feature-2", vault=vault)
        assert reason is None
        assert res["action"] == "update"
        assert res["target"]["slug"] == "decision-branch-per-feature"
        assert "decision-old-branching" not in [c["slug"] for c in res["candidates"]]

    def test_unrelated_subject_lands_as_create(self, vault):
        res, _ = vc.dedup("skill", "Compose placeholder substitution", ["compose"], vault=vault)
        assert res["action"] == "create" and res["target"] is None

    def test_engine_output_carries_selector_fields(self, vault):
        payload, _ = vc.search("skill", None, entities=["branch"], write=False, vault=vault)
        for r in payload["results"]:
            assert {"slug", "title", "tags", "status", "direct", "tier"} <= set(r)

    def test_probe_writes_zero_telemetry(self, vault):
        vc.dedup("skill", "Branch per feature", ["git"], vault=vault)
        shards = list((vault / ".telemetry").glob("*.jsonl")) if (vault / ".telemetry").exists() else []
        assert sum(len(s.read_text(encoding="utf-8").splitlines()) for s in shards) == 0

    def test_cli(self, vault, monkeypatch, capsys):
        monkeypatch.setattr(vc, "VAULT_DIR", vault)
        assert vc.main(["dedup", "--alias", "skill", "--title", "Branch per feature",
                        "--tags", "git,branches"]) == 0
        assert json.loads(capsys.readouterr().out)["target"]["slug"] == "decision-branch-per-feature"
