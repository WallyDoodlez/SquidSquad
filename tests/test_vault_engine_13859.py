"""#13859 -- vault-v2 P3 (telemetry): pinned behavior tests.

Covers the three P3 deliverables that landed on this branch:

  - S3.3 report (T1): vault-impressions-report.mjs buckets every note per
    VAULT-ARCH 6.4/4.4 (cold / surfaced-never-used / stale; healthy = no
    bucket), least-consumed-first ordering, read-only.
  - S3.3 consumption AC (T2): vault_optimize.py propose-prunes CONSUMES the
    report via the engine subprocess and emits proposals (never auto-applied,
    7.3); engine-unavailable degrades honestly (9.9).
  - S3.4 compaction (T3): compact-telemetry.mjs implements the three 6.5
    invariants -- owner-only, aggregate-before-truncate staged for one
    commit, idempotent via last-absorbed id. THE AC: kill-mid-compaction
    shows no double-count, and the recovery rerun completes the interrupted
    truncation. readTelemetry merges aggregate + live shard as one logical
    stream per writer. Horizon default 30d and <instance>-<alias>.agg.json
    naming are fixed here per the PRD.

JS behavior runs the real engine via subprocess (node); module skips when
node is absent (that environment is the 9.9 degraded path, live-verified
separately). Python-side wiring tests run regardless.
"""

import json
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SKILL_SRC = REPO / "references" / "skills" / "vault-search"
REPORT = SKILL_SRC / "scripts" / "vault-impressions-report.mjs"
COMPACT = SKILL_SRC / "scripts" / "compact-telemetry.mjs"

sys.path.insert(0, str(REPO / "references" / "scripts"))
import vault_optimize  # noqa: E402

NODE = shutil.which("node")
needs_node = pytest.mark.skipif(
    NODE is None, reason="node unavailable -- engine degrades per VAULT-ARCH 9.9")

TODAY = "2026-07-20"


def run_js(script, *args):
    proc = subprocess.run(
        [NODE, str(script), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=60,
    )
    return proc


def note(vault: Path, folder: str, slug: str, body: str) -> Path:
    d = vault / folder
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{slug}.md"
    p.write_text(textwrap.dedent(body), encoding="utf-8")
    return p


def event(eid, ts, slug, counter, alias="skill", task=1):
    return json.dumps({"id": eid, "ts": ts, "agent": alias, "task": task,
                       "slug": slug, "counter": counter})


def write_shard(vault: Path, key: str, lines):
    tdir = vault / ".telemetry"
    tdir.mkdir(parents=True, exist_ok=True)
    (tdir / f"{key}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_vault(tmp_path: Path) -> Path:
    """4-note fixture spanning all four 6.4 buckets."""
    vault = tmp_path / "vault"
    note(vault, "galaxy", "note-cold", """\
        ---
        type: learning
        status: active
        ---
        # Cold -- no telemetry at all
        """)
    note(vault, "galaxy", "note-offered", """\
        ---
        type: pattern
        status: active
        ---
        # Surfaced (impression+walked) but never used
        """)
    note(vault, "galaxy", "note-stale", """\
        ---
        type: decision
        status: active
        ---
        # Used once, long ago
        """)
    note(vault, "galaxy", "note-healthy", """\
        ---
        type: decision
        status: active
        ---
        # Used recently
        """)
    write_shard(vault, "uuid-a-skill", [
        event("r1", "2026-07-01T10:00:00Z", "note-offered", "impression"),
        event("r2", "2026-07-01T10:00:00Z", "note-offered", "walked"),
        event("r3", "2026-01-05T10:00:00Z", "note-stale", "used"),
        event("r4", "2026-07-19T10:00:00Z", "note-healthy", "used"),
    ])
    return vault


# ---------------------------------------------------------------------------
# T1 -- S3.3 report bucketing (6.4/4.4)
# ---------------------------------------------------------------------------

@needs_node
class TestImpressionsReport:
    def test_buckets_and_counts(self, tmp_path):
        vault = make_vault(tmp_path)
        proc = run_js(REPORT, "--vault", str(vault), "--today", TODAY)
        assert proc.returncode == 0, proc.stderr
        rep = json.loads(proc.stdout)
        assert rep["counts"] == {
            "total": 4, "cold": 1, "surfacedNeverUsed": 1, "stale": 1, "healthy": 1}
        by_slug = {r["slug"]: r for r in rep["rows"]}
        assert by_slug["note-cold"]["cold"] is True
        assert by_slug["note-offered"]["surfacedNeverUsed"] is True
        assert by_slug["note-stale"]["stale"] is True
        healthy = by_slug["note-healthy"]
        assert not (healthy["cold"] or healthy["surfacedNeverUsed"] or healthy["stale"])

    def test_least_consumed_first_ordering(self, tmp_path):
        vault = make_vault(tmp_path)
        rep = json.loads(run_js(REPORT, "--vault", str(vault), "--today", TODAY).stdout)
        bands = []
        for r in rep["rows"]:
            bands.append(0 if r["cold"] else 1 if r["surfacedNeverUsed"] else 2 if r["stale"] else 3)
        assert bands == sorted(bands), "rows must be least-consumed-first"

    def test_stale_days_knob(self, tmp_path):
        vault = make_vault(tmp_path)
        # 400-day window: the January use is recent enough -- nothing stale.
        rep = json.loads(run_js(REPORT, "--vault", str(vault), "--today", TODAY,
                                "--stale-days", "400").stdout)
        assert rep["counts"]["stale"] == 0
        assert rep["counts"]["healthy"] == 2

    def test_top_caps_rows_not_counts(self, tmp_path):
        vault = make_vault(tmp_path)
        rep = json.loads(run_js(REPORT, "--vault", str(vault), "--today", TODAY,
                                "--top", "2").stdout)
        assert len(rep["rows"]) == 2
        assert rep["counts"]["total"] == 4

    def test_report_is_read_only(self, tmp_path):
        vault = make_vault(tmp_path)
        tdir = vault / ".telemetry"
        before = {f.name: f.read_bytes() for f in tdir.iterdir()}
        run_js(REPORT, "--vault", str(vault), "--today", TODAY)
        after = {f.name: f.read_bytes() for f in tdir.iterdir()}
        assert before == after, "the 8.5 report row carries no write"


# ---------------------------------------------------------------------------
# T2 -- S3.3 consumption AC (vault_optimize.py proposal run)
# ---------------------------------------------------------------------------

class TestProposePrunes:
    @needs_node
    def test_proposals_consume_report_buckets(self, tmp_path, monkeypatch):
        vault = make_vault(tmp_path)
        monkeypatch.setattr(vault_optimize, "VAULT_DIR", vault)
        result = vault_optimize.propose_prunes(stale_days=90)
        assert result["engineUnavailable"] is False
        by_slug = {p["slug"]: p for p in result["proposals"]}
        assert by_slug["note-stale"]["action"] == "archive"
        assert by_slug["note-stale"]["bucket"] == "stale"
        assert by_slug["note-offered"]["action"] == "review"
        assert by_slug["note-cold"]["action"] == "review"
        assert "note-healthy" not in by_slug, "healthy notes are never proposed"

    @needs_node
    def test_archived_rows_skipped(self, tmp_path, monkeypatch):
        vault = make_vault(tmp_path)
        note(vault, "galaxy", "note-retired", """\
            ---
            type: decision
            status: superseded
            ---
            # Already retired
            """)
        monkeypatch.setattr(vault_optimize, "VAULT_DIR", vault)
        result = vault_optimize.propose_prunes(stale_days=90)
        assert "note-retired" not in {p["slug"] for p in result["proposals"]}

    def test_engine_unavailable_degrades_honestly(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vault_optimize, "ENGINE_REPORT", tmp_path / "missing.mjs")
        result = vault_optimize.propose_prunes()
        assert result == {"proposals": [], "engineUnavailable": True,
                          "reason": "engine report script missing"}


# ---------------------------------------------------------------------------
# T3 -- S3.4 compaction (6.5 invariants)
# ---------------------------------------------------------------------------

OLD1 = event("e1", "2026-05-01T10:00:00Z", "note-a", "impression")
OLD2 = event("e2", "2026-05-02T10:00:00Z", "note-a", "used")
YOUNG = event("e3", "2026-07-19T10:00:00Z", "note-b", "impression")


def compact_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    write_shard(vault, "uuid-a-skill", [OLD1, OLD2, YOUNG])
    return vault


def read_counts(vault: Path):
    """Aggregate view through the real read path (the report's telemetry)."""
    note(vault, "galaxy", "note-a", "---\ntype: learning\n---\n# a\n")
    note(vault, "galaxy", "note-b", "---\ntype: learning\n---\n# b\n")
    rep = json.loads(run_js(REPORT, "--vault", str(vault), "--today", TODAY).stdout)
    return {r["slug"]: (r["impression"], r["used"], r["walked"]) for r in rep["rows"]}


@needs_node
class TestCompaction:
    def test_absorbs_old_keeps_young(self, tmp_path):
        vault = compact_vault(tmp_path)
        proc = run_js(COMPACT, "--vault", str(vault), "--instance-id", "uuid-a",
                      "--alias", "skill", "--today", TODAY)
        assert proc.returncode == 0, proc.stderr
        out = json.loads(proc.stdout)
        assert out["absorbed"] == 2 and out["remaining"] == 1
        shard = (vault / ".telemetry" / "uuid-a-skill.jsonl").read_text(encoding="utf-8")
        assert "e3" in shard and "e1" not in shard and "e2" not in shard
        agg = json.loads((vault / ".telemetry" / "uuid-a-skill.agg.json").read_text(encoding="utf-8"))
        assert agg["lastAbsorbedId"] == "e2"
        assert agg["counts"]["note-a"] == {
            "impression": 1, "used": 1, "walked": 0, "lastUsed": "2026-05-02"}

    def test_aggregate_naming_and_horizon_default(self, tmp_path):
        """PRD fixes: <instance>-<alias>.agg.json, horizon 30d."""
        vault = tmp_path / "vault"
        # 31 days old on the default horizon -> absorbed; 29 days -> kept.
        write_shard(vault, "uuid-a-skill", [
            event("h1", "2026-06-19T10:00:00Z", "note-a", "impression"),  # 31d
            event("h2", "2026-06-21T10:00:00Z", "note-a", "impression"),  # 29d
        ])
        out = json.loads(run_js(COMPACT, "--vault", str(vault), "--instance-id", "uuid-a",
                                "--alias", "skill", "--today", TODAY).stdout)
        assert out["absorbed"] == 1 and out["remaining"] == 1
        assert (vault / ".telemetry" / "uuid-a-skill.agg.json").is_file()

    def test_idempotent_rerun(self, tmp_path):
        vault = compact_vault(tmp_path)
        run_js(COMPACT, "--vault", str(vault), "--instance-id", "uuid-a",
               "--alias", "skill", "--today", TODAY)
        tdir = vault / ".telemetry"
        first = {f.name: f.read_bytes() for f in tdir.iterdir()}
        out = json.loads(run_js(COMPACT, "--vault", str(vault), "--instance-id", "uuid-a",
                                "--alias", "skill", "--today", TODAY).stdout)
        assert out["absorbed"] == 0
        assert {f.name: f.read_bytes() for f in tdir.iterdir()} == first

    def test_owner_only_identity_required(self, tmp_path):
        vault = compact_vault(tmp_path)
        proc = run_js(COMPACT, "--vault", str(vault), "--alias", "skill")
        assert proc.returncode == 2
        assert "owner" in proc.stderr

    def test_owner_only_never_touches_other_writers(self, tmp_path):
        vault = compact_vault(tmp_path)
        write_shard(vault, "uuid-b-qa", [OLD1])
        other_before = (vault / ".telemetry" / "uuid-b-qa.jsonl").read_bytes()
        run_js(COMPACT, "--vault", str(vault), "--instance-id", "uuid-a",
               "--alias", "skill", "--today", TODAY)
        assert (vault / ".telemetry" / "uuid-b-qa.jsonl").read_bytes() == other_before
        assert not (vault / ".telemetry" / "uuid-b-qa.agg.json").exists()

    def test_missing_shard_is_a_noop(self, tmp_path):
        vault = tmp_path / "vault"
        (vault / ".telemetry").mkdir(parents=True)
        proc = run_js(COMPACT, "--vault", str(vault), "--instance-id", "uuid-a",
                      "--alias", "skill", "--today", TODAY)
        assert proc.returncode == 0
        assert json.loads(proc.stdout)["absorbed"] == 0
        assert list((vault / ".telemetry").iterdir()) == []

    def test_corrupt_line_kept_never_absorbed(self, tmp_path):
        vault = tmp_path / "vault"
        write_shard(vault, "uuid-a-skill", [OLD1, "{corrupt", OLD2])
        out = json.loads(run_js(COMPACT, "--vault", str(vault), "--instance-id", "uuid-a",
                                "--alias", "skill", "--today", TODAY).stdout)
        # Prefix rule: e1 absorbs; the corrupt line stops absorption (a
        # non-prefix absorbed range would break positional idempotency).
        assert out["absorbed"] == 1
        shard = (vault / ".telemetry" / "uuid-a-skill.jsonl").read_text(encoding="utf-8")
        assert "{corrupt" in shard and "e2" in shard


@needs_node
class TestKillMidCompaction:
    """THE S3.4 AC: aggregate written, truncate never ran (the 6.5 crash
    window). Counts must not double; the rerun completes the truncation."""

    def crash_window(self, tmp_path: Path) -> Path:
        vault = compact_vault(tmp_path)
        run_js(COMPACT, "--vault", str(vault), "--instance-id", "uuid-a",
               "--alias", "skill", "--today", TODAY)
        # Undo ONLY the truncation: restore the full pre-compaction shard,
        # keep the aggregate -- byte-exact reproduction of a kill between
        # invariant 2's two writes.
        write_shard(vault, "uuid-a-skill", [OLD1, OLD2, YOUNG])
        return vault

    def test_no_double_count_in_crash_window(self, tmp_path):
        vault = self.crash_window(tmp_path)
        counts = read_counts(vault)
        assert counts["note-a"] == (1, 1, 0), "aggregate + un-truncated shard double-counted"
        assert counts["note-b"] == (1, 0, 0)

    def test_recovery_rerun_completes_truncation(self, tmp_path):
        vault = self.crash_window(tmp_path)
        out = json.loads(run_js(COMPACT, "--vault", str(vault), "--instance-id", "uuid-a",
                                "--alias", "skill", "--today", TODAY).stdout)
        assert out["absorbed"] == 0, "absorbed prefix must never re-absorb"
        assert out["recoveredPrefix"] == 2
        shard = (vault / ".telemetry" / "uuid-a-skill.jsonl").read_text(encoding="utf-8")
        assert "e1" not in shard and "e2" not in shard and "e3" in shard
        agg = json.loads((vault / ".telemetry" / "uuid-a-skill.agg.json").read_text(encoding="utf-8"))
        assert agg["counts"]["note-a"] == {
            "impression": 1, "used": 1, "walked": 0, "lastUsed": "2026-05-02"}

    def test_counts_stable_across_recovery(self, tmp_path):
        vault = self.crash_window(tmp_path)
        before = read_counts(vault)
        run_js(COMPACT, "--vault", str(vault), "--instance-id", "uuid-a",
               "--alias", "skill", "--today", TODAY)
        assert read_counts(vault) == before, "recovery changed observable counts"

    def test_marker_substring_never_latches_skip(self, tmp_path):
        """Review finding on 5e71f6e06: the skip boundary must be located by
        EXACT parsed id. A corrupt line merely CONTAINING the marker text (or
        an id-prefix collision) must not put the read into a skip state that
        silently drops every later event."""
        vault = tmp_path / "vault"
        # Aggregate claims e2 absorbed; the shard's only trace of "e2" is a
        # corrupt fragment plus an id ("e2x") that contains it as a prefix.
        write_shard(vault, "uuid-a-skill", [
            '{"corrupt line mentioning e2',
            event("e2x", "2026-07-18T10:00:00Z", "note-a", "impression"),
            event("e9", "2026-07-19T10:00:00Z", "note-b", "impression"),
        ])
        (vault / ".telemetry" / "uuid-a-skill.agg.json").write_text(
            json.dumps({"lastAbsorbedId": "e2",
                        "counts": {"note-a": {"impression": 1, "used": 1,
                                              "walked": 0, "lastUsed": "2026-05-02"}}}) + "\n",
            encoding="utf-8")
        counts = read_counts(vault)
        # e2x and e9 MUST both be visible: aggregate 1 + live e2x = 2.
        assert counts["note-a"] == (2, 1, 0), "live event dropped by a latched skip"
        assert counts["note-b"] == (1, 0, 0), "post-marker event dropped by a latched skip"


# ---------------------------------------------------------------------------
# T3 -- vault_optimize.py compact-telemetry wiring
# ---------------------------------------------------------------------------

class TestCompactTelemetryWiring:
    @needs_node
    def test_wired_pass_compacts_own_shard(self, tmp_path, monkeypatch):
        vault = tmp_path / "vault"
        write_shard(vault, "uuid-a-skill", [OLD1, OLD2])
        monkeypatch.setattr(vault_optimize, "VAULT_DIR", vault)
        monkeypatch.setattr(vault_optimize, "INSTANCE_ID_FILE", tmp_path / "iid")
        (tmp_path / "iid").write_text("uuid-a\n", encoding="utf-8")
        result = vault_optimize.compact_telemetry("skill", horizon_days=30)
        assert result["skipped"] is False
        assert result["absorbed"] == 2
        assert (vault / ".telemetry" / "uuid-a-skill.agg.json").is_file()

    def test_unprovisioned_identity_refuses_to_compact(self, tmp_path, monkeypatch):
        """Distinct un-minted clones with one alias share the 'unprovisioned'
        shard -- owner-only does not hold there, so the destructive pass must
        refuse (review finding on 14b632bc3)."""
        vault = tmp_path / "vault"
        write_shard(vault, "unprovisioned-skill", [OLD1])
        monkeypatch.setattr(vault_optimize, "VAULT_DIR", vault)
        monkeypatch.setattr(vault_optimize, "INSTANCE_ID_FILE", tmp_path / "absent")
        result = vault_optimize.compact_telemetry("skill")
        assert result["skipped"] is True
        assert result["engineUnavailable"] is False
        assert "unprovisioned" in result["reason"]
        # And the shard was not touched.
        shard = vault / ".telemetry" / "unprovisioned-skill.jsonl"
        assert "e1" in shard.read_text(encoding="utf-8")

    def test_engine_unavailable_degrades_honestly(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vault_optimize, "ENGINE_COMPACT", tmp_path / "missing.mjs")
        result = vault_optimize.compact_telemetry("skill")
        assert result["skipped"] is True
        assert result["engineUnavailable"] is True
        assert result["reason"] == "engine compact script missing"

    def test_cli_requires_alias(self):
        proc = subprocess.run(
            [sys.executable, str(REPO / "references" / "scripts" / "vault_optimize.py"),
             "compact-telemetry"],
            capture_output=True, text=True, encoding="utf-8", timeout=60,
        )
        assert proc.returncode == 2
        assert "--alias" in proc.stderr


# ---------------------------------------------------------------------------
# T4 -- provisional instance-id mint (wizard; P5/S5.2 replaces)
# ---------------------------------------------------------------------------

import wizard  # noqa: E402  (path inserted above)


class TestInstanceIdMint:
    def make_root(self, tmp_path: Path) -> Path:
        root = tmp_path / "install"
        (root / "references" / "skills").mkdir(parents=True)
        return root

    def test_mints_uuid_into_squidsquad_dir(self, tmp_path):
        root = self.make_root(tmp_path)
        result = wizard.install_vault_engine(root)
        assert result["instance_id_minted"] is True
        iid = (root / ".squidsquad" / ".instance-id").read_text(encoding="utf-8").strip()
        import uuid
        assert str(uuid.UUID(iid)) == iid, "must be a well-formed UUID"

    def test_existing_id_never_reminted(self, tmp_path):
        """Re-minting would orphan the clone's shard history under the old
        writer name -- mint-if-absent is a hard rule."""
        root = self.make_root(tmp_path)
        (root / ".squidsquad").mkdir(parents=True)
        (root / ".squidsquad" / ".instance-id").write_text("keep-me\n", encoding="utf-8")
        result = wizard.install_vault_engine(root)
        assert result["instance_id_minted"] is False
        assert (root / ".squidsquad" / ".instance-id").read_text(
            encoding="utf-8").strip() == "keep-me"

    def test_empty_file_treated_as_absent(self, tmp_path):
        root = self.make_root(tmp_path)
        (root / ".squidsquad").mkdir(parents=True)
        (root / ".squidsquad" / ".instance-id").write_text("", encoding="utf-8")
        result = wizard.install_vault_engine(root)
        assert result["instance_id_minted"] is True

    def test_instance_id_is_gitignored(self):
        lines = (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()
        # Exact-line match: the .tmp entry alone must not satisfy this
        # (substring containment would -- review finding on 14b632bc3).
        assert ".squidsquad/.instance-id" in lines
        assert ".squidsquad/.instance-id.tmp" in lines


# ---------------------------------------------------------------------------
# T4 -- S3.1 live AC: two clones writing concurrently, zero conflicts
# ---------------------------------------------------------------------------

GIT = shutil.which("git")
RECORD = SKILL_SRC / "scripts" / "record-consumption.mjs"


@needs_node
@pytest.mark.skipif(GIT is None, reason="git unavailable")
class TestTwoCloneConcurrency:
    """S3.1 AC (VAULT-ARCH 6.3): two clones, each writing its OWN shard via
    the engine, merge with zero conflicts; dedup-by-id holds at read. Also
    pins the merge=union backstop for the same-file case."""

    def git(self, cwd, *args):
        proc = subprocess.run(
            [GIT, "-C", str(cwd), *args],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=60,
        )
        return proc

    def make_clones(self, tmp_path: Path):
        origin = tmp_path / "origin.git"
        subprocess.run([GIT, "init", "--bare", "-b", "main", str(origin)],
                       capture_output=True, timeout=60, check=True)
        a, b = tmp_path / "clone-a", tmp_path / "clone-b"
        for c in (a, b):
            subprocess.run([GIT, "clone", str(origin), str(c)],
                           capture_output=True, timeout=60, check=True)
            self.git(c, "config", "user.email", "t@t")
            self.git(c, "config", "user.name", "t")
        # Seed vault + union attribute from clone A (the installer's job).
        tele = a / "vault" / ".telemetry"
        tele.mkdir(parents=True)
        (tele / ".gitattributes").write_text("*.jsonl merge=union\n", encoding="utf-8")
        note(a / "vault", "galaxy", "note-x", "---\ntype: learning\n---\n# x\n")
        self.git(a, "add", "-A")
        self.git(a, "commit", "-m", "seed")
        self.git(a, "push", "origin", "main")
        self.git(b, "pull", "origin", "main")
        return a, b

    def record(self, clone: Path, iid: str, alias: str):
        proc = subprocess.run(
            [NODE, str(RECORD), "--vault", str(clone / "vault"),
             "--slugs", "note-x", "--task", "13859",
             "--instance-id", iid, "--alias", alias],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=60,
        )
        assert proc.returncode == 0, proc.stderr
        return proc

    def test_distinct_writers_merge_with_zero_conflicts(self, tmp_path):
        a, b = self.make_clones(tmp_path)
        # Concurrent writes: each clone appends to its OWN shard, unpulled.
        self.record(a, "uuid-a", "skill")
        self.record(b, "uuid-b", "qa")
        self.git(a, "add", "-A"); self.git(a, "commit", "-m", "a events")
        assert self.git(a, "push", "origin", "main").returncode == 0
        self.git(b, "add", "-A"); self.git(b, "commit", "-m", "b events")
        merge = self.git(b, "pull", "--no-rebase", "origin", "main")
        assert merge.returncode == 0, f"merge conflicted: {merge.stdout}{merge.stderr}"
        assert self.git(b, "push", "origin", "main").returncode == 0
        # Both shards present in the merged tree; dedup holds at read.
        tele = b / "vault" / ".telemetry"
        assert (tele / "uuid-a-skill.jsonl").is_file()
        assert (tele / "uuid-b-qa.jsonl").is_file()
        rep = json.loads(run_js(REPORT, "--vault", str(b / "vault"),
                                "--today", TODAY).stdout)
        row = {r["slug"]: r for r in rep["rows"]}["note-x"]
        assert row["used"] == 2, "one used event per writer, deduped by id"

    def test_union_merge_backstop_same_file(self, tmp_path):
        """Same shard file appended in both clones (the pathological case the
        .gitattributes backstop exists for): union merge keeps BOTH lines."""
        a, b = self.make_clones(tmp_path)
        for clone, eid in ((a, "u1"), (b, "u2")):
            shard = clone / "vault" / ".telemetry" / "shared-w.jsonl"
            with open(shard, "a", encoding="utf-8") as f:
                f.write(event(eid, "2026-07-20T10:00:00Z", "note-x", "used") + "\n")
        self.git(a, "add", "-A"); self.git(a, "commit", "-m", "a line")
        assert self.git(a, "push", "origin", "main").returncode == 0
        self.git(b, "add", "-A"); self.git(b, "commit", "-m", "b line")
        merge = self.git(b, "pull", "--no-rebase", "origin", "main")
        assert merge.returncode == 0, f"union merge failed: {merge.stdout}{merge.stderr}"
        merged = (b / "vault" / ".telemetry" / "shared-w.jsonl").read_text(encoding="utf-8")
        assert "u1" in merged and "u2" in merged, "union merge must keep both writers' lines"
