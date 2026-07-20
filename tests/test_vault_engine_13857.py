"""#13857 -- vault consumption engine (P1): pinned behavior tests.

The engine is the portable reference-system extraction adapted to the
SquidSquad contracts (docs/VAULT-ARCH.md):

  - Section 6.2 search contract: tiered match (filename > wikilink > tag >
    content), budgeted galaxy traversal, two-stage ranking with status
    multiplier, top-K metadata-only JSON.
  - Section 6.1/6.3 telemetry: JSONL events appended to the caller's own
    per-writer shard; counters aggregated at read with dedup by event id;
    notes never carry counters.
  - Section 8.5 boundary: caller identity (instance-id + alias) required on
    every call; record writes `used` (consumers only); --no-write emits zero
    events (AC4's unit-level pin).
  - Section 9.9 degradation: corrupt shards are skipped, cold start ranks by
    tier + recency + weight.

These tests run the real engine via subprocess (node). If node is absent the
whole module skips -- that environment is the AC2 degraded path, exercised by
its own live verification, not by this unit suite.
"""

import json
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
# The committed source of truth (references/); installs materialize a copy to
# .claude/skills/ per clone (the repo's standard source -> live split, and the
# reason commit_code's .claude/ filter never sees the engine).
SKILL_SRC = REPO / "references" / "skills" / "vault-search"
QUERY = SKILL_SRC / "scripts" / "vault-query.mjs"
RECORD = SKILL_SRC / "scripts" / "record-consumption.mjs"

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(
    NODE is None, reason="node unavailable -- engine degrades per VAULT-ARCH 9.9 (AC2 live-verified separately)"
)

IDENTITY = ["--instance-id", "test-uuid", "--alias", "skill", "--task", "13857"]


def note(vault: Path, folder: str, slug: str, body: str) -> Path:
    d = vault / folder
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{slug}.md"
    p.write_text(textwrap.dedent(body), encoding="utf-8")
    return p


def make_vault(tmp_path: Path) -> Path:
    """Fixture vault: 2 direct 'auth' hits, a budget-blocked galaxy chain, a
    hub-reachable superseded note, and vault-root/scaffolding exclusions."""
    vault = tmp_path / "vault"
    note(
        vault,
        "galaxy",
        "decision-auth-flow",
        """\
        ---
        type: decision
        status: active
        updated: 2026-07-19
        tags: [auth, security]
        ---
        # Auth flow decision
        We chose OAuth. See [[hub-auth]] and [[learning-token-expiry]].
        """,
    )
    note(
        vault,
        "areas",
        "hub-auth",
        """\
        ---
        type: hub
        status: active
        updated: 2026-07-01
        tags: [auth]
        ---
        # Auth hub
        Links: [[decision-auth-flow]], [[learning-token-expiry]], [[pattern-retry]].
        """,
    )
    note(
        vault,
        "galaxy",
        "learning-token-expiry",
        """\
        ---
        type: learning
        status: active
        updated: 2026-06-15
        tags: [tokens]
        ---
        # Token expiry learning
        Tokens expire. [[pattern-retry]]
        """,
    )
    note(
        vault,
        "galaxy",
        "pattern-retry",
        """\
        ---
        type: pattern
        status: superseded
        updated: 2026-05-01
        tags: [retry]
        ---
        # Retry pattern
        Old retry pattern, superseded.
        """,
    )
    # Exclusions: BRIEFING at root, scaffolding files inside folders.
    (vault / "BRIEFING.md").write_text("# Briefing\nauth auth auth\n", encoding="utf-8")
    note(vault, "galaxy", "README", "# readme\nauth\n")
    note(vault, "galaxy", "INDEX", "# index\nauth\n")
    note(vault, "galaxy", "_template", "# template\nauth\n")
    return vault


def run_query(vault: Path, *args: str, identity=None, check=True):
    cmd = [NODE, str(QUERY), "--vault", str(vault), *(identity if identity is not None else IDENTITY), *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO))
    if check:
        assert proc.returncode == 0, proc.stderr
        return json.loads(proc.stdout)
    return proc


def run_record(vault: Path, *args: str, identity=None, check=True):
    cmd = [NODE, str(RECORD), "--vault", str(vault), *(identity if identity is not None else IDENTITY), *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO))
    if check:
        assert proc.returncode == 0, proc.stderr
        return json.loads(proc.stdout)
    return proc


def shard(vault: Path) -> Path:
    return vault / ".telemetry" / "test-uuid-skill.jsonl"


def read_events(vault: Path):
    return [json.loads(l) for l in shard(vault).read_text(encoding="utf-8").splitlines() if l.strip()]


# ---- arg contract (section 8.5 identity) ------------------------------------


class TestArgContract:
    def test_query_requires_identity(self, tmp_path):
        vault = make_vault(tmp_path)
        proc = run_query(vault, "--entities", "auth", identity=[], check=False)
        assert proc.returncode == 2
        assert "instance-id" in proc.stderr

    def test_query_requires_some_query(self, tmp_path):
        vault = make_vault(tmp_path)
        proc = run_query(vault, check=False)
        assert proc.returncode == 2

    def test_record_requires_task(self, tmp_path):
        vault = make_vault(tmp_path)
        proc = run_record(
            vault, "--slugs", "decision-auth-flow", identity=["--instance-id", "u", "--alias", "skill"], check=False
        )
        assert proc.returncode == 2
        assert "task" in proc.stderr

    def test_record_requires_slugs_and_identity(self, tmp_path):
        vault = make_vault(tmp_path)
        assert run_record(vault, identity=[], check=False).returncode == 2
        assert run_record(vault, "--task", "1", identity=IDENTITY, check=False).returncode == 2


# ---- search contract (section 6.2) ------------------------------------------


class TestSearch:
    def test_tier_order_and_exclusions(self, tmp_path):
        vault = make_vault(tmp_path)
        out = run_query(vault, "--entities", "auth", "--no-write")
        slugs = [r["slug"] for r in out["results"]]
        # Both filename hits, decision first (higher galaxy weight + recency).
        assert slugs == ["decision-auth-flow", "hub-auth"]
        assert all(r["tier"] == "filename" for r in out["results"])
        # BRIEFING.md and scaffolding files are never indexed.
        surfaced = {r["slug"] for r in out["results"] + out["traversed"]}
        assert not {"BRIEFING", "README", "INDEX", "_template"} & surfaced

    def test_tag_and_content_tiers(self, tmp_path):
        vault = make_vault(tmp_path)
        out = run_query(vault, "--tags", "tokens", "--terms", "OAuth", "--no-write")
        by_slug = {r["slug"]: r for r in out["results"]}
        assert by_slug["learning-token-expiry"]["tier"] == "tag"
        assert by_slug["decision-auth-flow"]["tier"] == "content"
        # tag tier outranks content tier in the ordering.
        slugs = [r["slug"] for r in out["results"]]
        assert slugs.index("learning-token-expiry") < slugs.index("decision-auth-flow")

    def test_traversal_budget_blocks_galaxy_chain(self, tmp_path):
        """decision(galaxy,1) -> learning(galaxy,2) -> pattern(galaxy,3) is
        over budget 2; pattern-retry is reachable only through the free hub."""
        vault = make_vault(tmp_path)
        out = run_query(vault, "--entities", "decision-auth-flow", "--no-write")
        # hub-auth links to [[decision-auth-flow]], so it is a DIRECT
        # wikilink-tier match (reverse-ref), not a walked note.
        by_slug = {r["slug"]: r for r in out["results"]}
        assert by_slug["hub-auth"]["tier"] == "wikilink"
        walked = {t["slug"]: t for t in out["traversed"]}
        assert set(walked) == {"learning-token-expiry", "pattern-retry"}
        # pattern-retry IS reached, but only via hub-auth: the pure galaxy
        # chain decision(k=1) -> learning(k=2) -> pattern(k=3) is over budget,
        # while hub-auth (free folder, direct match, k=0) -> pattern is k=1.
        assert walked["pattern-retry"]["walkedFrom"] == ["hub-auth"]

    def test_hard_budget_block_without_hub(self, tmp_path):
        """A pure galaxy chain of length 3 stops at the budget: c1 -> c2 -> c3
        with budget 2 never reaches c3."""
        vault = tmp_path / "vault2"
        note(vault, "galaxy", "chain-1", "---\nupdated: 2026-07-01\n---\n# c1\n[[chain-2]]\n")
        note(vault, "galaxy", "chain-2", "---\nupdated: 2026-07-01\n---\n# c2\n[[chain-3]]\n")
        note(vault, "galaxy", "chain-3", "---\nupdated: 2026-07-01\n---\n# c3\n")
        out = run_query(vault, "--entities", "chain-1", "--no-write")
        walked = {t["slug"] for t in out["traversed"]}
        assert walked == {"chain-2"}

    def test_status_multiplier_ranks_superseded_near_zero(self, tmp_path):
        vault = make_vault(tmp_path)
        out = run_query(vault, "--tags", "retry", "--tags", "tokens", "--no-write")
        by_slug = {r["slug"]: r for r in out["results"]}
        assert by_slug["pattern-retry"]["score"] < by_slug["learning-token-expiry"]["score"]
        assert by_slug["pattern-retry"]["score"] < 0.01  # crushed, still discoverable

    def test_metadata_only_no_bodies(self, tmp_path):
        vault = make_vault(tmp_path)
        proc = run_query(vault, "--entities", "auth", "--no-write", check=False)
        assert proc.returncode == 0
        assert "We chose OAuth" not in proc.stdout  # no note bodies in output

    def test_zero_matches_ok(self, tmp_path):
        vault = make_vault(tmp_path)
        out = run_query(vault, "--entities", "zzz-nothing", "--no-write")
        assert out["results"] == [] and out["traversed"] == []


# ---- telemetry (sections 6.1 / 6.3) -----------------------------------------


class TestTelemetry:
    def test_search_appends_impression_and_walked_events(self, tmp_path):
        vault = make_vault(tmp_path)
        run_query(vault, "--entities", "auth")
        events = read_events(vault)
        by_counter = {}
        for e in events:
            by_counter.setdefault(e["counter"], set()).add(e["slug"])
            # Section 6.1 record shape, exactly.
            assert set(e) == {"id", "ts", "agent", "task", "slug", "counter"}
            assert e["agent"] == "skill" and e["task"] == 13857
        assert by_counter["impression"] == {"decision-auth-flow", "hub-auth"}
        assert by_counter["walked"] == {"learning-token-expiry", "pattern-retry"}
        assert "used" not in by_counter  # engine never writes used

    def test_top_cap_limits_events(self, tmp_path):
        vault = make_vault(tmp_path)
        run_query(vault, "--entities", "auth", "--top", "1")
        events = read_events(vault)
        assert len(events) == 1 and events[0]["slug"] == "decision-auth-flow"

    def test_no_write_emits_zero_events(self, tmp_path):
        """AC4 unit pin: --no-write leaves no telemetry trace at all."""
        vault = make_vault(tmp_path)
        out = run_query(vault, "--entities", "auth", "--no-write")
        assert out["written"] == {"events": 0, "shard": None, "skipped": True}
        assert not (vault / ".telemetry").exists()

    def test_notes_never_mutated(self, tmp_path):
        vault = make_vault(tmp_path)
        before = {p: p.read_text(encoding="utf-8") for p in vault.rglob("*.md")}
        run_query(vault, "--entities", "auth")
        run_record(vault, "--slugs", "decision-auth-flow")
        after = {p: p.read_text(encoding="utf-8") for p in vault.rglob("*.md")}
        assert before == after  # notes stay pure content, forever (6.3)

    def test_aggregation_dedup_and_ranking_feedback(self, tmp_path):
        vault = make_vault(tmp_path)
        run_query(vault, "--entities", "auth")
        run_record(vault, "--slugs", "hub-auth")
        # Duplicate an existing line (union-merge double-merge shape) plus a
        # corrupt line: dedup by id must count once, corrupt line skipped.
        sh = shard(vault)
        lines = sh.read_text(encoding="utf-8").splitlines()
        sh.write_text("\n".join(lines + [lines[0], "{corrupt"]) + "\n", encoding="utf-8")
        out = run_query(vault, "--entities", "auth", "--no-write")
        by_slug = {r["slug"]: r for r in out["results"]}
        assert by_slug["decision-auth-flow"]["impression"] == 1  # deduped
        assert by_slug["hub-auth"]["used"] == 1
        # used weight (2.0) must lift hub-auth over its impression-only peer
        # score composition -- verify used dominates the tiebreak.
        assert by_slug["hub-auth"]["score"] > by_slug["hub-auth"]["impression"] * 0.25

    def test_multi_shard_aggregation(self, tmp_path):
        vault = make_vault(tmp_path)
        run_query(vault, "--entities", "auth")  # shard test-uuid-skill
        run_query(
            vault,
            "--entities",
            "auth",
            identity=["--instance-id", "other-uuid", "--alias", "pm", "--task", "99"],
        )
        out = run_query(vault, "--entities", "auth", "--no-write")
        by_slug = {r["slug"]: r for r in out["results"]}
        assert by_slug["decision-auth-flow"]["impression"] == 2  # summed across shards
        shards = sorted(p.name for p in (vault / ".telemetry").glob("*.jsonl"))
        assert shards == ["other-uuid-pm.jsonl", "test-uuid-skill.jsonl"]

    def test_shard_is_appended_not_rewritten(self, tmp_path):
        vault = make_vault(tmp_path)
        run_query(vault, "--entities", "auth")
        first = shard(vault).read_text(encoding="utf-8")
        run_query(vault, "--entities", "auth")
        second = shard(vault).read_text(encoding="utf-8")
        assert second.startswith(first)  # append-only
        assert second.endswith("\n")  # trailing-newline JSONL discipline


# ---- record (section 8.5 record op) -----------------------------------------


class TestRecord:
    def test_record_used_events(self, tmp_path):
        vault = make_vault(tmp_path)
        out = run_record(vault, "--slugs", "decision-auth-flow,hub-auth", "--slugs", "ghost")
        assert out["recorded"] == ["decision-auth-flow", "hub-auth"]
        assert out["unresolved"] == ["ghost"]
        events = read_events(vault)
        assert [e["counter"] for e in events] == ["used", "used"]
        assert {e["slug"] for e in events} == {"decision-auth-flow", "hub-auth"}

    def test_record_no_write(self, tmp_path):
        vault = make_vault(tmp_path)
        out = run_record(vault, "--slugs", "decision-auth-flow", "--no-write")
        assert out["skipped"] is True and out["events"] == 0
        assert not (vault / ".telemetry").exists()


# ---- degradation (section 9.9) ----------------------------------------------


class TestDegradation:
    def test_cold_start_ranks_by_recency(self, tmp_path):
        """No telemetry at all: ranking still deterministic via tier + recency
        + weight (all counters 0)."""
        vault = make_vault(tmp_path)
        out = run_query(vault, "--entities", "auth", "--no-write")
        assert [r["slug"] for r in out["results"]] == ["decision-auth-flow", "hub-auth"]
        assert all(r["used"] == 0 and r["impression"] == 0 for r in out["results"])

    def test_unreadable_shard_is_skipped(self, tmp_path):
        vault = make_vault(tmp_path)
        (vault / ".telemetry").mkdir()
        (vault / ".telemetry" / "junk.jsonl").write_text("not json at all\n{also bad", encoding="utf-8")
        out = run_query(vault, "--entities", "auth", "--no-write")
        assert [r["slug"] for r in out["results"]] == ["decision-auth-flow", "hub-auth"]

    def test_missing_vault_folders_ok(self, tmp_path):
        vault = tmp_path / "empty-vault"
        vault.mkdir()
        out = run_query(vault, "--entities", "anything", "--no-write")
        assert out["results"] == []


# ---- config (vault-schema.json forward-compat) ------------------------------


class TestConfig:
    def test_schema_overrides_merge_over_defaults(self, tmp_path):
        vault = make_vault(tmp_path)
        (vault / "vault-schema.json").write_text(
            json.dumps({"searchTopK": 1, "folderWeights": {"areas": 50.0}}), encoding="utf-8"
        )
        out = run_query(vault, "--entities", "auth")
        # topK override caps events at 1; areas weight 50 lifts hub-auth to #1
        # (its recency deficit vs decision-auth-flow is about 10x, so a 5x
        # weight would NOT flip the order -- 50x provably does).
        assert [r["slug"] for r in out["results"]][0] == "hub-auth"
        assert len(read_events(vault)) == 1
