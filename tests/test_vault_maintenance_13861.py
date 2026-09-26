"""#13861 -- PRD-VAULT-V2 P5: harness-scheduled optimize + instance-id mint.

  - S5.2 (TestInstanceId*): the harness mints/persists its instance UUID in its
    own gitignored .instance-id (mint-if-absent, so it survives restarts; two
    harness dirs mint distinct ids), distributes it to every agent clone
    (production-only), and reports it on /status.
  - S5.1 (TestAnalyzeQueue .. TestMaintenanceWindow): vault_optimize.py selects
    the last_optimized queue (14-day cutoff), stamps it, and files
    contradictions / pruning proposals as deduped `pending` HITL tasks (never
    applied); the harness maintenance window runs the queue on a schedule and
    wakes pm with a `vault-maintenance` event.

Every forge/harness egress is stubbed at its single seam (vault_optimize._tracker,
harness._emit_event, subprocess.run) and every file lives under tmp_path --
never the live .squidsquad (see learning-tests-must-not-mutate-shared-live-state).
"""

import asyncio
import inspect
import json
import subprocess
import sys
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "references" / "scripts"))

import harness  # noqa: E402
import vault_optimize  # noqa: E402


# ---------------------------------------------------------------------------
# S5.2 -- instance id
# ---------------------------------------------------------------------------

class TestInstanceIdMint:
    def test_mints_uuid_when_absent_and_persists(self, tmp_path):
        f = tmp_path / ".squidsquad" / ".instance-id"
        iid = harness._ensure_instance_id(f)
        assert str(uuid.UUID(iid)) == iid
        assert f.read_text(encoding="utf-8").strip() == iid
        assert not (f.parent / ".instance-id.tmp").exists()

    def test_survives_restart(self, tmp_path):
        f = tmp_path / ".instance-id"
        first = harness._ensure_instance_id(f)
        assert harness._ensure_instance_id(f) == first

    def test_two_harness_instances_mint_distinct_ids(self, tmp_path):
        a = harness._ensure_instance_id(tmp_path / "a" / ".instance-id")
        b = harness._ensure_instance_id(tmp_path / "b" / ".instance-id")
        assert a != b

    def test_adopts_provision_time_mint(self, tmp_path):
        f = tmp_path / ".instance-id"
        f.write_text("wizard-minted-id\n", encoding="utf-8")
        assert harness._ensure_instance_id(f) == "wizard-minted-id"

    def test_empty_file_is_minted(self, tmp_path):
        f = tmp_path / ".instance-id"
        f.write_text("  \n", encoding="utf-8")
        iid = harness._ensure_instance_id(f)
        assert iid and f.read_text(encoding="utf-8").strip() == iid

    def test_unpersistable_returns_none(self, tmp_path):
        f = tmp_path / ".instance-id"
        f.mkdir()  # a directory where the file should be: neither read nor replace works
        assert harness._ensure_instance_id(f) is None

    def test_default_path_is_harness_own_gitignored_file(self):
        assert harness.INSTANCE_ID_FILE == harness.SQUIDSQUAD_DIR / ".instance-id"
        lines = (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()
        assert ".squidsquad/.instance-id" in lines


def _fleet(tmp_path):
    roots = {}
    for role, name in (("pm", "Proj"), ("skill", "Proj-2"), ("qa", "Proj-qa")):
        root = tmp_path / name
        (root / ".squidsquad").mkdir(parents=True)
        roots[role] = root
    return roots


class TestInstanceIdDistribution:
    def test_isolated_harness_skips(self, tmp_path):
        with patch.object(harness, "SQUIDSQUAD_DIR", tmp_path / "isolated"):
            assert harness._distribute_instance_id_to_clones("iid") is None

    def test_production_repoints_siblings_not_itself(self, tmp_path):
        roots = _fleet(tmp_path)
        (roots["skill"] / ".squidsquad" / ".instance-id").write_text("p3-per-clone\n",
                                                                    encoding="utf-8")
        (roots["qa"] / ".squidsquad" / ".instance-id").write_text("harness-id\n",
                                                                 encoding="utf-8")
        (tmp_path / "Proj-3").mkdir()  # clone without .squidsquad: skipped
        clone_map = {r: str(p) for r, p in roots.items()}
        clone_map["dm"] = str(tmp_path / "Proj-3")
        with patch.object(harness, "REPO_ROOT", roots["pm"]), \
             patch.object(harness, "SQUIDSQUAD_DIR", roots["pm"] / ".squidsquad"), \
             patch.object(harness.boot_remote, "_parse_local_config",
                          return_value=clone_map):
            rewritten = harness._distribute_instance_id_to_clones("harness-id")
        assert rewritten == [("skill", "p3-per-clone")]
        assert (roots["skill"] / ".squidsquad" / ".instance-id").read_text(
            encoding="utf-8").strip() == "harness-id"
        assert not (roots["pm"] / ".squidsquad" / ".instance-id").exists(), \
            "the harness root is never written by distribution (it owns the source)"
        assert not (tmp_path / "Proj-3" / ".squidsquad").exists()

    def test_unset_clone_reports_none_as_old(self, tmp_path):
        roots = _fleet(tmp_path)
        with patch.object(harness, "REPO_ROOT", roots["pm"]), \
             patch.object(harness, "SQUIDSQUAD_DIR", roots["pm"] / ".squidsquad"), \
             patch.object(harness.boot_remote, "_parse_local_config",
                          return_value={r: str(p) for r, p in roots.items()}):
            rewritten = harness._distribute_instance_id_to_clones("hid")
        assert sorted(rewritten) == [("qa", None), ("skill", None)]


class TestInstanceIdWiring:
    def test_lifespan_mints_before_deferred_distribution_before_autostart(self):
        src = inspect.getsource(harness.lifespan)
        assert "state.instance_id = _ensure_instance_id()" in src
        init = src[src.index("def _deferred_init"):]
        dist = init.index("_distribute_instance_id_to_clones(state.instance_id)")
        assert dist < init.index("Auto-starting all agents")

    def test_status_reports_instance_id(self):
        with patch.object(harness.state, "instance_id", "abc-123"):
            body = asyncio.run(harness.get_status())
        assert body["harness"]["instance_id"] == "abc-123"


# ---------------------------------------------------------------------------
# S5.1 -- vault_optimize analyze queue / stamp / HITL filing
# ---------------------------------------------------------------------------

def _note(vault, rel, **fm):
    p = vault / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    head = "".join(f"{k}: {v}\n" for k, v in fm.items())
    p.write_text(f"---\n{head}---\n\n# {p.stem}\n\nbody\n", encoding="utf-8")
    return p


@pytest.fixture
def vault(tmp_path, monkeypatch):
    v = tmp_path / "vault"
    v.mkdir()
    monkeypatch.setattr(vault_optimize, "VAULT_DIR", v)
    return v


class TestAnalyzeQueue:
    def test_due_selection_and_order(self, vault):
        from datetime import date
        _note(vault, "galaxy/decision-fresh.md", status="active", last_optimized="2026-09-20")
        _note(vault, "galaxy/learning-old.md", status="active", last_optimized="2026-09-01")
        _note(vault, "galaxy/learning-older.md", status="active", last_optimized="2026-08-01")
        _note(vault, "galaxy/pattern-never.md", status="active")
        _note(vault, "systems/harness.md", status="active", last_optimized="not-a-date")
        _note(vault, "galaxy/learning-retired.md", status="superseded")
        _note(vault, "archives/legacy.md", status="active")
        (vault / "BRIEFING.md").write_text("# Briefing\n", encoding="utf-8")
        out = vault_optimize.analyze_queue(today=date(2026, 9, 26))
        assert [n["slug"] for n in out["queue"]] == [
            "pattern-never", "harness", "learning-older", "learning-old"]
        assert out["total_due"] == 4 and out["cutoff_days"] == 14

    def test_cutoff_boundary_is_inclusive_at_14_days(self, vault):
        from datetime import date
        _note(vault, "galaxy/a.md", last_optimized="2026-09-12")  # exactly 14d
        _note(vault, "galaxy/b.md", last_optimized="2026-09-13")  # 13d
        out = vault_optimize.analyze_queue(today=date(2026, 9, 26))
        assert [n["slug"] for n in out["queue"]] == ["a"]

    def test_limit_caps_queue_not_total(self, vault):
        for i in range(5):
            _note(vault, f"galaxy/n{i}.md")
        out = vault_optimize.analyze_queue(limit=2)
        assert len(out["queue"]) == 2 and out["total_due"] == 5


class TestMarkOptimized:
    def test_inserts_and_replaces_without_touching_updated(self, vault):
        a = _note(vault, "galaxy/a.md", status="active", updated="2026-01-01")
        b = _note(vault, "galaxy/b.md", last_optimized="2026-01-01", updated="2026-01-02")
        out = vault_optimize.mark_optimized(["a", "b", "ghost"], date="2026-09-26")
        assert out["marked"] == ["a", "b"] and out["missing"] == ["ghost"]
        ta, tb = a.read_text(encoding="utf-8"), b.read_text(encoding="utf-8")
        assert "last_optimized: 2026-09-26" in ta and "updated: 2026-01-01" in ta
        assert tb.count("last_optimized:") == 1 and "last_optimized: 2026-09-26" in tb
        assert "updated: 2026-01-02" in tb
        assert ta.endswith("body\n")
        assert vault_optimize._parse_frontmatter(ta)["last_optimized"] == "2026-09-26"

    def test_crlf_note_keeps_crlf_line_endings(self, vault):
        """Review fix: the stamp must not flip a CRLF note's whole file to LF."""
        (vault / "galaxy").mkdir()
        for name, fm in (("ins", "status: active\r\n"),
                         ("rep", "last_optimized: 2026-01-01\r\nstatus: active\r\n")):
            (vault / "galaxy" / f"{name}.md").write_bytes(
                f"---\r\n{fm}---\r\n\r\n# {name}\r\n".encode("utf-8"))
        vault_optimize.mark_optimized(["ins", "rep"], date="2026-09-26")
        for name in ("ins", "rep"):
            raw = (vault / "galaxy" / f"{name}.md").read_bytes()
            assert b"last_optimized: 2026-09-26\r\n" in raw
            assert raw.count(b"\n") == raw.count(b"\r\n"), f"{name}: mixed line endings"
            assert raw.count(b"last_optimized") == 1

    def test_note_without_frontmatter_is_missing(self, vault):
        (vault / "galaxy").mkdir()
        (vault / "galaxy" / "bare.md").write_text("# bare\n", encoding="utf-8")
        assert vault_optimize.mark_optimized(["bare"])["missing"] == ["bare"]

    def test_stamped_note_leaves_the_queue(self, vault):
        _note(vault, "galaxy/a.md")
        vault_optimize.mark_optimized(["a"])
        assert vault_optimize.analyze_queue()["queue"] == []


class _Forge:
    """Stub for vault_optimize._tracker: open pm task titles + create log."""

    def __init__(self, titles=(), list_rc=0, create_rc=0):
        self.titles, self.list_rc, self.create_rc = list(titles), list_rc, create_rc
        self.created = []

    def __call__(self, *args):
        if args[0] == "list-by-labels":
            assert args[1] == "type:task,role:pm"
            return self.list_rc, json.dumps([{"number": 1, "title": t} for t in self.titles])
        if args[0] == "create-task":
            self.created.append(args)
            return self.create_rc, 'NOTE: x\n{"number": 4242, "url": "u"}\n'
        raise AssertionError(args)


def _opt(args, flag):
    return args[args.index(flag) + 1]


class TestFileContradiction:
    def test_files_pending_pm_task_with_sorted_pair_title(self, monkeypatch):
        forge = _Forge()
        monkeypatch.setattr(vault_optimize, "_tracker", forge)
        out = vault_optimize.file_contradiction(
            "rule-z", "decision-a", "merge policy", "always rebase", "never rebase", "pm")
        assert out == {"filed": True, "number": 4242,
                       "title": "Vault contradiction: decision-a vs rule-z"}
        (args,) = forge.created
        assert _opt(args, "--role") == "pm" and _opt(args, "--priority") == "low"
        body = _opt(args, "--body")
        assert "[[decision-a]]: never rebase" in body and "[[rule-z]]: always rebase" in body
        assert "nothing has been changed" in body

    def test_open_duplicate_is_not_refiled(self, monkeypatch):
        forge = _Forge(titles=["TASK: Vault contradiction: decision-a vs rule-z"])
        monkeypatch.setattr(vault_optimize, "_tracker", forge)
        out = vault_optimize.file_contradiction("decision-a", "rule-z", "t", "x", "y", "pm")
        assert out["filed"] is False and "already exists" in out["reason"]
        assert forge.created == []

    def test_non_ascii_slug_dedupes_against_transliterated_forge_title(self, monkeypatch):
        """Review fix: tracker stores an ASCII-transliterated title (#13517)."""
        import tracker
        title = "Vault contradiction: decision-café vs rule-z"
        forge = _Forge(titles=[f"TASK: {tracker._asciiize_title(title)}"])
        monkeypatch.setattr(vault_optimize, "_tracker", forge)
        out = vault_optimize.file_contradiction("rule-z", "decision-café", "t", "x", "y", "pm")
        assert out["filed"] is False and forge.created == []

    def test_forge_read_failure_refuses_to_file_blind(self, monkeypatch):
        forge = _Forge(list_rc=1)
        monkeypatch.setattr(vault_optimize, "_tracker", forge)
        assert vault_optimize.file_contradiction("a", "b", "t", "x", "y", "pm")["filed"] is False
        assert forge.created == []

    def test_same_note_twice_rejected(self, monkeypatch):
        monkeypatch.setattr(vault_optimize, "_tracker", _Forge())
        assert vault_optimize.file_contradiction("a", "a", "t", "x", "y", "pm")["filed"] is False

    def test_cli_exit_codes(self, monkeypatch):
        forge = _Forge(create_rc=1)
        monkeypatch.setattr(vault_optimize, "_tracker", forge)
        base = ["vault_optimize.py", "file-contradiction", "--slug-a", "a", "--slug-b", "b",
                "--topic", "t", "--statement-a", "x", "--statement-b", "y", "--reporter", "pm"]
        monkeypatch.setattr(sys, "argv", base)
        assert vault_optimize.main() == 1  # create failed -> nonzero
        forge.create_rc = 0
        assert vault_optimize.main() == 0
        monkeypatch.setattr(sys, "argv", base[:4])
        assert vault_optimize.main() == 2


class TestFilePruneReview:
    PROPOSALS = {"proposals": [
        {"slug": "learning-x", "path": "galaxy/learning-x.md", "action": "archive",
         "bucket": "stale", "evidence": "used 2x, last 2026-01-01"},
        {"slug": "pattern-y", "path": "galaxy/pattern-y.md", "action": "review",
         "bucket": "cold", "evidence": "never surfaced by any search"}],
        "engineUnavailable": False}

    def test_files_one_review_task(self, monkeypatch):
        forge = _Forge()
        monkeypatch.setattr(vault_optimize, "_tracker", forge)
        monkeypatch.setattr(vault_optimize, "propose_prunes", lambda stale_days=90: self.PROPOSALS)
        out = vault_optimize.file_prune_review("pm")
        assert out["filed"] and out["title"] == "Vault pruning review: 2 notes"
        body = _opt(forge.created[0], "--body")
        assert "[[learning-x]] -- stale -> archive" in body and "[[pattern-y]] -- cold" in body

    @pytest.mark.parametrize("proposals,titles,reason", [
        ({"proposals": [], "engineUnavailable": True, "reason": "node unavailable"}, [],
         "engine unavailable"),
        ({"proposals": [], "engineUnavailable": False}, [], "no proposals"),
        (PROPOSALS, ["TASK: Vault pruning review: 7 notes"], "already exists"),
    ])
    def test_skips(self, monkeypatch, proposals, titles, reason):
        forge = _Forge(titles=titles)
        monkeypatch.setattr(vault_optimize, "_tracker", forge)
        monkeypatch.setattr(vault_optimize, "propose_prunes", lambda stale_days=90: proposals)
        out = vault_optimize.file_prune_review("pm")
        assert out["filed"] is False and reason in out["reason"]
        assert forge.created == []


# ---------------------------------------------------------------------------
# S5.1 -- harness maintenance window
# ---------------------------------------------------------------------------

@pytest.fixture
def window(tmp_path, monkeypatch):
    """Isolated window: tmp state file, stubbed analyze-queue subprocess,
    captured emits, pm alias pinned, config interval at its default."""
    ctx = {"queue": {"queue": [{"slug": "a", "path": "galaxy/a.md"}], "total_due": 3},
           "rc": 0, "emitted": [], "calls": 0}
    monkeypatch.setattr(harness, "VAULT_MAINTENANCE_STATE_FILE",
                        tmp_path / ".vault-maintenance.json")

    def fake_run(cmd, **kw):
        ctx["calls"] += 1
        assert cmd[1].endswith("vault_optimize.py") and cmd[2] == "analyze-queue"
        assert cmd[cmd.index("--cutoff-days") + 1] == "14"
        return subprocess.CompletedProcess(cmd, ctx["rc"], json.dumps(ctx["queue"]), "boom")

    def fake_emit(event_type, role, payload=None, **extra):
        ctx["emitted"].append((event_type, role, payload))
        return {"id": "ev1"}

    monkeypatch.setattr(harness.subprocess, "run", fake_run)
    monkeypatch.setattr(harness, "_emit_event", fake_emit)
    monkeypatch.setattr(harness.ExternalActivityDetector, "_alias_for_role_class",
                        staticmethod(lambda rc: {"pm": "pm-alias"}[rc]))
    monkeypatch.setattr(harness, "_vault_optimize_interval_hours", lambda: 24.0)
    return ctx


class TestMaintenanceWindow:
    def test_first_window_is_due_and_wakes_pm(self, window):
        out = harness.run_vault_maintenance_window(now=1000.0)
        assert out["ran"] and out["total_due"] == 3 and out["queued"] == 1
        (etype, role, payload), = window["emitted"]
        assert etype == "vault-maintenance" and role == "harness"
        assert payload["target_alias"] == "pm-alias" and payload["cutoff_days"] == 14
        state = json.loads(harness.VAULT_MAINTENANCE_STATE_FILE.read_text(encoding="utf-8"))
        assert state["last_window_at"] == 1000.0
        assert state["last_result"]["emitted"] == {"event_id": "ev1", "target_alias": "pm-alias"}

    def test_not_due_until_interval_elapses(self, window):
        harness.run_vault_maintenance_window(now=1000.0)
        out = harness.run_vault_maintenance_window(now=1000.0 + 23 * 3600)
        assert out["ran"] is False and out["next_due_at"] == 1000.0 + 24 * 3600
        assert window["calls"] == 1
        assert harness.run_vault_maintenance_window(now=1000.0 + 24 * 3600)["ran"]

    def test_force_ignores_schedule(self, window):
        harness.run_vault_maintenance_window(now=1000.0)
        assert harness.run_vault_maintenance_window(force=True, now=1001.0)["forced"]
        assert window["calls"] == 2

    def test_empty_queue_emits_nothing_but_advances(self, window):
        window["queue"] = {"queue": [], "total_due": 0}
        out = harness.run_vault_maintenance_window(now=5.0)
        assert out["ran"] and out["emitted"] is None and window["emitted"] == []
        assert harness._read_vault_maintenance_state()["last_window_at"] == 5.0

    def test_analyze_failure_recorded_and_retried_next_interval(self, window):
        window["rc"] = 1
        out = harness.run_vault_maintenance_window(now=5.0)
        assert "analyze-queue exited 1" in out["error"] and window["emitted"] == []
        assert harness._read_vault_maintenance_state()["last_window_at"] == 5.0

    def test_endpoints(self, window):
        forced = asyncio.run(harness.post_vault_maintenance())
        assert forced["ran"] and forced["forced"]
        body = asyncio.run(harness.get_vault_maintenance())
        assert body["interval_hours"] == 24.0 and body["cutoff_days"] == 14
        assert body["last_result"]["queued"] == 1
        assert body["next_due_at"] == body["last_window_at"] + 24 * 3600

    def test_interval_reads_config_with_default(self):
        with patch("config.get_field", return_value="6"):
            assert harness._vault_optimize_interval_hours() == 6.0
        for bad in ("0", "soon"):
            with patch("config.get_field", return_value=bad):
                assert harness._vault_optimize_interval_hours() == 24.0
        import config
        assert config._FIELD_DEFAULTS["vault-optimize-interval-hours"] == "24"
        assert config.FIELD_MAP["vault-optimize-interval-hours"] == ("Vault Optimize",
                                                                     "Interval Hours")

    def test_scheduler_loop_runs_window_and_stops(self, window, monkeypatch):
        monkeypatch.setattr(harness, "VAULT_MAINTENANCE_INITIAL_DELAY", 0)
        monkeypatch.setattr(harness, "VAULT_MAINTENANCE_CHECK_INTERVAL", 0.01)
        sched = harness.VaultMaintenanceScheduler()
        sched.start()
        try:
            for _ in range(200):
                if window["calls"]:
                    break
                import time
                time.sleep(0.01)
        finally:
            sched.stop()
            sched._thread.join(timeout=2)
        assert window["calls"] >= 1 and not sched._thread.is_alive()

    def test_scheduler_wired_into_lifespan(self):
        src = inspect.getsource(harness.lifespan)
        assert "vault_maintenance.start()" in src and "vault_maintenance.stop()" in src

    def test_state_file_is_gitignored(self):
        lines = (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()
        assert ".squidsquad/.vault-maintenance.json" in lines
        assert ".squidsquad/.vault-maintenance.json.tmp" in lines


class TestConsumerWiring:
    def test_event_type_cataloged(self):
        import event_catalog
        entry = event_catalog.EMITTED["vault-maintenance"]
        assert "target_alias" in entry["payload_fields"]

    def test_event_mode_contract_routes_event_to_vault_optimize(self):
        text = (REPO / "references" / "sub-skills" / "common-events"
                / "event-mode-contract.md").read_text(encoding="utf-8")
        line = next(l for l in text.splitlines() if l.startswith("- **`vault-maintenance`**"))
        assert "vault-optimize" in line and "ack-cursor" in line

    def test_sub_skill_uses_the_deterministic_filers(self):
        text = (REPO / "references" / "sub-skills" / "common"
                / "vault-optimize.md").read_text(encoding="utf-8")
        for cmd in ("analyze-queue", "file-contradiction", "file-prune-review",
                    "mark-optimized", "compact-telemetry"):
            assert f"vault_optimize.py {cmd}" in text
        assert 'model: "sonnet"' in text
        assert "vault_optimize.py run`" in text  # named only as the retired path
